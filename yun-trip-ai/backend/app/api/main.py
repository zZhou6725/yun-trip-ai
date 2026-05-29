# =============================================================================
# 云途 AI 行程规划 - FastAPI 应用入口
# =============================================================================
# 负责：
#   1. 创建 FastAPI 实例并注册路由
#   2. 配置 CORS 中间件（来源白名单从 .env 统一读取）
#   3. 接入项目日志系统（控制台 + 文件双输出）
#   4. 注册全局异常处理器，统一错误响应格式
# =============================================================================

import traceback
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.export import router as export_router
from app.api.routes.trip import router as trip_router
from app.api.routes.user import router as user_router
from app.api.routes.weather import router as weather_router
from app.config import CORS_ORIGINS, REDIS_ENABLED, SERVER_DEBUG
from app.utils.logger import get_log_dir, setup_logger

# ---------- 初始化日志 ----------
logger = setup_logger(__name__)


# ---------- 应用生命周期 ----------
@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI 应用启动/关闭时的回调。"""
    # 启动时初始化数据库表结构
    from app.config import Base, engine
    from app.models.db_models import TripRecord, User  # noqa: F401 确保模型注册到 Base

    Base.metadata.create_all(bind=engine)

    logger.info("=" * 60)
    logger.info("云途 AI 行程规划后端服务启动中...")
    logger.info("日志系统已初始化，日志文件存放于: %s", get_log_dir())
    logger.info("CORS 白名单: %s", CORS_ORIGINS)
    logger.info("Redis 缓存: %s", "已启用" if REDIS_ENABLED else "未启用")
    logger.info("数据库表结构已就绪")
    logger.info("=" * 60)
    yield
    logger.info("云途 AI 行程规划后端服务正在关闭...")


# ---------- 创建 FastAPI 应用 ----------
app = FastAPI(
    title="云途 AI 行程规划 - 智能旅行助手后端",
    description="基于大模型 + RAG 的智能旅行行程规划 API，支持行程生成、编辑、导出等。",
    version="0.1.0",
    lifespan=lifespan,
    debug=SERVER_DEBUG,
)


# ---------- CORS 中间件 ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# 全局异常处理器
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """捕获所有未处理的异常，返回统一结构的错误响应并记录完整堆栈。"""
    logger.error(
        "未处理的异常 | path=%s method=%s | %s: %s",
        request.url.path,
        request.method,
        type(exc).__name__,
        str(exc),
    )
    logger.debug("完整堆栈:\n%s", traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={
            "detail": "服务器内部错误，请稍后重试。",
            "error_type": type(exc).__name__,
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """捕获参数校验类异常，返回 422 状态码。"""
    logger.warning(
        "参数校验失败 | path=%s method=%s | %s",
        request.url.path,
        request.method,
        str(exc),
    )
    return JSONResponse(
        status_code=422,
        content={
            "detail": str(exc),
            "error_type": "ValueError",
        },
    )


# =============================================================================
# 基础接口
# =============================================================================

@app.get("/")
def read_root() -> dict[str, str]:
    """根路径接口：确认后端服务已启动。"""
    logger.debug("根路径被访问")
    return {"message": "云途 AI 行程规划后端服务运行中。"}


@app.get("/health")
def health_check() -> dict[str, str]:
    """健康检查接口：供容器编排或监控系统探测。"""
    return {"status": "ok"}


# ---------- 注册业务路由 ----------
app.include_router(user_router)
app.include_router(trip_router)
app.include_router(export_router)
app.include_router(weather_router)

logger.info("路由注册完成: user, trip, export, weather")