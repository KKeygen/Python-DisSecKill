import uuid
import json
import time
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from jose import jwt, JWTError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import redis.asyncio as aioredis
from aiokafka import AIOKafkaProducer
from sqlalchemy import text

from app.config import get_settings
from app.snowflake import generate_order_id
from app.sharding import get_sharding_manager, ShardingRouter
from app.schemas import (
    OrderCreateRequest, OrderResponse, OrderListResponse,
    OrderPayRequest, OrderCancelRequest, PaymentResult,
    OrderStatus, PayMethod
)

logger = logging.getLogger("order_service")
settings = get_settings()
router = APIRouter()
security_scheme = HTTPBearer()

# ==================== Redis 连接池 ====================
_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/2"
        _redis_pool = aioredis.from_url(redis_url, decode_responses=True)
    return _redis_pool


# ==================== Kafka 生产者 ====================
_kafka_producer: AIOKafkaProducer | None = None

# Kafka Topics
PAYMENT_TOPIC = "payment_status_topic"          # 支付状态变更
ORDER_CANCEL_TOPIC = "order_cancel_topic"       # 订单取消（库存回滚）
ORDER_STATUS_DLQ = "order_status_dlq"           # 死信队列


async def get_kafka_producer() -> AIOKafkaProducer:
    global _kafka_producer
    if _kafka_producer is None:
        _kafka_producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_url,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            enable_idempotence=True,
            acks='all',
            retries=3,
        )
        await _kafka_producer.start()
    return _kafka_producer


