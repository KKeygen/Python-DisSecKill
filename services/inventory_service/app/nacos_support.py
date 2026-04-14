"""
库存服务 Nacos 扩展 —— 在共用 NacosRegistry 基础上增加动态配置刷新

NacosRegistry 由共用模块提供（services/common/nacos_registry.py）。
"""

import asyncio
import json
import logging
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass

from app._nacos_common import NacosRegistry  # noqa: F401 — 重导出供 main.py 使用


logger = logging.getLogger("inventory_nacos")


@dataclass
class InventoryDynamicConfig:
    default_limit_per_user: int = 1
    degrade_message: str = "系统繁忙，请稍后重试"
    updated_at: float = 0.0


class NacosConfigRefresher:
    def __init__(
        self,
        server_addr: str,
        namespace: str,
        group: str,
        data_id: str,
        refresh_sec: int,
        enabled: bool,
    ):
        self.server_addr = server_addr
        self.namespace = namespace
        self.group = group
        self.data_id = data_id
        self.refresh_sec = max(1, refresh_sec)
        self.enabled = enabled
        self.config = InventoryDynamicConfig()
        self._task: asyncio.Task | None = None

    def _fetch_config(self) -> str | None:
        params = urllib.parse.urlencode(
            {"dataId": self.data_id, "group": self.group, "tenant": self.namespace}
        )
        req = urllib.request.Request(f"http://{self.server_addr}/nacos/v1/cs/configs?{params}", method="GET")
        try:
            with urllib.request.urlopen(req, timeout=2) as resp:
                return resp.read().decode("utf-8")
        except Exception:
            return None

    def _apply_config(self, raw: str):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("inventory-config不是合法JSON，忽略本次更新")
            return
        self.config.default_limit_per_user = int(
            payload.get("default_limit_per_user", self.config.default_limit_per_user)
        )
        self.config.degrade_message = str(payload.get("degrade_message", self.config.degrade_message))
        self.config.updated_at = time.time()

    async def start(self):
        if not self.enabled:
            return
        raw = await asyncio.to_thread(self._fetch_config)
        if raw:
            self._apply_config(raw)
        self._task = asyncio.create_task(self._loop())

    async def _loop(self):
        while True:
            await asyncio.sleep(self.refresh_sec)
            raw = await asyncio.to_thread(self._fetch_config)
            if raw:
                self._apply_config(raw)

    async def close(self):
        if self._task:
            self._task.cancel()
