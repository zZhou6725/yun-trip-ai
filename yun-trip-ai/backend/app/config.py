# =============================================================================
# 云途 AI 行程规划 - 全局配置文件
# =============================================================================
# 所有环境变量统一从 backend/.env 加载，此处提供类型转换和默认值。
# 新增配置项时：先在 .env 和 .env.example 中声明，再在此处添加读取逻辑。
# =============================================================================

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# =============================================================================
# 基础路径：定位到 backend/ 目录
# =============================================================================
BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")


# =============================================================================
# 数据库配置（SQLite）
# =============================================================================
DB_DIR = BACKEND_DIR / "db"
DB_DIR.mkdir(parents=True, exist_ok=True)

SQLITE_DB_PATH = DB_DIR / "app.db"
DATABASE_URL = f"sqlite:///{SQLITE_DB_PATH.as_posix()}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# =============================================================================
# 大模型配置（LLM）
# =============================================================================
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai_compatible")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "1"))


# =============================================================================
# RAG / 向量库配置（Chroma / Milvus Lite + Embedding + Rerank）
# =============================================================================
VECTOR_STORE = os.getenv("VECTOR_STORE", "chroma")  # chroma | milvus

_chroma_db_dir_raw = Path(os.getenv("CHROMA_DB_DIR", "db/chroma_db"))
CHROMA_DB_DIR = (
    _chroma_db_dir_raw
    if _chroma_db_dir_raw.is_absolute()
    else BACKEND_DIR / _chroma_db_dir_raw
)
CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)

_milvus_db_dir_raw = Path(os.getenv("MILVUS_DB_DIR", "db/milvus_db"))
MILVUS_DB_DIR = (
    _milvus_db_dir_raw
    if _milvus_db_dir_raw.is_absolute()
    else BACKEND_DIR / _milvus_db_dir_raw
)
MILVUS_DB_DIR.mkdir(parents=True, exist_ok=True)
MILVUS_COLLECTION_NAME = os.getenv("MILVUS_COLLECTION_NAME", "travel_guides")

CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "travel_guides")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "10"))
RERANK_MODEL = os.getenv("RERANK_MODEL", "qwen3-rerank")


# =============================================================================
# Redis / 缓存配置
# =============================================================================
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "false").lower() == "true"
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
REDIS_KEY_PREFIX = os.getenv("REDIS_KEY_PREFIX", "trip_planner")
REDIS_DEFAULT_TTL_SECONDS = int(os.getenv("REDIS_DEFAULT_TTL_SECONDS", "1800"))
REDIS_WEATHER_TTL_SECONDS = int(os.getenv("REDIS_WEATHER_TTL_SECONDS", "1800"))
REDIS_MAP_TTL_SECONDS = int(os.getenv("REDIS_MAP_TTL_SECONDS", "86400"))
REDIS_RAG_TTL_SECONDS = int(os.getenv("REDIS_RAG_TTL_SECONDS", "21600"))
REDIS_RERANK_TTL_SECONDS = int(os.getenv("REDIS_RERANK_TTL_SECONDS", "21600"))


# =============================================================================
# 高德地图配置（Amap）
# =============================================================================
AMAP_API_KEY = os.getenv("AMAP_API_KEY", "")
AMAP_BASE_URL = os.getenv("AMAP_BASE_URL", "https://restapi.amap.com/v3")
AMAP_DEFAULT_CITY = os.getenv("AMAP_DEFAULT_CITY", "")
AMAP_TIMEOUT_SECONDS = int(os.getenv("AMAP_TIMEOUT_SECONDS", "20"))
ENABLE_AMAP_ENRICHMENT = os.getenv("ENABLE_AMAP_ENRICHMENT", "false").lower() == "true"


# =============================================================================
# 服务器配置
# =============================================================================
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
SERVER_DEBUG = os.getenv("SERVER_DEBUG", "false").lower() == "true"

# CORS 白名单：从逗号分隔字符串解析为列表
_cors_raw = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173",
)
CORS_ORIGINS = [origin.strip() for origin in _cors_raw.split(",") if origin.strip()]


# =============================================================================
# 日志配置
# =============================================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_MAX_SIZE_MB = int(os.getenv("LOG_MAX_SIZE_MB", "10"))
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "7"))


# =============================================================================
# JWT / 鉴权配置
# =============================================================================
# JWT 签名密钥（生产环境必须更换为强随机字符串）
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "yun-trip-ai-default-secret-change-me")
# JWT 签名算法
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
# Token 过期时间（分钟），默认 1440 分钟 = 24 小时
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))


# =============================================================================
# 接口限流配置
# =============================================================================
# 全局接口限流：每分钟最大请求数（0 表示不限流）
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
# 行程生成接口限流：每分钟最大请求数（生成接口开销大，单独限制）
RATE_LIMIT_GENERATE_PER_MINUTE = int(os.getenv("RATE_LIMIT_GENERATE_PER_MINUTE", "5"))
