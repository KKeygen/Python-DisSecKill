import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, get_read_db
from app.models import Goods, GoodsCategory
from app.schemas import (
    GoodsCreateRequest,
    GoodsResponse,
    GoodsListResponse,
    GoodsCategoryResponse,
)
from app.cache import (
    get_goods_cache,
    set_goods_cache,
    set_null_cache,
    invalidate_goods_cache,
    acquire_rebuild_lock,
    release_rebuild_lock,
    CacheMiss,
)

router = APIRouter()


@router.get("/categories", response_model=list[GoodsCategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_read_db)):
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
    db: AsyncSession = Depends(get_read_db),
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


@router.get("/search", response_model=dict)
async def search_goods_route(
    q: str = Query(..., description="搜索关键词"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100)
):
    """通过Elasticsearch搜索商品"""
    from app.search import search_goods_from_es
    items, total = await search_goods_from_es(q, page, size)
    return {"items": items, "total": total, "page": page, "size": size}


@router.get("/{goods_id}", response_model=GoodsResponse)
async def get_goods(goods_id: int, db: AsyncSession = Depends(get_read_db)):
    """商品详情（Redis缓存 + 防穿透/击穿/雪崩）"""
    # 第1步：查缓存
    try:
        cached = await get_goods_cache(goods_id)
        if cached is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品不存在")
        return GoodsResponse(**cached)
    except CacheMiss:
        pass

    # 第2步：尝试获取重建锁（防击穿）
    acquired = await acquire_rebuild_lock(goods_id)
    if not acquired:
        await asyncio.sleep(0.1)
        try:
            cached = await get_goods_cache(goods_id)
            if cached is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品不存在")
            return GoodsResponse(**cached)
        except CacheMiss:
            pass

    # 第3步：查数据库
    try:
        result = await db.execute(select(Goods).where(Goods.id == goods_id))
        goods = result.scalar_one_or_none()

        if not goods:
            await set_null_cache(goods_id)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品不存在")
            
        goods_data = GoodsResponse.model_validate(goods).model_dump(mode="json")
        await set_goods_cache(goods_id, goods_data)
        
        return goods
    finally:
        if acquired:
            await release_rebuild_lock(goods_id)


@router.post("/", response_model=GoodsResponse, status_code=status.HTTP_201_CREATED)
async def create_goods(req: GoodsCreateRequest, db: AsyncSession = Depends(get_db)):
    """创建商品（管理接口），并同步到ES"""
    goods = Goods(**req.model_dump())
    db.add(goods)
    await db.commit()
    await db.refresh(goods)
    
    # 同步到 ES
    try:
        from app.search import sync_goods_to_es
        goods_resp = GoodsResponse.model_validate(goods)
        await sync_goods_to_es(goods_resp)
    except Exception as e:
        print(f"ES sync failed for goods {goods.id}: {e}")
        
    return goods
