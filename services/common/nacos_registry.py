"""
Nacos 服务注册与心跳 —— 各微服务共用模块

使用 stdlib urllib 实现，无额外依赖。注册失败不影响服务启动（仅警告）。
"""

import asyncio
import json
import logging
import urllib.parse
import urllib.request


logger = logging.getLogger("nacos_registry")


class NacosRegistry:
    """轻量级 Nacos 服务注册客户端（基于 REST API v1）"""

    def __init__(
        self,
        server_addr: str,
        namespace: str,
        group: str,
        service_name: str,
        ip: str,
        port: int,
        enabled: bool,
    ):
        self.server_addr = server_addr
        self.namespace = namespace
        self.group = group
        self.service_name = service_name
        self.ip = ip
        self.port = port
        self.enabled = enabled
        self._task: asyncio.Task | None = None

    def _request(self, method: str, path: str, params: dict[str, str]):
        if method == "POST":
            # POST 使用表单编码 body
            data = urllib.parse.urlencode(params).encode("utf-8")
            url = f"http://{self.server_addr}{path}"
        else:
            # PUT/DELETE 使用查询参数
            data = None
            qs = urllib.parse.urlencode(params)
            url = f"http://{self.server_addr}{path}?{qs}"
        req = urllib.request.Request(url=url, data=data, method=method)
        if data:
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(req, timeout=2) as resp:
            resp.read()

    async def register(self):
        if not self.enabled:
            return
        try:
            await asyncio.to_thread(
                self._request,
                "POST",
                "/nacos/v1/ns/instance",
                {
                    "serviceName": self.service_name,
                    "groupName": self.group,
                    "namespaceId": self.namespace,
                    "ip": self.ip,
                    "port": str(self.port),
                    "ephemeral": "true",
                    "healthy": "true",
                },
            )
            self._task = asyncio.create_task(self._heartbeat_loop())
            logger.info("Nacos注册成功: %s %s:%s", self.service_name, self.ip, self.port)
        except Exception as exc:
            logger.warning("Nacos注册失败，服务将继续运行: %s", exc)

    async def _heartbeat_loop(self):
        while True:
            await asyncio.sleep(5)
            beat = json.dumps(
                {
                    "ip": self.ip,
                    "port": self.port,
                    "serviceName": self.service_name,
                    "cluster": "DEFAULT",
                    "weight": 1.0,
                    "ephemeral": True,
                },
                ensure_ascii=False,
            )
            try:
                await asyncio.to_thread(
                    self._request,
                    "PUT",
                    "/nacos/v1/ns/instance/beat",
                    {
                        "serviceName": self.service_name,
                        "groupName": self.group,
                        "namespaceId": self.namespace,
                        "ephemeral": "true",
                        "beat": beat,
                    },
                )
            except Exception as exc:
                logger.warning("Nacos心跳失败: %s", exc)

    async def close(self):
        if self._task:
            self._task.cancel()
        if not self.enabled:
            return
        try:
            await asyncio.to_thread(
                self._request,
                "DELETE",
                "/nacos/v1/ns/instance",
                {
                    "serviceName": self.service_name,
                    "groupName": self.group,
                    "namespaceId": self.namespace,
                    "ip": self.ip,
                    "port": str(self.port),
                    "ephemeral": "true",
                },
            )
        except Exception:
            pass
