# =============================================================================
# 云途 AI 行程规划 - Redis 缓存服务（优化版）
# =============================================================================
# 提供：
#   - 按业务类型分级 TTL（天气 30min / 地图 24h / RAG 6h / 默认 30min）
#   - 缓存穿透防护：null 值缓存，防止大量不存在的 key 击穿到 DB/API
#   - Redis 不可用时自动降级，不阻塞主流程
# =============================================================================

from __future__ import annotations

import json
from enum import Enum
from typing import Any

from app.config import (
    REDIS_DEFAULT_TTL_SECONDS,
    REDIS_ENABLED,
    REDIS_KEY_PREFIX,
    REDIS_MAP_TTL_SECONDS,
    REDIS_RAG_TTL_SECONDS,
    REDIS_RERANK_TTL_SECONDS,
    REDIS_URL,
    REDIS_WEATHER_TTL_SECONDS,
)
from app.utils.circuit_breaker import CircuitBreakerOpenError, get_redis_circuit_breaker
from app.utils.logger import setup_logger

try:
    import redis
except ImportError:
    redis = None

logger = setup_logger(__name__)
_redis_client: Any | None = None
_redis_unavailable_logged = False

# 缓存穿透防护：空值缓存 TTL（较短，避免长期缓存不存在的数据）
NULL_CACHE_TTL = 60
NULL_CACHE_MARKER = "__CACHE_NULL__"


class CacheCategory(Enum):
    DEFAULT = ("default", REDIS_DEFAULT_TTL_SECONDS)
    WEATHER = ("weather", REDIS_WEATHER_TTL_SECONDS)
    MAP = ("map", REDIS_MAP_TTL_SECONDS)
    RAG = ("rag", REDIS_RAG_TTL_SECONDS)
    RERANK = ("rerank", REDIS_RERANK_TTL_SECONDS)

    def __init__(self, prefix: str, ttl: int):
        self.prefix = prefix
        self.ttl = ttl


def _build_key(category: CacheCategory, key: str) -> str:
    return f"{REDIS_KEY_PREFIX}:{category.prefix}:{key}"


def _get_redis_client():
    global _redis_client, _redis_unavailable_logged

    if not REDIS_ENABLED:
        return None
    if redis is None:
        if not _redis_unavailable_logged:
            logger.warning("Redis 已启用但未安装 redis 依赖，缓存功能跳过")
            _redis_unavailable_logged = True
        return None
    if _redis_client is not None:
        return _redis_client

    breaker = get_redis_circuit_breaker()
    if not breaker.allow_request():
        logger.warning("Redis 熔断器已打开，跳过本次连接")
        return None

    try:
        client = redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=3)
        client.ping()
        breaker.on_success()
        _redis_client = client
        return _redis_client
    except Exception as exc:
        breaker.on_failure(exc)
        if not _redis_unavailable_logged:
            logger.warning("Redis 连接失败，缓存功能跳过: %s", exc)
            _redis_unavailable_logged = True
        return None


def get_cached_json(
    key: str,
    category: CacheCategory = CacheCategory.DEFAULT,
) -> Any | None:
    """读取缓存。Hit → 返回数据；miss → 返回 None；null 缓存 → 返回 NULL_CACHE_MARKER。"""
    client = _get_redis_client()
    if client is None:
        return None

    try:
        raw = client.get(_build_key(category, key))
        if raw is None:
            return None
        if raw == NULL_CACHE_MARKER:
            return NULL_CACHE_MARKER
        return json.loads(raw)
    except Exception as exc:
        logger.debug("读取缓存失败: %s", exc)
        return None


def set_cached_json(
    key: str,
    value: Any,
    category: CacheCategory = CacheCategory.DEFAULT,
    expire_seconds: int | None = None,
) -> None:
    """写入缓存。value 为 None/空时写入 null 标记防止穿透。"""
    client = _get_redis_client()
    if client is None:
        return

    ttl = expire_seconds if expire_seconds is not None else category.ttl
    try:
        if value is None or value == [] or value == {}:
            client.set(_build_key(category, key), NULL_CACHE_MARKER, ex=NULL_CACHE_TTL)
        else:
            client.set(
                _build_key(category, key),
                json.dumps(value, ensure_ascii=False),
                ex=ttl,
            )
    except Exception as exc:
        logger.debug("写入缓存失败: %s", exc)


def cache_or_fetch(
    key: str,
    fetcher,
    category: CacheCategory = CacheCategory.DEFAULT,
    expire_seconds: int | None = None,
) -> Any:
    """缓存穿透安全读取：先查缓存，miss 才调 fetcher 并回填。"""
    cached = get_cached_json(key, category)
    if cached is not None:
        if cached == NULL_CACHE_MARKER:
            return None
        return cached

    try:
        value = fetcher()
    except Exception as exc:
        logger.warning("fetcher 调用失败: %s", exc)
        return None

    set_cached_json(key, value, category, expire_seconds)
    return value


def invalidate_cache(key: str, category: CacheCategory = CacheCategory.DEFAULT) -> None:
    """主动清除缓存。"""
    client = _get_redis_client()
    if client is None:
        return
    try:
        client.delete(_build_key(category, key))
    except Exception as exc:
        logger.debug("清除缓存失败: %s", exc)