import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from jose import jwt, JWTError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx

from app.config import get_settings
from app.snowflake import generate_order_id
from app.sharding import get_sharding_manager, ShardingRouter
from app.schemas import OrderCreateRequest, OrderResponse, OrderListResponse

settings = get_settings()
router = APIRouter()
security_scheme = HTTPBearer()


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
    )
