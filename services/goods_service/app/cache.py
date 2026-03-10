"""
商品详情页缓存服务

解决三大缓存问题：
- 缓存穿透：缓存空值，短TTL
- 缓存击穿：Redis分布式互斥锁，防止热点key过期时大量回源
- 缓存雪崩：TTL加随机偏移量，避免大量key同时过期
"""
import json
import asyncio
import random

import redis.asyncio as aioredis

from app.config import get_settings

settings = get_settings()

# 缓存Key前缀
CACHE_PREFIX = "goods:detail:"
NULL_PREFIX = "goods:null:"
LOCK_PREFIX = "goods:lock:"

# TTL配置（秒）
CACHE_TTL = 300        # 正常缓存5分钟
NULL_TTL = 60          # 空值缓存1分钟（防穿透）
LOCK_TTL = 10          # 分布式锁超时10秒（防击穿）
TTL_JITTER = 30        # TTL随机偏移量（防雪崩）

_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """获取Redis连接池（单例）"""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis_pool


async def get_goods_cache(goods_id: int) -> dict | None:
    """
    读取商品详情缓存（带穿透/击穿/雪崩防护）

    返回:
        dict: 商品详情数据
        None: 商品不存在（空值缓存命中或数据库确认不存在）

    异常:
        CacheMiss: 缓存未命中且未能获取锁，调用方应直接查库
    """
    r = await get_redis()
    cache_key = f"{CACHE_PREFIX}{goods_id}"

    # 1. 查缓存
    cached = await r.get(cache_key)
    if cached is not None:
        return json.loads(cached)

    # 2. 检查空值缓存（防穿透：不存在的商品ID不会每次打到数据库）
    null_key = f"{NULL_PREFIX}{goods_id}"
    if await r.exists(null_key):
        return None

    # 缓存未命中，返回None让调用方查库
    raise CacheMiss()


async def set_goods_cache(goods_id: int, data: dict) -> None:
    """
    写入商品缓存（TTL加随机偏移防雪崩）
    """
    r = await get_redis()
    cache_key = f"{CACHE_PREFIX}{goods_id}"
    # 防雪崩：TTL加随机偏移，避免大量key同时过期
    ttl = CACHE_TTL + random.randint(-TTL_JITTER, TTL_JITTER)
    await r.set(cache_key, json.dumps(data, default=str), ex=ttl)


async def set_null_cache(goods_id: int) -> None:
    """
    写入空值缓存（防穿透：对不存在的ID缓存空标记）
    """
    r = await get_redis()
    null_key = f"{NULL_PREFIX}{goods_id}"
    await r.set(null_key, "1", ex=NULL_TTL)


async def invalidate_goods_cache(goods_id: int) -> None:
    """使缓存失效（商品更新/删除时调用）"""
    r = await get_redis()
    await r.delete(f"{CACHE_PREFIX}{goods_id}", f"{NULL_PREFIX}{goods_id}")


async def acquire_rebuild_lock(goods_id: int) -> bool:
    """
    尝试获取缓存重建锁（防击穿：只允许一个请求回源查库）

    使用 Redis SETNX 实现分布式互斥锁
    """
    r = await get_redis()
    lock_key = f"{LOCK_PREFIX}{goods_id}"
    return await r.set(lock_key, "1", ex=LOCK_TTL, nx=True)


async def release_rebuild_lock(goods_id: int) -> None:
    """释放缓存重建锁"""
    r = await get_redis()
    lock_key = f"{LOCK_PREFIX}{goods_id}"
    await r.delete(lock_key)


class CacheMiss(Exception):
    """缓存未命中异常"""
    pass
