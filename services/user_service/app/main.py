from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.routers.auth import router as auth_router


@asynccontextmanager
async def lifespan(application: FastAPI):
    # 启动时可初始化连接池等
    yield
    # 关闭时清理资源


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