def _get_user_id(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)) -> int:
    try:
        payload = jwt.decode(credentials.credentials, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证凭据")


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    req: OrderCreateRequest,
    user_id: int = Depends(_get_user_id),
):
    """创建订单（同步扣减库存，使用分库分表）"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        # 查询商品价格
        goods_resp = await client.get(f"{settings.GOODS_SERVICE_URL}/api/goods/{req.goods_id}")
        if goods_resp.status_code != 200:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品不存在")
        goods_data = goods_resp.json()
        unit_price = float(goods_data["price"])

        # 调用库存服务扣减库存
        resp = await client.post(
            f"{settings.INVENTORY_SERVICE_URL}/api/inventory/deduct",
            json={"goods_id": req.goods_id, "count": req.count},
        )
    if resp.status_code != 200 or not resp.json().get("success"):
        detail = resp.json().get("detail", "库存不足")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    total_price = req.count * unit_price

    # 生成雪花ID
    order_id = generate_order_id(user_id)
    
    # 使用分片管理器插入订单
    sharding_manager = get_sharding_manager()
    await sharding_manager.insert_order(
        order_id=order_id,
        user_id=user_id,
        goods_id=req.goods_id,
        count=req.count,
        total_price=total_price,
        address=req.address,
    )

    # 构造响应（简化版，实际应从DB重新查询）
    return OrderResponse(
        id=order_id,
        user_id=user_id,
        goods_id=req.goods_id,
        count=req.count,
        total_price=total_price,
        pay_method=3,
        order_status=1,
        address=req.address,
        trade_no=None,
        is_seckill=False,
        create_time=datetime.now(),
    )


@router.get("/", response_model=OrderListResponse)
async def list_orders(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    order_status: int | None = None,
    user_id: int = Depends(_get_user_id),
):
    """当前用户订单列表（跨分片聚合查询）"""
    sharding_manager = get_sharding_manager()
    orders, total = await sharding_manager.query_orders_by_user(
        user_id=user_id,
        page=page,
        size=size,
        order_status=order_status,
    )
    
    # 转换为Pydantic模型
    order_responses = []
    for order_dict in orders:
        order_responses.append(OrderResponse(
            id=order_dict["id"],
            user_id=order_dict["user_id"],
            goods_id=order_dict["goods_id"],
            count=order_dict["count"],
            total_price=float(order_dict["total_price"]),
            pay_method=order_dict["pay_method"],
            order_status=order_dict["order_status"],
            address=order_dict.get("address"),
            trade_no=order_dict.get("trade_no"),
            is_seckill=bool(order_dict["is_seckill"]),
            create_time=order_dict["create_time"],
        ))
    
    return OrderListResponse(items=order_responses, total=total)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    user_id: int = Depends(_get_user_id),
):
    """订单详情（基因法反查分库）"""
    sharding_manager = get_sharding_manager()
    
    # 验证基因：order_id最低位应该等于user_id%2
    if (order_id & 1) != (user_id % 2):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    
    order_dict = await sharding_manager.query_order_by_id(order_id, user_id)
    if not order_dict:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    
    return OrderResponse(
        id=order_dict["id"],
        user_id=order_dict["user_id"],
        goods_id=order_dict["goods_id"],
        count=order_dict["count"],
        total_price=float(order_dict["total_price"]),
        pay_method=order_dict["pay_method"],
        order_status=order_dict["order_status"],
        address=order_dict.get("address"),
        trade_no=order_dict.get("trade_no"),
        is_seckill=bool(order_dict["is_seckill"]),
        create_time=order_dict["create_time"],
        update_time=order_dict.get("update_time"),
    )


@router.put("/{order_id}/pay", response_model=PaymentResult)
async def pay_order(
    order_id: int,
    req: OrderPayRequest,
    user_id: int = Depends(_get_user_id),
):
    """
    订单支付
    
    支付流程：
    1. 校验订单状态（必须是待支付）
    2. 模拟支付（实际应调用第三方支付接口）
    3. 更新订单状态为已支付
    4. 发送支付完成消息到Kafka（保障一致性）
    5. 缓存支付结果到Redis（供前端轮询）
    
    采用TCC模式思想：
    - Try: 检查订单状态，生成trade_no
    - Confirm: 更新数据库状态，发送消息
    - Cancel: 如果消息发送失败，回滚订单状态（由消费者补偿）
    """
    sharding_manager = get_sharding_manager()
    
    # 验证基因
    if (order_id & 1) != (user_id % 2):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    
    # 查询订单
    order_dict = await sharding_manager.query_order_by_id(order_id, user_id)
    if not order_dict:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    
    # 校验订单状态
    if order_dict["order_status"] != OrderStatus.PENDING:
        return PaymentResult(
            success=False,
            message=f"订单状态不正确，当前状态: {order_dict['order_status']}",
            order_id=order_id,
            order_status=order_dict["order_status"]
        )
    
    # 生成交易号（实际应由支付网关返回）
    trade_no = f"PAY{int(time.time()*1000)}{uuid.uuid4().hex[:8].upper()}"
    
    # 获取分片信息
    db_name, table_name = ShardingRouter.resolve(user_id, order_id)
    
    # 更新订单状态（乐观锁：只有待支付状态才能更新）
    update_sql = f"""
        UPDATE {table_name}
        SET order_status = :new_status, 
            pay_method = :pay_method,
            trade_no = :trade_no,
            update_time = NOW()
        WHERE id = :order_id AND user_id = :user_id AND order_status = :old_status
    """
    
    async with await sharding_manager.get_session(db_name) as session:
        async with session.begin():
            result = await session.execute(text(update_sql), {
                "new_status": OrderStatus.PAID,
                "pay_method": req.pay_method,
                "trade_no": trade_no,
                "order_id": order_id,
                "user_id": user_id,
                "old_status": OrderStatus.PENDING,
            })
            
            if result.rowcount == 0:
                return PaymentResult(
                    success=False,
                    message="支付失败，订单状态已变更",
                    order_id=order_id,
                    order_status=order_dict["order_status"]
                )
    
    # 发送支付成功消息到Kafka（保障下游服务一致性）
    payment_message = {
        "order_id": order_id,
        "user_id": user_id,
        "goods_id": order_dict["goods_id"],
        "count": order_dict["count"],
        "total_price": float(order_dict["total_price"]),
        "trade_no": trade_no,
        "pay_method": req.pay_method,
        "is_seckill": bool(order_dict["is_seckill"]),
        "status": "PAID",
        "timestamp": time.time(),
    }
    
    try:
        producer = await get_kafka_producer()
        await producer.send(
            topic=PAYMENT_TOPIC,
            key=str(order_id),
            value=payment_message,
        )
    except Exception as e:
        logger.error(f"发送支付消息失败: {e}, 订单已支付但消息未投递")
        # 这里不回滚订单状态，因为支付已完成
        # 应该写入本地消息表，由定时任务补偿
    
    # 缓存支付结果到Redis
    r = await get_redis()
    await r.set(
        f"payment:result:{order_id}",
        json.dumps({"status": "PAID", "trade_no": trade_no}),
        ex=3600,  # 1小时过期
    )
    
    return PaymentResult(
        success=True,
        message="支付成功",
        order_id=order_id,
        trade_no=trade_no,
        order_status=OrderStatus.PAID
    )


@router.put("/{order_id}/cancel", response_model=PaymentResult)
async def cancel_order(
    order_id: int,
    req: OrderCancelRequest | None = None,
    user_id: int = Depends(_get_user_id),
):
    """
    取消订单
    
    取消流程（Saga补偿模式）：
    1. 校验订单状态（只有待支付才能取消）
    2. 更新订单状态为已取消
    3. 发送取消消息到Kafka（异步回滚库存）
    4. 如果是秒杀订单，还需回滚Redis库存
    
    补偿机制：
    - 如果库存回滚失败，消费者会重试
    - 幂等性由order_id保证
    """
    sharding_manager = get_sharding_manager()
    
    # 验证基因
    if (order_id & 1) != (user_id % 2):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    
    # 查询订单
    order_dict = await sharding_manager.query_order_by_id(order_id, user_id)
    if not order_dict:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    
    # 校验订单状态（只有待支付才能取消）
    if order_dict["order_status"] != OrderStatus.PENDING:
        return PaymentResult(
            success=False,
            message=f"订单不可取消，当前状态: {order_dict['order_status']}",
            order_id=order_id,
            order_status=order_dict["order_status"]
        )
    
    # 获取分片信息
    db_name, table_name = ShardingRouter.resolve(user_id, order_id)
    
    # 更新订单状态为已取消
    update_sql = f"""
        UPDATE {table_name}
        SET order_status = :new_status,
            update_time = NOW()
        WHERE id = :order_id AND user_id = :user_id AND order_status = :old_status
    """
    
    async with await sharding_manager.get_session(db_name) as session:
        async with session.begin():
            result = await session.execute(text(update_sql), {
                "new_status": OrderStatus.CANCELLED,
                "order_id": order_id,
                "user_id": user_id,
                "old_status": OrderStatus.PENDING,
            })
            
            if result.rowcount == 0:
                return PaymentResult(
                    success=False,
                    message="取消失败，订单状态已变更",
                    order_id=order_id,
                    order_status=order_dict["order_status"]
                )
    
    # 发送取消消息到Kafka（异步回滚库存 - Saga补偿）
    cancel_message = {
        "order_id": order_id,
        "user_id": user_id,
        "goods_id": order_dict["goods_id"],
        "count": order_dict["count"],
        "is_seckill": bool(order_dict["is_seckill"]),
        "reason": req.reason if req else None,
        "action": "CANCEL",
        "timestamp": time.time(),
    }
    
    try:
        producer = await get_kafka_producer()
        await producer.send(
            topic=ORDER_CANCEL_TOPIC,
            key=str(order_id),
            value=cancel_message,
        )
    except Exception as e:
        logger.error(f"发送取消消息失败: {e}, 需要手动回滚库存")
        # 订单已取消，但库存未回滚
        # 应该写入本地消息表，由定时任务补偿
    
    # 如果是秒杀订单，立即回滚Redis库存（提高用户体验）
    if order_dict["is_seckill"]:
        try:
            r = await get_redis()
            stock_key = f"seckill:stock:{order_dict['goods_id']}"
            user_count_key = f"seckill:user_count:{order_dict['goods_id']}"
            
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
            await r.eval(rollback_lua, 2, stock_key, user_count_key, 
                        str(user_id), str(order_dict["count"]))
        except Exception as e:
            logger.error(f"Redis库存回滚失败: {e}")
    
    return PaymentResult(
        success=True,
        message="订单已取消",
        order_id=order_id,
        order_status=OrderStatus.CANCELLED
    )


@router.get("/seckill/result/{goods_id}")
async def get_seckill_result(
    goods_id: int,
    user_id: int = Depends(_get_user_id),
):
    """
    查询秒杀结果（前端轮询用）
    
    返回用户对指定商品的秒杀结果
    """
    r = await get_redis()
    result_key = f"seckill:result:{user_id}:{goods_id}"
    result = await r.get(result_key)
    
    if result:
        return json.loads(result)
    
    return {"status": "pending", "message": "秒杀结果处理中"}
