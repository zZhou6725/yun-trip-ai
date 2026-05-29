# =============================================================================
# 云途 AI 行程规划 - 数据库连接管理
# =============================================================================
# 提供 SQLAlchemy 会话的 FastAPI 依赖注入（Depends），确保每次请求使用独立
# 的数据库会话，请求结束后自动关闭，避免连接泄漏。
#
# 使用方式：
#     from app.db import get_db
#     @router.post("/xxx")
#     def handler(db: Session = Depends(get_db)): ...
# =============================================================================

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.config import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖项：为每个请求提供一个独立的数据库会话。

    请求进入时创建新会话，请求结束后自动关闭，确保连接资源不泄漏。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()