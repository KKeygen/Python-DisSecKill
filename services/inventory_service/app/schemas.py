from pydantic import BaseModel, Field


class InventoryResponse(BaseModel):
    goods_id: int
    stock: int
    model_config = {"from_attributes": True}


class DeductRequest(BaseModel):
    goods_id: int
    count: int = Field(1, ge=1)


class DeductResponse(BaseModel):
    success: bool
    remaining: int


class SeckillRequest(BaseModel):
    goods_id: int
    user_id: int
    count: int = Field(1, ge=1, le=10, description="购买数量，默认1件，最多10件")


class SeckillResponse(BaseModel):
    success: bool
    message: str
    order_id: str | None = None


class InitSeckillRequest(BaseModel):
    stock: int = Field(..., ge=0, description="秒杀库存数量")
    seckill_price: float = Field(0.0, ge=0, description="秒杀价格")
    limit_per_user: int = Field(1, ge=1, le=10, description="每用户限购数量，默认1件")
