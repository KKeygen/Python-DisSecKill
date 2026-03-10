from pydantic import BaseModel, Field
from datetime import datetime


class GoodsCategoryResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    model_config = {"from_attributes": True}


class GoodsCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    desc: str | None = None
    price: float = Field(..., gt=0)
    category_id: int
    unit: str = "件"
    image: str | None = None


class GoodsResponse(BaseModel):
    id: int
    category_id: int
    name: str
    desc: str | None = None
    price: float
    unit: str
    image: str | None = None
    is_seckill: bool
    seckill_price: float | None = None
    seckill_start: datetime | None = None
    seckill_end: datetime | None = None
    status: int
    create_time: datetime
    model_config = {"from_attributes": True}


class GoodsListResponse(BaseModel):
    items: list[GoodsResponse]
    total: int
    page: int
    size: int
