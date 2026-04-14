import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from app.config import get_settings
from app.governance import CircuitBreaker, RateLimiter
from app.nacos_client import NacosClient, parse_gateway_config


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("gateway_service")
settings = get_settings()


@dataclass
class RuntimeConfig:
    routes: dict[str, str] = field(default_factory=lambda: {
        "user": "user-service",
        "goods": "goods-service",
        "order": "order-service",
        "inventory": "inventory-service",
    })
    rate_limit_rps: float = settings.RATE_LIMIT_RPS
    rate_limit_burst: int = settings.RATE_LIMIT_BURST
    circuit_fail_threshold: int = settings.CIRCUIT_FAIL_THRESHOLD
    circuit_open_seconds: int = settings.CIRCUIT_OPEN_SECONDS
    connect_timeout_sec: float = settings.CONNECT_TIMEOUT_SEC
    read_timeout_sec: float = settings.READ_TIMEOUT_SEC
    updated_at: float = field(default_factory=time.time)

    def apply_dynamic(self, payload: dict[str, Any]):
        route_data = payload.get("routes")
        if isinstance(route_data, dict):
            self.routes = {str(k): str(v) for k, v in route_data.items()}

        governance = payload.get("governance", {})
        if isinstance(governance, dict):
            self.rate_limit_rps = float(governance.get("rate_limit_rps", self.rate_limit_rps))
            self.rate_limit_burst = int(governance.get("rate_limit_burst", self.rate_limit_burst))
            self.circuit_fail_threshold = int(governance.get("circuit_fail_threshold", self.circuit_fail_threshold))
            self.circuit_open_seconds = int(governance.get("circuit_open_seconds", self.circuit_open_seconds))

        timeout_cfg = payload.get("timeout", {})
        if isinstance(timeout_cfg, dict):
            self.connect_timeout_sec = float(timeout_cfg.get("connect_timeout_sec", self.connect_timeout_sec))
            self.read_timeout_sec = float(timeout_cfg.get("read_timeout_sec", self.read_timeout_sec))

        self.updated_at = time.time()


nacos_client: NacosClient | None = None
runtime_cfg = RuntimeConfig()
rate_limiter = RateLimiter()
circuit_breaker = CircuitBreaker()
http_client: httpx.AsyncClient | None = None

discovery_cache: dict[str, tuple[float, list[tuple[str, int]]]] = {}
round_robin_idx: dict[str, int] = {}
config_task: asyncio.Task | None = None
beat_task: asyncio.Task | None = None


async def refresh_gateway_config_loop():
    while True:
        await asyncio.sleep(max(1, settings.NACOS_CONFIG_REFRESH_SEC))
        if not (settings.NACOS_ENABLED and nacos_client):
            continue
        raw = await nacos_client.get_config(settings.NACOS_CONFIG_DATA_ID, settings.NACOS_GROUP)
        payload = parse_gateway_config(raw)
        if payload:
            runtime_cfg.apply_dynamic(payload)


async def heartbeat_loop():
    while True:
        await asyncio.sleep(5)
        if not (settings.NACOS_ENABLED and nacos_client):
            continue
        try:
            await nacos_client.send_beat(
                settings.SERVICE_NAME,
                settings.SERVICE_IP,
                settings.SERVICE_PORT,
                settings.NACOS_GROUP,
            )
        except Exception as exc:
            logger.warning("网关Nacos心跳失败: %s", exc)


async def choose_instance(service_name: str) -> tuple[str, int] | None:
    now = time.monotonic()
    cached = discovery_cache.get(service_name)
    if cached and cached[0] > now:
        instances = cached[1]
    else:
        instances: list[tuple[str, int]] = []
        if settings.NACOS_ENABLED and nacos_client:
            instances = await nacos_client.get_instances(service_name, settings.NACOS_GROUP)
        if not instances:
            instances = settings.static_service_fallback.get(service_name, [])
        discovery_cache[service_name] = (now + settings.DISCOVERY_CACHE_TTL_SEC, instances)

    if not instances:
        return None
    idx = round_robin_idx.get(service_name, 0)
    target = instances[idx % len(instances)]
    round_robin_idx[service_name] = (idx + 1) % len(instances)
    return target


def filter_headers(headers: httpx.Headers) -> dict[str, str]:
    # httpx 自动解压 gzip，必须移除 content-encoding 避免浏览器二次解压失败
    excluded = {"content-length", "content-encoding", "connection", "keep-alive", "transfer-encoding", "host"}
    return {k: v for k, v in headers.items() if k.lower() not in excluded}


@asynccontextmanager
async def lifespan(application: FastAPI):
    global nacos_client, http_client, config_task, beat_task
    http_client = httpx.AsyncClient()
    nacos_client = NacosClient(settings.NACOS_SERVER_ADDR, settings.NACOS_NAMESPACE)

    if settings.NACOS_ENABLED:
        try:
            await nacos_client.register_instance(
                settings.SERVICE_NAME,
                settings.SERVICE_IP,
                settings.SERVICE_PORT,
                settings.NACOS_GROUP,
            )
            raw = await nacos_client.get_config(settings.NACOS_CONFIG_DATA_ID, settings.NACOS_GROUP)
            runtime_cfg.apply_dynamic(parse_gateway_config(raw))
            config_task = asyncio.create_task(refresh_gateway_config_loop())
            beat_task = asyncio.create_task(heartbeat_loop())
            logger.info("网关已接入Nacos：注册成功并开始监听动态配置")
        except Exception as exc:
            logger.warning("网关注册Nacos失败，继续使用本地静态配置: %s", exc)

    yield

    if config_task:
        config_task.cancel()
    if beat_task:
        beat_task.cancel()
    if settings.NACOS_ENABLED and nacos_client:
        try:
            await nacos_client.deregister_instance(
                settings.SERVICE_NAME,
                settings.SERVICE_IP,
                settings.SERVICE_PORT,
                settings.NACOS_GROUP,
            )
        except Exception:
            pass
    if http_client:
        await http_client.aclose()
    if nacos_client:
        await nacos_client.close()


