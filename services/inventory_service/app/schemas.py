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


class SeckillResponse(BaseModel):
    success: bool
    message: str
    order_id: str | None = None


class InitSeckillRequest(BaseModel):
    stock: int = Field(..., ge=0)
