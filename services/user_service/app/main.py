from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.routers.auth import router as auth_router
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
    yield
    await registry.close()


app = FastAPI(
    title="用户服务 - DisSecKill",
    description="分布式秒杀系统 · 用户服务：注册、登录、JWT认证、用户信息管理",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(auth_router, prefix="/api/user", tags=["用户"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "user-service"}
