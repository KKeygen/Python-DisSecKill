import json
import logging
from typing import Any

import httpx


logger = logging.getLogger("gateway_nacos")


class NacosClient:
    def __init__(self, server_addr: str, namespace: str = "public", timeout_sec: float = 2.0):
        self.base_url = f"http://{server_addr}"
        self.namespace = namespace
        self.timeout = timeout_sec
        self._client = httpx.AsyncClient(timeout=timeout_sec)

    async def close(self):
        await self._client.aclose()

    async def get_instances(self, service_name: str, group: str = "DEFAULT_GROUP") -> list[tuple[str, int]]:
        try:
            resp = await self._client.get(
                f"{self.base_url}/nacos/v1/ns/instance/list",
                params={
                    "serviceName": service_name,
                    "groupName": group,
                    "namespaceId": self.namespace,
                    "healthyOnly": "true",
                },
            )
            resp.raise_for_status()
            payload = resp.json()
            hosts = payload.get("hosts", [])
            return [(str(item["ip"]), int(item["port"])) for item in hosts if item.get("healthy")]
        except Exception as exc:
            logger.warning("拉取Nacos实例失败 service=%s err=%s", service_name, exc)
            return []

    async def get_config(self, data_id: str, group: str = "DEFAULT_GROUP") -> str | None:
        try:
            resp = await self._client.get(
                f"{self.base_url}/nacos/v1/cs/configs",
                params={"dataId": data_id, "group": group, "tenant": self.namespace},
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.text
        except Exception as exc:
            logger.warning("拉取Nacos配置失败 dataId=%s err=%s", data_id, exc)
            return None

    async def register_instance(self, service_name: str, ip: str, port: int, group: str = "DEFAULT_GROUP"):
        await self._client.post(
            f"{self.base_url}/nacos/v1/ns/instance",
            data={
                "serviceName": service_name,
                "groupName": group,
                "namespaceId": self.namespace,
                "ip": ip,
                "port": str(port),
                "ephemeral": "true",
                "healthy": "true",
                "weight": "1.0",
            },
        )

    async def send_beat(self, service_name: str, ip: str, port: int, group: str = "DEFAULT_GROUP"):
        beat_payload = {
            "ip": ip,
            "port": port,
            "serviceName": service_name,
            "cluster": "DEFAULT",
            "weight": 1.0,
            "ephemeral": True,
        }
        await self._client.put(
            f"{self.base_url}/nacos/v1/ns/instance/beat",
            params={
                "serviceName": service_name,
                "groupName": group,
                "namespaceId": self.namespace,
                "ephemeral": "true",
                "beat": json.dumps(beat_payload, ensure_ascii=False),
            },
        )

    async def deregister_instance(self, service_name: str, ip: str, port: int, group: str = "DEFAULT_GROUP"):
        await self._client.delete(
            f"{self.base_url}/nacos/v1/ns/instance",
            params={
                "serviceName": service_name,
                "groupName": group,
                "namespaceId": self.namespace,
                "ip": ip,
                "port": str(port),
                "ephemeral": "true",
            },
        )


def parse_gateway_config(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Nacos网关配置不是合法JSON，忽略动态配置")
        return {}
