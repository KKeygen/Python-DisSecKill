"""Nacos服务注册 —— 从共用模块 common/nacos_registry.py 导入"""
# noqa: F401 — 公共模块由 Dockerfile 从 services/common/ 复制进来
from app._nacos_common import NacosRegistry  # noqa: F401
