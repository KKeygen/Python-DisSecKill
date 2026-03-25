"""
秒杀订单 Kafka 消费者 + 分库分表

从 Kafka seckill_order_topic 消费消息，创建秒杀订单到分片库表。
包含：幂等校验、雪花ID生成、MySQL 乐观锁扣减、失败时 Redis 补偿回滚。

启动方式：python -m app.consumer
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime

from aiokafka import AIOKafkaConsumer
import redis.asyncio as aioredis
from sqlalchemy import text

from app.config import get_settings
from app.snowflake import init_snowflake, SnowflakeGenerator
from app.sharding import init_sharding_manager, ShardingManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seckill_consumer")

settings = get_settings()

# ==================== Redis 连接 ====================
redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global redis_client
    if redis_client is None:
        redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/2"
        redis_client = aioredis.from_url(redis_url, decode_responses=True)
    return redis_client


# ==================== 幂等检查 ====================

async def is_processed(request_id: str, sharding_manager: ShardingManager) -> int | None:
    """
    检查消息是否已处理（跨所有分片库查询）
    
    Returns:
        order_id or None
    """
    # 简化版：在两个分片库中都查询幂等表
    for db_idx in range(2):
        db_name = f"disseckill_order_{db_idx}"
        sql = "SELECT order_id FROM df_seckill_processed WHERE request_id = :request_id"
        try:
            async with await sharding_manager.get_session(db_name) as session:
                result = await session.execute(text(sql), {"request_id": request_id})
                order_id = result.scalar_one_or_none()
                if order_id:
                    return order_id
        except Exception as e:
            logger.warning(f"幂等检查失败 {db_name}: {e}")
    return None


async def rollback_redis(goods_id: int, user_id: int):
    """Redis 补偿回滚：恢复库存 + 移除用户去重"""
    r = await get_redis()
    stock_key = f"seckill:stock:{goods_id}"
    user_set_key = f"seckill:users:{goods_id}"
    await r.incr(stock_key)
    await r.srem(user_set_key, str(user_id))
    logger.info(f"Redis补偿回滚: goods_id={goods_id}, user_id={user_id}")


# ==================== 消息处理 ====================

async def process_seckill_message(message, sharding_manager: ShardingManager, generator: SnowflakeGenerator):
    """处理单条秒杀消息"""
    data = json.loads(message.value.decode())
    request_id = data["request_id"]
    user_id = data["user_id"]
    goods_id = data["goods_id"]

    logger.info(f"消费消息: request_id={request_id}, user={user_id}, goods={goods_id}")

    # 幂等检查（跨分片）
    existing_order_id = await is_processed(request_id, sharding_manager)
    if existing_order_id:
        logger.info(f"消息已处理(幂等跳过): request_id={request_id}, order={existing_order_id}")
        return

    # 生成订单ID（雪花算法+基因法）
    order_id = generator.generate(user_id)
    
    # 获取目标分片
    from app.sharding import ShardingRouter
    db_name, table_name = ShardingRouter.resolve(user_id, order_id)
    
    try:
        async with await sharding_manager.get_session(db_name) as session:
            async with session.begin():
                # 读取当前库存 + 版本号（从主库）
                inv_sql = f"""
                    SELECT stock, version FROM disseckill.df_inventory 
                    WHERE goods_id = :goods_id
                """
                inv_result = await session.execute(text(inv_sql), {"goods_id": goods_id})
                inv_row = inv_result.mappings().first()

                if not inv_row or inv_row["stock"] <= 0:
                    logger.warning(f"DB库存不足: goods_id={goods_id}, 执行Redis补偿")
                    await rollback_redis(goods_id, user_id)
                    return

                current_version = inv_row["version"]

                # 乐观锁扣减库存（在主库）
                update_sql = """
                    UPDATE disseckill.df_inventory 
                    SET stock = stock - 1, version = version + 1 
                    WHERE goods_id = :goods_id AND stock > 0 AND version = :version
                """
                result = await session.execute(text(update_sql), {
                    "goods_id": goods_id,
                    "version": current_version
                })

                if result.rowcount == 0:
                    logger.warning(f"乐观锁冲突: goods_id={goods_id}, 执行Redis补偿")
                    await rollback_redis(goods_id, user_id)
                    return

                # 创建订单（插入到正确的分片表）
                seckill_price = float(data.get("seckill_price", 0))
                order_sql = f"""
                    INSERT INTO {table_name}
                        (id, user_id, goods_id, count, total_price, is_seckill, order_status, pay_method)
                    VALUES
                        (:id, :user_id, :goods_id, 1, :total_price, TRUE, 1, 3)
                """
                await session.execute(text(order_sql), {
                    "id": order_id,
                    "user_id": user_id,
                    "goods_id": goods_id,
                    "total_price": seckill_price,
                })

                # 写入幂等表
                processed_sql = """
                    INSERT INTO df_seckill_processed (request_id, order_id)
                    VALUES (:request_id, :order_id)
                """
                await session.execute(text(processed_sql), {
                    "request_id": request_id,
                    "order_id": order_id
                })

        # 缓存秒杀结果供前端轮询
        r = await get_redis()
        await r.set(
            f"seckill:result:{user_id}:{goods_id}",
            json.dumps({"order_id": str(order_id), "status": "created"}),
            ex=1800,  # 30分钟过期
        )

        logger.info(f"订单创建成功: order_id={order_id}, user={user_id}, goods={goods_id}, 分片={db_name}.{table_name}")

    except Exception as e:
        logger.error(f"订单创建失败: {e}, 执行Redis补偿")
        await rollback_redis(goods_id, user_id)


# ==================== 主循环 ====================

async def main():
    logger.info("秒杀订单Kafka消费者启动中...")
    logger.info(f"Kafka: {settings.KAFKA_HOST}:{settings.KAFKA_PORT}")
    logger.info(f"MySQL: {settings.MYSQL_HOST}:{settings.MYSQL_PORT}")

    # 初始化雪花算法生成器
    generator = init_snowflake(worker_id=0, db_count=2)
    
    # 初始化分片管理器
    sharding_manager = init_sharding_manager(settings.shard_url_template)

    # 创建Kafka消费者
    consumer = AIOKafkaConsumer(
        "seckill_order_topic",
        bootstrap_servers=settings.kafka_url,
        group_id="seckill_order_consumer_group",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda m: m,  # 原始字节，在处理函数中解析JSON
    )

    try:
        await consumer.start()
        logger.info("开始监听 seckill_order_topic ...")

        async for message in consumer:
            try:
                await process_seckill_message(message, sharding_manager, generator)
            except Exception as e:
                logger.error(f"处理消息失败: {e}, offset={message.offset}")
                # Kafka会自动提交offset，失败的消息不会重复处理
                # 如需死信队列，可手动发送到DLQ topic

    finally:
        await consumer.stop()
        await sharding_manager.close()
        if redis_client:
            await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
