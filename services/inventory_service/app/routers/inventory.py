import json
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis
import aio_pika

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


# ==================== RabbitMQ 连接 ====================
_mq_connection: aio_pika.abc.AbstractRobustConnection | None = None
_mq_channel: aio_pika.abc.AbstractChannel | None = None

SECKILL_QUEUE = "seckill_order_queue"
SECKILL_DLX = "seckill_dlx"
SECKILL_DLQ = "seckill_dlq"


async def get_mq_channel() -> aio_pika.abc.AbstractChannel:
    global _mq_connection, _mq_channel
    if _mq_connection is None or _mq_connection.is_closed:
        _mq_connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    if _mq_channel is None or _mq_channel.is_closed:
        _mq_channel = await _mq_connection.channel()
        # 声明死信交换机和队列
        dlx = await _mq_channel.declare_exchange(SECKILL_DLX, aio_pika.ExchangeType.DIRECT, durable=True)
        dlq = await _mq_channel.declare_queue(SECKILL_DLQ, durable=True)
        await dlq.bind(dlx, routing_key=SECKILL_DLQ)
        # 声明秒杀订单队列（绑定死信交换机）
        await _mq_channel.declare_queue(
            SECKILL_QUEUE,
            durable=True,
            arguments={
                "x-dead-letter-exchange": SECKILL_DLX,
                "x-dead-letter-routing-key": SECKILL_DLQ,
                "x-message-ttl": 30000,
            },
        )
    return _mq_channel


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
    request_id = uuid.uuid4().hex
    message_body = {
        "user_id": req.user_id,
        "goods_id": req.goods_id,
        "request_id": request_id,
        "timestamp": time.time(),
    }

    try:
        channel = await get_mq_channel()
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(message_body).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                message_id=request_id,
            ),
            routing_key=SECKILL_QUEUE,
        )
    except Exception:
        # MQ投递失败 → 补偿回滚Redis
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

    await r.set(stock_key, req.stock)
    await r.delete(user_set_key)

    # 清除本地售罄标记
    sold_out_map.pop(goods_id, None)

    return {"success": True, "goods_id": goods_id, "stock": req.stock}
