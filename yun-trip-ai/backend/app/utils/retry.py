# =============================================================================
# 云途 AI 行程规划 - 重试工具
# =============================================================================
# 提供指数退避 + 随机抖动（jitter）的重试装饰器。
# 使用方式：
#   @retry_on_failure(max_attempts=3, base_delay=1.0, backoff=2.0)
#   def call_llm(...):
#       ...
# =============================================================================

from __future__ import annotations

import functools
import random
import time
from collections.abc import Callable
from typing import Any, TypeVar

from app.utils.logger import setup_logger

logger = setup_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def retry_on_failure(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    backoff: float = 2.0,
    jitter: float = 0.1,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
):
    """指数退避重试装饰器，带随机抖动避免惊群效应。"""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_exception = exc
                    if attempt < max_attempts - 1:
                        delay = base_delay * (backoff ** attempt)
                        delay += random.uniform(0, jitter * delay)
                        logger.warning(
                            "%s 调用失败（尝试 %d/%d），%s: %s，%0.1fs 后重试",
                            func.__name__, attempt + 1, max_attempts,
                            type(exc).__name__, exc, delay,
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            "%s 调用失败（已达最大重试次数 %d），%s: %s",
                            func.__name__, max_attempts, type(exc).__name__, exc,
                        )
            raise last_exception  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    return decorator


def async_retry_on_failure(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    backoff: float = 2.0,
    jitter: float = 0.1,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
):
    """异步版指数退避重试装饰器。"""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_exception = exc
                    if attempt < max_attempts - 1:
                        delay = base_delay * (backoff ** attempt)
                        delay += random.uniform(0, jitter * delay)
                        logger.warning(
                            "%s 调用失败（尝试 %d/%d），%s: %s，%0.1fs 后重试",
                            func.__name__, attempt + 1, max_attempts,
                            type(exc).__name__, exc, delay,
                        )
                        await asyncio_sleep(delay)
                    else:
                        logger.error(
                            "%s 调用失败（已达最大重试次数 %d），%s: %s",
                            func.__name__, max_attempts, type(exc).__name__, exc,
                        )
            raise last_exception  # type: ignore[misc]

        return wrapper

    return decorator


async def asyncio_sleep(seconds: float) -> None:
    import asyncio
    await asyncio.sleep(seconds)