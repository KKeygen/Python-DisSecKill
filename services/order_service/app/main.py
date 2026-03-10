from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.routers.orders import router as order_router


@asynccontextmanager
async def lifespan(application: FastAPI):
    yield


app = FastAPI(
    title="订单服务 - DisSecKill",
    description="分布式秒杀系统 · 订单服务：下单、查询、状态管理",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(order_router, prefix="/api/order", tags=["订单"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "order-service"}
