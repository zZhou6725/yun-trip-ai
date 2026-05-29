# =============================================================================
# 云途 AI 行程规划 - 日志工具类
# =============================================================================
# 提供控制台彩色输出 + 文件持久化双通道日志能力，支持按大小自动轮转。
# 使用方式：
#     from app.utils.logger import setup_logger
#     logger = setup_logger(__name__)
#     logger.info("这是一条日志")
# =============================================================================

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


class _ColoredFormatter(logging.Formatter):
    """控制台日志格式化器：按日志级别输出不同颜色，Windows 兼容降级。"""

    # ANSI 颜色代码
    _COLORS = {
        "DEBUG": "\033[36m",        # 青色
        "INFO": "\033[32m",         # 绿色
        "WARNING": "\033[33m",      # 黄色
        "ERROR": "\033[31m",        # 红色
        "CRITICAL": "\033[1;31m",   # 加粗红色
    }
    _RESET = "\033[0m"

    @staticmethod
    def _supports_color() -> bool:
        """检测当前终端是否支持 ANSI 颜色输出。"""
        # Windows cmd/powershell 老版本不支持，但 Windows Terminal 支持
        if not sys.stdout.isatty():
            return False
        if os.name == "nt":
            # Windows Terminal 会设置 WT_SESSION 环境变量
            return "WT_SESSION" in os.environ or "TERM" in os.environ
        return True

    def __init__(self, fmt: str | None = None, datefmt: str | None = None):
        super().__init__(fmt, datefmt)
        self._use_color = self._supports_color()

    def format(self, record: logging.LogRecord) -> str:
        # 先获取原始格式化结果
        log_message = super().format(record)
        if not self._use_color:
            return log_message
        color = self._COLORS.get(record.levelname)
        if color is None:
            return log_message
        return f"{color}{log_message}{self._RESET}"


# 全局单例：确保 setup_logger 不会被重复初始化
_logger_initialized: bool = False
_default_logger: Optional[logging.Logger] = None
_log_dir_used: Optional[str] = None


def setup_logger(
    name: str | None = None,
    *,
    log_level: str | None = None,
    log_dir: str | None = None,
    max_size_mb: int | None = None,
    backup_count: int | None = None,
    force: bool = False,
) -> logging.Logger:
    """创建或获取已配置好的 logger 实例。

    首次调用时会初始化全局日志系统（从环境变量读取配置），后续调用直接返回指定 name 的 logger。
    控制台输出带颜色区分，文件输出为纯文本并自动按大小轮转。

    Args:
        name: logger 名称，通常传入 __name__
        log_level: 日志级别，None 时从环境变量 LOG_LEVEL 读取，默认 INFO
        log_dir: 日志目录，None 时从环境变量 LOG_DIR 读取，默认 "logs"
        max_size_mb: 单文件最大大小（MB），None 时从 LOG_MAX_SIZE_MB 读取，默认 10
        backup_count: 保留的历史文件数，None 时从 LOG_BACKUP_COUNT 读取，默认 7
        force: 是否强制重新初始化（用于测试场景）

    Returns:
        配置完毕的 logging.Logger 实例
    """
    global _logger_initialized, _default_logger, _log_dir_used  # noqa: PLW0603

    # 读取配置：显式参数 > 环境变量 > 默认值
    resolved_level = (
        log_level
        or os.getenv("LOG_LEVEL", "INFO").upper()
    )
    resolved_dir = (
        log_dir
        or os.getenv("LOG_DIR", "logs")
    )
    resolved_max_mb = (
        max_size_mb
        or int(os.getenv("LOG_MAX_SIZE_MB", "10"))
    )
    resolved_backup = (
        backup_count
        or int(os.getenv("LOG_BACKUP_COUNT", "7"))
    )

    # 只在首次调用时配置 root logger 的 handler
    if not _logger_initialized or force:
        _logger_initialized = True

        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, resolved_level, logging.INFO))

        # 清除已有的 handler，避免重复添加
        root_logger.handlers.clear()

        # ---------- 控制台处理器 ----------
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, resolved_level, logging.INFO))
        console_fmt = _ColoredFormatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(console_fmt)
        root_logger.addHandler(console_handler)

        # ---------- 文件处理器（带轮转） ----------
        log_path = Path(resolved_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        _log_dir_used = str(log_path.resolve())

        file_handler = RotatingFileHandler(
            filename=log_path / "app.log",
            maxBytes=resolved_max_mb * 1024 * 1024,  # MB → Bytes
            backupCount=resolved_backup,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)  # 文件记录所有级别日志
        file_fmt = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)-25s | %(filename)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_fmt)
        root_logger.addHandler(file_handler)

        # 降低第三方库的日志噪音
        for noisy_lib in ("chromadb", "httpx", "httpcore", "urllib3", "sqlalchemy.engine"):
            logging.getLogger(noisy_lib).setLevel(logging.WARNING)

    # 返回指定 name 的 logger
    logger = logging.getLogger(name)
    _default_logger = logger
    return logger


def get_log_dir() -> str | None:
    """返回当前日志文件存放目录的绝对路径（仅在 setup_logger 之后有效）。"""
    return _log_dir_used


def get_logger(name: str | None = None) -> logging.Logger:
    """获取已初始化的 logger 实例（便捷函数，不触发重新初始化）。"""
    return logging.getLogger(name)