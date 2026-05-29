# =============================================================================
# 云途 AI 行程规划 - 接口限流工具
# =============================================================================
# 基于 Redis 实现滑动窗口限流，防止恶意高频请求。
# Redis 不可用时自动降级放行，保证主流程不受影响。
#
# 使用方式：
#     from app.utils.rate_limit import RateLimiter
#     limiter = RateLimiter(max_requests=10, window_seconds=60)
#     @router.post("/xxx")
#     def handler(..., _rate=Depends(limiter)): ...
# =============================================================================

from __future__ import annotations

import time
from typing import Any

from fastapi import HTTPException, Request

from app.config import (
    RATE_LIMIT_GENERATE_PER_MINUTE,
    RATE_LIMIT_PER_MINUTE,
    REDIS_KEY_PREFIX,
)
from app.services.cache_service import _get_redis_client
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class RateLimiter:
    """基于 Redis 的滑动窗口速率限制器。

    使用 Redis 有序集合（Sorted Set）实现，每个请求以时间戳为 score 写入，
    查询时只统计窗口内的请求数。相比固定窗口，滑动窗口能更平滑地限流。
    """

    def __init__(
        self,
        max_requests: int,
        window_seconds: int = 60,
        key_prefix: str = "rate_limit",
    ) -> None:
        """初始化限流器。

        Args:
            max_requests: 时间窗口内允许的最大请求数
            window_seconds: 时间窗口大小（秒），默认 60 秒
            key_prefix: Redis Key 前缀
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix

    async def __call__(self, request: Request) -> None:
        """FastAPI 依赖项入口：检查当前请求是否被限流。

        以客户端 IP + 接口路径作为限流粒度，不同接口之间互不影响。
        """
        if self.max_requests <= 0:
            return  # 不限流

        redis_client = _get_redis_client()
        if redis_client is None:
            return  # Redis 不可用时放行，不影响正常业务

        # 按 IP + 路径做限流粒度
        client_ip = _get_client_ip(request)
        path = request.url.path
        rate_key = f"{REDIS_KEY_PREFIX}:{self.key_prefix}:{client_ip}:{path}"

        allowed = self._check_and_increment(redis_client, rate_key)
        if not allowed:
            logger.warning("接口限流触发: ip=%s path=%s limit=%d/%ds",
                           client_ip, path, self.max_requests, self.window_seconds)
            raise HTTPException(
                status_code=429,
                detail=f"请求过于频繁，请 {self.window_seconds} 秒后再试。",
            )

    def _check_and_increment(self, redis_client: Any, key: str) -> bool:
        """滑动窗口检查：清理过期记录，统计当前窗口请求数，判断是否放行。

        Returns:
            True 表示放行，False 表示触发限流。
        """
        now = time.time()
        window_start = now - self.window_seconds

        try:
            # 使用 pipeline 保证原子性
            pipe = redis_client.pipeline()
            # 清理窗口外的过期记录
            pipe.zremrangebyscore(key, 0, window_start)
            # 统计当前窗口内请求数
            pipe.zcard(key)
            # 记录本次请求
            pipe.zadd(key, {str(now): now})
            # 设置 Key 过期时间（窗口的 2 倍，避免僵尸 Key）
            pipe.expire(key, self.window_seconds * 2)
            _, current_count, _, _ = pipe.execute()

            return current_count < self.max_requests
        except Exception as exc:
            logger.debug("Redis 限流检查异常，放行请求: %s", exc)
            return True  # Redis 异常时放行


def _get_client_ip(request: Request) -> str:
    """从请求中获取客户端真实 IP。

    优先从 X-Forwarded-For 头获取（适用于反向代理 / CDN 场景），
    回退到直接连接的客户端 IP。
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = request.client
    if client:
        return client.host
    return "unknown"


# ---------- 预置限流器实例 ----------

# 全局限流：所有接口共用
global_limiter = RateLimiter(
    max_requests=RATE_LIMIT_PER_MINUTE,
    window_seconds=60,
    key_prefix="global",
)

# 行程生成接口专用限流（更严格）
generate_limiter = RateLimiter(
    max_requests=RATE_LIMIT_GENERATE_PER_MINUTE,
    window_seconds=60,
    key_prefix="generate",
)