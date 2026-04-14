from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.routers.inventory import router as inventory_router
from app.config import get_settings
from app.nacos_support import NacosRegistry, NacosConfigRefresher, InventoryDynamicConfig
from app.dynamic_config import set_dynamic_config

_dynamic_config = InventoryDynamicConfig()


@asynccontextmanager
async def lifespan(application: FastAPI):
    global _dynamic_config
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
    refresher = NacosConfigRefresher(
        server_addr=settings.NACOS_SERVER_ADDR,
        namespace=settings.NACOS_NAMESPACE,
        group=settings.NACOS_GROUP,
        data_id=settings.NACOS_CONFIG_DATA_ID,
        refresh_sec=settings.NACOS_CONFIG_REFRESH_SEC,
        enabled=settings.NACOS_ENABLED,
    )
    await registry.register()
    await refresher.start()
    _dynamic_config = refresher.config
    set_dynamic_config(_dynamic_config)
    yield
    await refresher.close()
    await registry.close()


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
