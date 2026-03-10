"""
秒杀订单 MQ 消费者

从 RabbitMQ seckill_order_queue 消费消息，创建秒杀订单。
包含：幂等校验、MySQL 乐观锁扣减、失败时 Redis 补偿回滚。

启动方式：python -m app.consumer
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime

import aio_pika
import redis.asyncio as aioredis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seckill_consumer")

settings = get_settings()

# ==================== 数据库连接 ====================
engine = create_async_engine(settings.database_url, pool_size=5, max_overflow=5)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# ==================== Redis 连接 ====================
redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global redis_client
    if redis_client is None:
        redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/2"
        redis_client = aioredis.from_url(redis_url, decode_responses=True)
    return redis_client


# ==================== ORM 模型(内联避免循环导入) ====================
from sqlalchemy import BigInteger, String, SmallInteger, Boolean, DateTime, Numeric, func, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Inventory(Base):
    __tablename__ = "df_inventory"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    goods_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    stock: Mapped[int] = mapped_column(default=0)
    locked_stock: Mapped[int] = mapped_column(default=0)
    version: Mapped[int] = mapped_column(Integer, default=0)


class Order(Base):
    __tablename__ = "df_order"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    goods_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    count: Mapped[int] = mapped_column(default=1)
    total_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    pay_method: Mapped[int] = mapped_column(SmallInteger, default=3)
    order_status: Mapped[int] = mapped_column(SmallInteger, default=1)
    address: Mapped[str | None] = mapped_column(String(256), nullable=True)
    trade_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_seckill: Mapped[bool] = mapped_column(Boolean, default=False)
    create_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    update_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class SeckillProcessed(Base):
    """幂等去重表"""
    __tablename__ = "df_seckill_processed"
    request_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    order_id: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ==================== 工具函数 ====================

def generate_order_id() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S") + uuid.uuid4().hex[:18]


async def is_processed(request_id: str) -> str | None:
    """检查消息是否已处理，返回order_id或None"""
    async with SessionLocal() as db:
        result = await db.execute(
            select(SeckillProcessed.order_id).where(SeckillProcessed.request_id == request_id)
        )
        return result.scalar_one_or_none()


async def rollback_redis(goods_id: int, user_id: int):
    """Redis 补偿回滚：恢复库存 + 移除用户去重"""
    r = await get_redis()
    stock_key = f"seckill:stock:{goods_id}"
    user_set_key = f"seckill:users:{goods_id}"
    await r.incr(stock_key)
    await r.srem(user_set_key, str(user_id))
    logger.info(f"Redis补偿回滚: goods_id={goods_id}, user_id={user_id}")


# ==================== 消息处理 ====================

async def process_seckill_message(message: aio_pika.abc.AbstractIncomingMessage):
    """处理单条秒杀消息"""
    async with message.process(requeue=False):
        data = json.loads(message.body.decode())
        request_id = data["request_id"]
        user_id = data["user_id"]
        goods_id = data["goods_id"]

        logger.info(f"消费消息: request_id={request_id}, user={user_id}, goods={goods_id}")

        # 幂等检查
        existing_order_id = await is_processed(request_id)
        if existing_order_id:
            logger.info(f"消息已处理(幂等跳过): request_id={request_id}, order={existing_order_id}")
            return

        async with SessionLocal() as db:
            async with db.begin():
                # 读取当前库存 + 版本号
                inv_result = await db.execute(
                    select(Inventory).where(Inventory.goods_id == goods_id)
                )
                inv = inv_result.scalar_one_or_none()

                if not inv or inv.stock <= 0:
                    logger.warning(f"DB库存不足: goods_id={goods_id}, 执行Redis补偿")
                    await rollback_redis(goods_id, user_id)
                    return

                # 乐观锁扣减
                stmt = (
                    update(Inventory)
                    .where(
                        Inventory.goods_id == goods_id,
                        Inventory.stock > 0,
                        Inventory.version == inv.version,
                    )
                    .values(stock=Inventory.stock - 1, version=Inventory.version + 1)
                )
                result = await db.execute(stmt)

                if result.rowcount == 0:
                    logger.warning(f"乐观锁冲突: goods_id={goods_id}, 执行Redis补偿")
                    await rollback_redis(goods_id, user_id)
                    return

                # 创建订单
                order_id = generate_order_id()
                seckill_price = float(data.get("seckill_price", 0))
                order = Order(
                    id=order_id,
                    user_id=user_id,
                    goods_id=goods_id,
                    count=1,
                    total_price=seckill_price,
                    is_seckill=True,
                    order_status=1,  # 待支付
                )
                db.add(order)

                # 写入幂等表
                processed = SeckillProcessed(request_id=request_id, order_id=order_id)
                db.add(processed)

        # 缓存秒杀结果供前端轮询
        r = await get_redis()
        await r.set(
            f"seckill:result:{user_id}:{goods_id}",
            json.dumps({"order_id": order_id, "status": "created"}),
            ex=1800,  # 30分钟过期
        )

        logger.info(f"订单创建成功: order_id={order_id}, user={user_id}, goods={goods_id}")


# ==================== 主循环 ====================

async def main():
    logger.info("秒杀订单消费者启动中...")
    logger.info(f"RabbitMQ: {settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}")
    logger.info(f"MySQL: {settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}")

    # 确保幂等表存在
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)

    # 连接 RabbitMQ
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)

    # 声明死信交换机和队列
    dlx = await channel.declare_exchange("seckill_dlx", aio_pika.ExchangeType.DIRECT, durable=True)
    dlq = await channel.declare_queue("seckill_dlq", durable=True)
    await dlq.bind(dlx, routing_key="seckill_dlq")

    # 声明主队列
    queue = await channel.declare_queue(
        "seckill_order_queue",
        durable=True,
        arguments={
            "x-dead-letter-exchange": "seckill_dlx",
            "x-dead-letter-routing-key": "seckill_dlq",
            "x-message-ttl": 30000,
        },
    )

    logger.info("开始监听 seckill_order_queue ...")
    await queue.consume(process_seckill_message)

    # 永久运行
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
