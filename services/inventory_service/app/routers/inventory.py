import json
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis
from aiokafka import AIOKafkaProducer

from app.config import get_settings
from app.database import get_db
from app.models import Inventory
from app.schemas import (
    InventoryResponse,
    DeductRequest,
    DeductResponse,
    SeckillRequest,
    SeckillResponse,
    InitSeckillRequest,
)

settings = get_settings()
router = APIRouter()

# ==================== Redis 连接池 ====================
_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis_pool


# ==================== Kafka 生产者 ====================
_kafka_producer: AIOKafkaProducer | None = None

SECKILL_TOPIC = "seckill_order_topic"
SECKILL_DLQ_TOPIC = "seckill_order_dlq"


async def get_kafka_producer() -> AIOKafkaProducer:
    global _kafka_producer
    if _kafka_producer is None:
        _kafka_producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_url,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            enable_idempotence=True,  # 保证幂等性
            acks='all',  # 等待所有副本确认
            retries=3,   # 重试次数
        )
        await _kafka_producer.start()
    return _kafka_producer


# ==================== 本地售罄标记 ====================
sold_out_map: dict[int, bool] = {}


# ==================== Lua脚本 ====================
SECKILL_LUA_SCRIPT = """
local stock_key = KEYS[1]
local user_set_key = KEYS[2]
local user_id = ARGV[1]

-- 检查用户是否已秒杀
if redis.call('sismember', user_set_key, user_id) == 1 then
    return -1  -- 重复秒杀
end

-- 检查库存
local stock = tonumber(redis.call('get', stock_key) or '0')
if stock <= 0 then
    return 0  -- 库存不足
end

-- 扣减库存 + 记录用户
redis.call('decr', stock_key)
redis.call('sadd', user_set_key, user_id)
return 1  -- 成功
"""


@router.get("/{goods_id}", response_model=InventoryResponse)
async def get_inventory(goods_id: int, db: AsyncSession = Depends(get_db)):
    """查询商品库存"""
    result = await db.execute(select(Inventory).where(Inventory.goods_id == goods_id))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="库存记录不存在")
    return InventoryResponse(goods_id=inv.goods_id, stock=inv.stock)


@router.post("/deduct", response_model=DeductResponse)
async def deduct_stock(req: DeductRequest, db: AsyncSession = Depends(get_db)):
    """扣减库存（乐观锁）"""
    result = await db.execute(select(Inventory).where(Inventory.goods_id == req.goods_id))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="库存记录不存在")

    if inv.stock < req.count:
        return DeductResponse(success=False, remaining=inv.stock)

    # 乐观锁更新
    stmt = (
        update(Inventory)
        .where(Inventory.goods_id == req.goods_id, Inventory.version == inv.version)
        .values(stock=Inventory.stock - req.count, version=Inventory.version + 1)
    )
    result = await db.execute(stmt)
    await db.commit()

    if result.rowcount == 0:
        return DeductResponse(success=False, remaining=inv.stock)

    return DeductResponse(success=True, remaining=inv.stock - req.count)


@router.post("/revert", response_model=DeductResponse)
async def revert_stock(req: DeductRequest, db: AsyncSession = Depends(get_db)):
    """回滚库存"""
    stmt = (
        update(Inventory)
        .where(Inventory.goods_id == req.goods_id)
        .values(stock=Inventory.stock + req.count, version=Inventory.version + 1)
    )
    await db.execute(stmt)
    await db.commit()

    result = await db.execute(select(Inventory).where(Inventory.goods_id == req.goods_id))
    inv = result.scalar_one_or_none()
    return DeductResponse(success=True, remaining=inv.stock if inv else 0)


@router.post("/seckill", response_model=SeckillResponse)
async def seckill(req: SeckillRequest):
    """秒杀抢购（Redis Lua原子操作 + MQ异步下单）"""
    # 第1层：本地内存快速拒绝
    if sold_out_map.get(req.goods_id, False):
        return SeckillResponse(success=False, message="库存不足，秒杀结束")

    r = await get_redis()

    stock_key = f"seckill:stock:{req.goods_id}"
    user_set_key = f"seckill:users:{req.goods_id}"

    # 第2层：Redis Lua 原子扣减
    result = await r.eval(SECKILL_LUA_SCRIPT, 2, stock_key, user_set_key, str(req.user_id))

    if result == -1:
        return SeckillResponse(success=False, message="请勿重复秒杀")
    if result == 0:
        sold_out_map[req.goods_id] = True  # 标记售罄
        return SeckillResponse(success=False, message="库存不足，秒杀结束")

    # 第3层：投递MQ消息，异步创建订单
    # 从 Redis 缓存中获取秒杀价格
    seckill_info_key = f"seckill:info:{req.goods_id}"
    seckill_price = await r.hget(seckill_info_key, "seckill_price")
    seckill_price = float(seckill_price) if seckill_price else 0.0

    request_id = uuid.uuid4().hex
    message_body = {
        "user_id": req.user_id,
        "goods_id": req.goods_id,
        "seckill_price": seckill_price,
        "request_id": request_id,
        "timestamp": time.time(),
    }

    try:
        producer = await get_kafka_producer()
        await producer.send(
            topic=SECKILL_TOPIC,
            key=request_id,  # 使用 request_id 作为 partition key
            value=message_body,
        )
    except Exception:
        # Kafka投递失败 → 补偿回滚Redis
        await r.incr(stock_key)
        await r.srem(user_set_key, str(req.user_id))
        sold_out_map.pop(req.goods_id, None)
        return SeckillResponse(success=False, message="系统繁忙，请稍后重试")

    return SeckillResponse(success=True, message="秒杀成功，订单创建中", order_id=request_id)


@router.post("/init/{goods_id}")
async def init_seckill_stock(goods_id: int, req: InitSeckillRequest):
    """初始化秒杀商品库存到Redis"""
    r = await get_redis()
    stock_key = f"seckill:stock:{goods_id}"
    user_set_key = f"seckill:users:{goods_id}"
    info_key = f"seckill:info:{goods_id}"

    await r.set(stock_key, req.stock)
    await r.delete(user_set_key)
    # 存储秒杀价格信息
    await r.hset(info_key, mapping={"seckill_price": str(req.seckill_price)})

    # 清除本地售罄标记
    sold_out_map.pop(goods_id, None)

    return {"success": True, "goods_id": goods_id, "stock": req.stock}
