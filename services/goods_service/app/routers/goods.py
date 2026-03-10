from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Goods, GoodsCategory
from app.schemas import (
    GoodsCreateRequest,
    GoodsResponse,
    GoodsListResponse,
    GoodsCategoryResponse,
)

router = APIRouter()


@router.get("/categories", response_model=list[GoodsCategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    """获取商品分类列表"""
    result = await db.execute(
        select(GoodsCategory).where(GoodsCategory.is_active == True).order_by(GoodsCategory.sort_order)
    )
    return result.scalars().all()


@router.get("/", response_model=GoodsListResponse)
async def list_goods(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    category_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """商品列表（分页）"""
    query = select(Goods).where(Goods.status == 1)
    count_query = select(sa_func.count()).select_from(Goods).where(Goods.status == 1)

    if category_id:
        query = query.where(Goods.category_id == category_id)
        count_query = count_query.where(Goods.category_id == category_id)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    result = await db.execute(query.offset((page - 1) * size).limit(size).order_by(Goods.id.desc()))
    items = result.scalars().all()

    return GoodsListResponse(items=items, total=total, page=page, size=size)


@router.get("/{goods_id}", response_model=GoodsResponse)
async def get_goods(goods_id: int, db: AsyncSession = Depends(get_db)):
    """商品详情"""
    result = await db.execute(select(Goods).where(Goods.id == goods_id))
    goods = result.scalar_one_or_none()
    if not goods:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品不存在")
    return goods


@router.post("/", response_model=GoodsResponse, status_code=status.HTTP_201_CREATED)
async def create_goods(req: GoodsCreateRequest, db: AsyncSession = Depends(get_db)):
    """创建商品（管理接口）"""
    goods = Goods(**req.model_dump())
    db.add(goods)
    await db.commit()
    await db.refresh(goods)
    return goods
