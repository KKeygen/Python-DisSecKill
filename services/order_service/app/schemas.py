from pydantic import BaseModel, Field
from datetime import datetime


class OrderCreateRequest(BaseModel):
    goods_id: int
    count: int = Field(1, ge=1)
    address: str | None = None


class OrderResponse(BaseModel):
    id: str
    user_id: int
    goods_id: int
    count: int
    total_price: float
    pay_method: int
    order_status: int
    address: str | None = None
    trade_no: str | None = None
    is_seckill: bool
    create_time: datetime
    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    items: list[OrderResponse]
    total: int
