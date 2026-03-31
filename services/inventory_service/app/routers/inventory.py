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
# 增强版Lua脚本：支持限购N件
SECKILL_LUA_SCRIPT = """
local stock_key = KEYS[1]           -- 库存键 seckill:stock:{goods_id}
local user_count_key = KEYS[2]      -- 用户购买计数键 seckill:user_count:{goods_id}
local limit_key = KEYS[3]           -- 限购数量键 seckill:limit:{goods_id}
local user_id = ARGV[1]             -- 用户ID
local buy_count = tonumber(ARGV[2]) -- 本次购买数量

-- 获取限购数量（默认1）
local limit = tonumber(redis.call('get', limit_key) or '1')

-- 获取用户已购买数量
local bought = tonumber(redis.call('hget', user_count_key, user_id) or '0')

-- 检查是否超过限购
if bought + buy_count > limit then
    return -1  -- 超过限购数量
end

-- 检查库存是否充足
local stock = tonumber(redis.call('get', stock_key) or '0')
if stock < buy_count then
    return 0  -- 库存不足
end

-- 原子操作：扣减库存 + 记录用户购买数量
redis.call('decrby', stock_key, buy_count)
redis.call('hincrby', user_count_key, user_id, buy_count)
return buy_count  -- 返回实际购买数量
"""

# 库存回滚Lua脚本（补偿用）
SECKILL_ROLLBACK_LUA_SCRIPT = """
local stock_key = KEYS[1]           -- 库存键
local user_count_key = KEYS[2]      -- 用户购买计数键
local user_id = ARGV[1]             -- 用户ID
local rollback_count = tonumber(ARGV[2])  -- 回滚数量

-- 恢复库存
redis.call('incrby', stock_key, rollback_count)

-- 减少用户购买计数
local bought = tonumber(redis.call('hget', user_count_key, user_id) or '0')
local new_count = bought - rollback_count
if new_count <= 0 then
    redis.call('hdel', user_count_key, user_id)
else
    redis.call('hset', user_count_key, user_id, new_count)
end

return 1
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
    """
    秒杀抢购（Redis Lua原子操作 + MQ异步下单）
    
    支持限购N件：
    - 每次请求可指定购买数量(count)
    - Redis使用Hash记录每个用户的累计购买数量
    - Lua脚本原子性检查限购+扣减库存
    """
    # 第1层：本地内存快速拒绝
    if sold_out_map.get(req.goods_id, False):
        return SeckillResponse(success=False, message="库存不足，秒杀结束")

    r = await get_redis()

    stock_key = f"seckill:stock:{req.goods_id}"
    user_count_key = f"seckill:user_count:{req.goods_id}"  # 改用Hash存储用户购买计数
    limit_key = f"seckill:limit:{req.goods_id}"

    # 第2层：Redis Lua 原子扣减（支持限购N件）
    result = await r.eval(
        SECKILL_LUA_SCRIPT, 3, 
        stock_key, user_count_key, limit_key,
        str(req.user_id), str(req.count)
    )

    if result == -1:
        # 获取当前限购配置给用户提示
        limit = await r.get(limit_key)
        limit = int(limit) if limit else 1
        return SeckillResponse(success=False, message=f"超过限购数量(限购{limit}件)")
    if result == 0:
        sold_out_map[req.goods_id] = True  # 标记售罄
        return SeckillResponse(success=False, message="库存不足，秒杀结束")

    buy_count = int(result)  # 实际购买数量

    # 第3层：投递MQ消息，异步创建订单
    # 从 Redis 缓存中获取秒杀价格
    seckill_info_key = f"seckill:info:{req.goods_id}"
    seckill_price = await r.hget(seckill_info_key, "seckill_price")
    seckill_price = float(seckill_price) if seckill_price else 0.0

    request_id = uuid.uuid4().hex
    message_body = {
        "user_id": req.user_id,
        "goods_id": req.goods_id,
        "count": buy_count,  # 购买数量
        "seckill_price": seckill_price,
        "total_price": seckill_price * buy_count,  # 总价
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
        await r.eval(
            SECKILL_ROLLBACK_LUA_SCRIPT, 2,
            stock_key, user_count_key,
            str(req.user_id), str(buy_count)
        )
        sold_out_map.pop(req.goods_id, None)
        return SeckillResponse(success=False, message="系统繁忙，请稍后重试")

    return SeckillResponse(success=True, message=f"秒杀成功，购买{buy_count}件，订单创建中", order_id=request_id)


@router.post("/init/{goods_id}")
async def init_seckill_stock(goods_id: int, req: InitSeckillRequest):
    """
    初始化秒杀商品库存到Redis
    
    设置：
    - 库存数量
    - 秒杀价格
    - 限购数量（默认1件/人）
    - 清空用户购买计数
    """
    r = await get_redis()
    stock_key = f"seckill:stock:{goods_id}"
    user_count_key = f"seckill:user_count:{goods_id}"  # 用户购买计数Hash
    limit_key = f"seckill:limit:{goods_id}"  # 限购数量
    info_key = f"seckill:info:{goods_id}"

    # 使用pipeline批量设置
    pipe = r.pipeline()
    pipe.set(stock_key, req.stock)
    pipe.delete(user_count_key)  # 清空用户购买计数
    pipe.set(limit_key, req.limit_per_user)  # 设置限购数量
    pipe.hset(info_key, mapping={
        "seckill_price": str(req.seckill_price),
        "limit_per_user": str(req.limit_per_user),
        "total_stock": str(req.stock),
    })
    await pipe.execute()

    # 清除本地售罄标记
    sold_out_map.pop(goods_id, None)

    return {
        "success": True, 
        "goods_id": goods_id, 
        "stock": req.stock,
        "limit_per_user": req.limit_per_user,
        "seckill_price": req.seckill_price
    }


@router.get("/seckill/status/{goods_id}")
async def get_seckill_status(goods_id: int):
    """
    查询秒杀商品状态
    
    返回当前库存、限购配置等信息
    """
    r = await get_redis()
    stock_key = f"seckill:stock:{goods_id}"
    limit_key = f"seckill:limit:{goods_id}"
    info_key = f"seckill:info:{goods_id}"
    
    stock = await r.get(stock_key)
    limit = await r.get(limit_key)
    info = await r.hgetall(info_key)
    
    return {
        "goods_id": goods_id,
        "current_stock": int(stock) if stock else 0,
        "limit_per_user": int(limit) if limit else 1,
        "seckill_price": float(info.get("seckill_price", 0)),
        "total_stock": int(info.get("total_stock", 0)),
        "sold_out": sold_out_map.get(goods_id, False),
    }


@router.get("/seckill/user/{goods_id}/{user_id}")
async def get_user_seckill_info(goods_id: int, user_id: int):
    """
    查询用户秒杀购买信息
    
    返回用户已购买数量和剩余可购数量
    """
    r = await get_redis()
    user_count_key = f"seckill:user_count:{goods_id}"
    limit_key = f"seckill:limit:{goods_id}"
    
    bought = await r.hget(user_count_key, str(user_id))
    limit = await r.get(limit_key)
    
    bought_count = int(bought) if bought else 0
    limit_count = int(limit) if limit else 1
    
    return {
        "user_id": user_id,
        "goods_id": goods_id,
        "bought_count": bought_count,
        "limit_per_user": limit_count,
        "remaining_quota": max(0, limit_count - bought_count),
    }
