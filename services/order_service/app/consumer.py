"""
秒杀订单 Kafka 消费者 + 分库分表

从 Kafka 消费消息，处理：
1. seckill_order_topic - 创建秒杀订单到分片库表
2. order_cancel_topic - 订单取消后回滚库存（Saga补偿）
3. payment_status_topic - 支付状态变更处理

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
from app.sharding import init_sharding_manager, ShardingManager, ShardingRouter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seckill_consumer")

settings = get_settings()

# Kafka Topics
SECKILL_TOPIC = "seckill_order_topic"
ORDER_CANCEL_TOPIC = "order_cancel_topic"
PAYMENT_TOPIC = "payment_status_topic"

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


async def rollback_redis(goods_id: int, user_id: int, count: int = 1):
    """Redis 补偿回滚：恢复库存 + 减少用户购买计数"""
    r = await get_redis()
    stock_key = f"seckill:stock:{goods_id}"
    user_count_key = f"seckill:user_count:{goods_id}"
    
    # 使用Lua脚本原子回滚
    rollback_lua = """
    local stock_key = KEYS[1]
    local user_count_key = KEYS[2]
    local user_id = ARGV[1]
    local count = tonumber(ARGV[2])
    
    redis.call('incrby', stock_key, count)
    local bought = tonumber(redis.call('hget', user_count_key, user_id) or '0')
    local new_count = bought - count
    if new_count <= 0 then
        redis.call('hdel', user_count_key, user_id)
    else
        redis.call('hset', user_count_key, user_id, new_count)
    end
    return 1
    """
    await r.eval(rollback_lua, 2, stock_key, user_count_key, str(user_id), str(count))
    logger.info(f"Redis补偿回滚: goods_id={goods_id}, user_id={user_id}, count={count}")


# ==================== 消息处理 ====================

async def process_seckill_message(message, sharding_manager: ShardingManager, generator: SnowflakeGenerator):
    """处理单条秒杀消息"""
    data = json.loads(message.value.decode())
    request_id = data["request_id"]
    user_id = data["user_id"]
    goods_id = data["goods_id"]
    count = data.get("count", 1)  # 支持购买多件

    logger.info(f"消费秒杀消息: request_id={request_id}, user={user_id}, goods={goods_id}, count={count}")

    # 幂等检查（跨分片）
    existing_order_id = await is_processed(request_id, sharding_manager)
    if existing_order_id:
        logger.info(f"消息已处理(幂等跳过): request_id={request_id}, order={existing_order_id}")
        return

    # 生成订单ID（雪花算法+基因法）
    order_id = generator.generate(user_id)
    
    # 获取目标分片
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

                if not inv_row or inv_row["stock"] < count:
                    logger.warning(f"DB库存不足: goods_id={goods_id}, 需要={count}, 执行Redis补偿")
                    await rollback_redis(goods_id, user_id, count)
                    return

                current_version = inv_row["version"]

                # 乐观锁扣减库存（在主库）
                update_sql = """
                    UPDATE disseckill.df_inventory 
                    SET stock = stock - :count, version = version + 1 
                    WHERE goods_id = :goods_id AND stock >= :count AND version = :version
                """
                result = await session.execute(text(update_sql), {
                    "goods_id": goods_id,
                    "count": count,
                    "version": current_version
                })

                if result.rowcount == 0:
                    logger.warning(f"乐观锁冲突: goods_id={goods_id}, 执行Redis补偿")
                    await rollback_redis(goods_id, user_id, count)
                    return

                # 创建订单（插入到正确的分片表）
                seckill_price = float(data.get("seckill_price", 0))
                total_price = float(data.get("total_price", seckill_price * count))
                order_sql = f"""
                    INSERT INTO {table_name}
                        (id, user_id, goods_id, count, total_price, is_seckill, order_status, pay_method)
                    VALUES
                        (:id, :user_id, :goods_id, :count, :total_price, TRUE, 1, 3)
                """
                await session.execute(text(order_sql), {
                    "id": order_id,
                    "user_id": user_id,
                    "goods_id": goods_id,
                    "count": count,
                    "total_price": total_price,
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
            json.dumps({"order_id": str(order_id), "status": "created", "count": count}),
            ex=1800,  # 30分钟过期
        )

        logger.info(f"秒杀订单创建成功: order_id={order_id}, user={user_id}, goods={goods_id}, count={count}, 分片={db_name}.{table_name}")

    except Exception as e:
        logger.error(f"秒杀订单创建失败: {e}, 执行Redis补偿")
        await rollback_redis(goods_id, user_id, count)


# ==================== 订单取消处理（Saga补偿） ====================

async def process_cancel_message(message, sharding_manager: ShardingManager):
    """
    处理订单取消消息（Saga补偿模式）
    
    回滚库存到MySQL，保障最终一致性
    """
    data = json.loads(message.value.decode())
    order_id = data["order_id"]
    user_id = data["user_id"]
    goods_id = data["goods_id"]
    count = data.get("count", 1)
    is_seckill = data.get("is_seckill", False)
    
    logger.info(f"处理订单取消: order_id={order_id}, goods={goods_id}, count={count}")
    
    try:
        # 回滚MySQL库存
        db_name = f"disseckill_order_0"  # 库存在主库
        async with await sharding_manager.get_session(db_name) as session:
            async with session.begin():
                revert_sql = """
                    UPDATE disseckill.df_inventory 
                    SET stock = stock + :count, version = version + 1 
                    WHERE goods_id = :goods_id
                """
                await session.execute(text(revert_sql), {
                    "goods_id": goods_id,
                    "count": count
                })
        
        logger.info(f"MySQL库存回滚成功: goods_id={goods_id}, count={count}")
        
    except Exception as e:
        logger.error(f"MySQL库存回滚失败: {e}, order_id={order_id}")
        # 这里应该发送到死信队列或写入补偿表，由定时任务重试


# ==================== 支付状态处理 ====================

async def process_payment_message(message, sharding_manager: ShardingManager):
    """
    处理支付状态变更消息
    
    可以在这里：
    1. 发送通知（短信、邮件等）
    2. 更新统计数据
    3. 触发后续业务流程（如发货）
    """
    data = json.loads(message.value.decode())
    order_id = data["order_id"]
    user_id = data["user_id"]
    status = data["status"]
    trade_no = data.get("trade_no")
    
    logger.info(f"处理支付消息: order_id={order_id}, status={status}, trade_no={trade_no}")
    
    # 缓存支付结果
    r = await get_redis()
    await r.set(
        f"payment:result:{order_id}",
        json.dumps({"status": status, "trade_no": trade_no}),
        ex=3600,
    )
    
    # TODO: 后续可以在这里添加：
    # - 发送支付成功通知
    # - 更新销量统计
    # - 触发发货流程


# ==================== 主循环 ====================

async def main():
    logger.info("订单消费者启动中...")
    logger.info(f"Kafka: {settings.KAFKA_HOST}:{settings.KAFKA_PORT}")
    logger.info(f"MySQL: {settings.MYSQL_HOST}:{settings.MYSQL_PORT}")

    # 初始化雪花算法生成器
    generator = init_snowflake(worker_id=0, db_count=2)
    
    # 初始化分片管理器
    sharding_manager = init_sharding_manager(settings.shard_url_template)

    # 创建Kafka消费者（订阅多个Topic）
    consumer = AIOKafkaConsumer(
        SECKILL_TOPIC,
        ORDER_CANCEL_TOPIC,
        PAYMENT_TOPIC,
        bootstrap_servers=settings.kafka_url,
        group_id="order_consumer_group",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda m: m,
    )

    try:
        await consumer.start()
        logger.info(f"开始监听Topics: {SECKILL_TOPIC}, {ORDER_CANCEL_TOPIC}, {PAYMENT_TOPIC}")

        async for message in consumer:
            try:
                topic = message.topic
                if topic == SECKILL_TOPIC:
                    await process_seckill_message(message, sharding_manager, generator)
                elif topic == ORDER_CANCEL_TOPIC:
                    await process_cancel_message(message, sharding_manager)
                elif topic == PAYMENT_TOPIC:
                    await process_payment_message(message, sharding_manager)
                else:
                    logger.warning(f"未知Topic: {topic}")
            except Exception as e:
                logger.error(f"处理消息失败: {e}, topic={message.topic}, offset={message.offset}")

    finally:
        await consumer.stop()
        await sharding_manager.close()
        if redis_client:
            await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
