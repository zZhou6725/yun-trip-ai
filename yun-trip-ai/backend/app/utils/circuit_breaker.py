# =============================================================================
# 云途 AI 行程规划 - 熔断器
# =============================================================================
# 当外部依赖连续失败超过阈值时，自动熔断一段时间，避免雪崩。
# 支持三种状态:
#   CLOSED    — 正常，允许请求通过
#   OPEN      — 熔断中，直接拒绝请求
#   HALF_OPEN — 试探性恢复，允许一次请求探测
# =============================================================================

from __future__ import annotations

import time
from collections.abc import Callable
from enum import Enum, auto
from functools import wraps
from typing import Any, TypeVar

from app.utils.logger import setup_logger

logger = setup_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class CircuitState(Enum):
    CLOSED = auto()
    OPEN = auto()
    HALF_OPEN = auto()


class CircuitBreaker:
    """对外部服务的熔断保护器。"""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max: int = 1,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max = half_open_max

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._half_open_count = 0

    @property
    def state(self) -> CircuitState:
        return self._state

    def on_success(self):
        if self._state == CircuitState.HALF_OPEN:
            logger.info("熔断器 %s 试探成功，恢复关闭状态", self.name)
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_count = 0

    def on_failure(self, error: Exception):
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            logger.warning("熔断器 %s 试探失败: %s", self.name, error)
            self._state = CircuitState.OPEN
            self._half_open_count = 0
        elif self._failure_count >= self.failure_threshold:
            logger.error(
                "熔断器 %s 触发熔断！连续失败 %d 次，进入 OPEN 状态 %0.0fs",
                self.name, self._failure_count, self.recovery_timeout,
            )
            self._state = CircuitState.OPEN
            self._half_open_count = 0

    def allow_request(self) -> bool:
        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            elapsed = time.time() - self._last_failure_time
            if elapsed >= self.recovery_timeout:
                logger.info("熔断器 %s 进入 HALF_OPEN 状态，允许试探请求", self.name)
                self._state = CircuitState.HALF_OPEN
                self._half_open_count = 0
                return True
            return False

        if self._state == CircuitState.HALF_OPEN:
            if self._half_open_count < self.half_open_max:
                self._half_open_count += 1
                return True
            return False

        return True


# =============================================================================
# 熔断装饰器
# =============================================================================

def with_circuit_breaker(breaker: CircuitBreaker):
    """在函数调用上附加熔断保护。"""

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not breaker.allow_request():
                raise CircuitBreakerOpenError(
                    f"熔断器 {breaker.name} 已打开，拒绝请求"
                )
            try:
                result = func(*args, **kwargs)
                breaker.on_success()
                return result
            except Exception as exc:
                breaker.on_failure(exc)
                raise

        return wrapper  # type: ignore[return-value]

    return decorator


class CircuitBreakerOpenError(Exception):
    """熔断器打开时抛出的异常。"""
    pass


# =============================================================================
# 全局熔断器实例（单例）
# =============================================================================

_llm_circuit_breaker: CircuitBreaker | None = None
_redis_circuit_breaker: CircuitBreaker | None = None
_amap_circuit_breaker: CircuitBreaker | None = None


def get_llm_circuit_breaker() -> CircuitBreaker:
    global _llm_circuit_breaker
    if _llm_circuit_breaker is None:
        _llm_circuit_breaker = CircuitBreaker(
            name="LLM",
            failure_threshold=5,
            recovery_timeout=120.0,
        )
    return _llm_circuit_breaker


def get_redis_circuit_breaker() -> CircuitBreaker:
    global _redis_circuit_breaker
    if _redis_circuit_breaker is None:
        _redis_circuit_breaker = CircuitBreaker(
            name="Redis",
            failure_threshold=3,
            recovery_timeout=60.0,
        )
    return _redis_circuit_breaker


def get_amap_circuit_breaker() -> CircuitBreaker:
    global _amap_circuit_breaker
    if _amap_circuit_breaker is None:
        _amap_circuit_breaker = CircuitBreaker(
            name="Amap",
            failure_threshold=3,
            recovery_timeout=60.0,
        )
    return _amap_circuit_breaker