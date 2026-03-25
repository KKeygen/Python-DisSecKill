from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.routers.orders import router as order_router
from app.snowflake import init_snowflake
from app.sharding import init_sharding_manager
from app.config import get_settings


@asynccontextmanager
async def lifespan(application: FastAPI):
    settings = get_settings()
    # 初始化雪花算法生成器（worker_id可从环境变量获取）
    init_snowflake(worker_id=0, db_count=2)
    # 初始化分片管理器
    init_sharding_manager(settings.shard_url_template)
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
