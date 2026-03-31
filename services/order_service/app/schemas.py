from pydantic import BaseModel, Field
from datetime import datetime
from enum import IntEnum


class OrderStatus(IntEnum):
    """订单状态枚举"""
    PENDING = 1      # 待支付
    PAID = 2         # 已支付
    SHIPPED = 3      # 已发货
    CANCELLED = 4    # 已取消
    COMPLETED = 5    # 已完成
    REFUNDING = 6    # 退款中
    REFUNDED = 7     # 已退款


class PayMethod(IntEnum):
    """支付方式枚举"""
    ALIPAY = 1       # 支付宝
    WECHAT = 2       # 微信支付
    BALANCE = 3      # 余额支付


class OrderCreateRequest(BaseModel):
    goods_id: int
    count: int = Field(1, ge=1)
    address: str | None = None


class OrderPayRequest(BaseModel):
    """订单支付请求"""
    pay_method: int = Field(PayMethod.BALANCE, ge=1, le=3, description="支付方式: 1-支付宝, 2-微信, 3-余额")


class OrderCancelRequest(BaseModel):
    """订单取消请求"""
    reason: str | None = Field(None, max_length=200, description="取消原因")


class OrderResponse(BaseModel):
    id: int
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
    update_time: datetime | None = None
    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    items: list[OrderResponse]
    total: int


class PaymentResult(BaseModel):
    """支付结果"""
    success: bool
    message: str
    order_id: int
    trade_no: str | None = None
    order_status: int
