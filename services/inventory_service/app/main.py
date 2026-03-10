from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.routers.inventory import router as inventory_router


@asynccontextmanager
async def lifespan(application: FastAPI):
    yield


app = FastAPI(
    title="库存服务 - DisSecKill",
    description="分布式秒杀系统 · 库存服务：库存管理、秒杀扣减、Redis原子操作",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(inventory_router, prefix="/api/inventory", tags=["库存"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "inventory-service"}
