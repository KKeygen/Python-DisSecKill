from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.routers.goods import router as goods_router
from app.config import get_settings
from app.nacos_registry import NacosRegistry


@asynccontextmanager
async def lifespan(application: FastAPI):
    settings = get_settings()
    registry = NacosRegistry(
        server_addr=settings.NACOS_SERVER_ADDR,
        namespace=settings.NACOS_NAMESPACE,
        group=settings.NACOS_GROUP,
        service_name=settings.SERVICE_NAME,
        ip=settings.SERVICE_IP,
        port=settings.SERVICE_PORT,
        enabled=settings.NACOS_ENABLED,
    )
    await registry.register()
    from app.search import init_es_index
    try:
        await init_es_index()
    except Exception as e:
        print("Failed to initialize ES", e)

    yield
    await registry.close()


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