app = FastAPI(
    title="动态网关服务 - DisSecKill",
    description="基于Nacos服务发现与动态配置的Python等价网关，提供路由、限流、熔断和降级能力。",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "gateway-service"}


@app.get("/gateway/config/current")
async def current_config():
    return {
        "routes": runtime_cfg.routes,
        "governance": {
            "rate_limit_rps": runtime_cfg.rate_limit_rps,
            "rate_limit_burst": runtime_cfg.rate_limit_burst,
            "circuit_fail_threshold": runtime_cfg.circuit_fail_threshold,
            "circuit_open_seconds": runtime_cfg.circuit_open_seconds,
        },
        "timeout": {
            "connect_timeout_sec": runtime_cfg.connect_timeout_sec,
            "read_timeout_sec": runtime_cfg.read_timeout_sec,
        },
        "updated_at": runtime_cfg.updated_at,
    }


@app.get("/gateway/discovery/{service_alias}")
async def discovery_debug(service_alias: str):
    service_name = runtime_cfg.routes.get(service_alias)
    if not service_name:
        return JSONResponse(status_code=404, content={"detail": f"未配置路由别名: {service_alias}"})
    instances = []
    if settings.NACOS_ENABLED and nacos_client:
        instances = await nacos_client.get_instances(service_name, settings.NACOS_GROUP)
    if not instances:
        instances = settings.static_service_fallback.get(service_name, [])
    return {"service_alias": service_alias, "service_name": service_name, "instances": instances}


@app.api_route("/api/{service_alias}/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def dynamic_proxy(service_alias: str, path: str, request: Request):
    service_name = runtime_cfg.routes.get(service_alias)
    if not service_name:
        return JSONResponse(status_code=404, content={"detail": f"未找到路由: /api/{service_alias}/..."})

    client_ip = request.client.host if request.client else "unknown"
    limiter_key = f"{client_ip}:{service_name}"
    if not rate_limiter.allow(limiter_key, runtime_cfg.rate_limit_rps, runtime_cfg.rate_limit_burst):
        return JSONResponse(
            status_code=429,
            content={"code": "RATE_LIMITED", "message": "请求过于频繁，已被网关限流，请稍后重试"},
        )

    if not circuit_breaker.allow(service_name):
        return JSONResponse(
            status_code=503,
            content={"code": "CIRCUIT_OPEN", "message": "下游服务暂时不可用，已触发熔断降级"},
        )

    instance = await choose_instance(service_name)
    if not instance:
        circuit_breaker.failure(service_name, runtime_cfg.circuit_fail_threshold, runtime_cfg.circuit_open_seconds)
        return JSONResponse(
            status_code=503,
            content={"code": "NO_INSTANCE", "message": f"服务 {service_name} 当前无可用实例"},
        )

    host, port = instance
    forward_path = f"/api/{service_alias}/{path}" if path else f"/api/{service_alias}/"
    forward_url = f"http://{host}:{port}{forward_path}"

    try:
        assert http_client is not None
        upstream = await http_client.request(
            request.method,
            forward_url,
            params=dict(request.query_params),
            content=await request.body(),
            headers=filter_headers(httpx.Headers(request.headers)),
            timeout=httpx.Timeout(runtime_cfg.read_timeout_sec, connect=runtime_cfg.connect_timeout_sec),
        )
    except Exception as exc:
        logger.warning("转发失败 upstream=%s err=%s", forward_url, exc)
        circuit_breaker.failure(service_name, runtime_cfg.circuit_fail_threshold, runtime_cfg.circuit_open_seconds)
        return JSONResponse(
            status_code=503,
            content={"code": "DEGRADED", "message": f"{service_name} 调用失败，网关降级返回"},
        )

    if upstream.status_code >= 500:
        circuit_breaker.failure(service_name, runtime_cfg.circuit_fail_threshold, runtime_cfg.circuit_open_seconds)
    else:
        circuit_breaker.success(service_name)

    resp_headers = filter_headers(upstream.headers)
    resp_headers["X-Gateway-Upstream"] = f"{host}:{port}"
    return Response(content=upstream.content, status_code=upstream.status_code, headers=resp_headers)


@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def frontend_proxy(full_path: str, request: Request):
    target_url = f"{settings.FRONTEND_UPSTREAM}/{full_path}" if full_path else settings.FRONTEND_UPSTREAM
    try:
        assert http_client is not None
        upstream = await http_client.request(
            request.method,
            target_url,
            params=dict(request.query_params),
            content=await request.body(),
            headers=filter_headers(httpx.Headers(request.headers)),
            timeout=httpx.Timeout(10.0, connect=2.0),
        )
        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            headers=filter_headers(upstream.headers),
        )
    except Exception:
        return JSONResponse(status_code=502, content={"detail": "前端服务不可用"})
