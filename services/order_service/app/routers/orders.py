import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from jose import jwt, JWTError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.config import get_settings
from app.database import get_db
from app.models import Order
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


def _generate_order_id() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S") + uuid.uuid4().hex[:18]


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    req: OrderCreateRequest,
    user_id: int = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """创建订单（同步扣减库存）"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        # 查询商品价格
        goods_resp = await client.get(
            f"{settings.GOODS_SERVICE_URL}/api/goods/{req.goods_id}",
        )
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

    order = Order(
        id=_generate_order_id(),
        user_id=user_id,
        goods_id=req.goods_id,
        count=req.count,
        total_price=total_price,
        address=req.address,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


@router.get("/", response_model=OrderListResponse)
async def list_orders(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    order_status: int | None = None,
    user_id: int = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """当前用户订单列表"""
    query = select(Order).where(Order.user_id == user_id)
    count_query = select(sa_func.count()).select_from(Order).where(Order.user_id == user_id)

    if order_status is not None:
        query = query.where(Order.order_status == order_status)
        count_query = count_query.where(Order.order_status == order_status)

    total = (await db.execute(count_query)).scalar()
    result = await db.execute(query.offset((page - 1) * size).limit(size).order_by(Order.create_time.desc()))
    return OrderListResponse(items=result.scalars().all(), total=total)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    user_id: int = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """订单详情"""
    result = await db.execute(select(Order).where(Order.id == order_id, Order.user_id == user_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    return order
