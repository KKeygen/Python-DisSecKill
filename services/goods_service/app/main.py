from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.routers.goods import router as goods_router


@asynccontextmanager
async def lifespan(application: FastAPI):
    yield


app = FastAPI(
    title="商品服务 - DisSecKill",
    description="分布式秒杀系统 · 商品服务：商品CRUD、分类管理",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(goods_router, prefix="/api/goods", tags=["商品"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "goods-service"}
