# =============================================================================
# 云途 AI 行程规划 - 鉴权工具类
# =============================================================================
# 提供完整的用户认证与授权能力：
#   1. 密码加密：使用 bcrypt 算法对密码做哈希，不存储明文
#   2. JWT 生成：登录成功后签发 JWT，包含用户身份信息
#   3. JWT 验证：解析并校验 Token 有效性
#   4. FastAPI 鉴权依赖：get_current_user 可直接注入到路由中
#
# 使用方式：
#     from app.utils.auth_util import get_current_user
#     @router.get("/protected")
#     def protected_route(current_user: dict = Depends(get_current_user)): ...
# =============================================================================

from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET_KEY
from app.db import get_db
from app.models.db_models import User
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# ---------- JWT Bearer Token 提取器 ----------
_bearer_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    """对明文密码做 bcrypt 哈希，返回不可逆的哈希值。

    使用 bcrypt 自动生成随机盐值，数据库中只存储此哈希值。
    即使数据库泄露也不会暴露用户原始密码。
    """
    # bcrypt 限制密码最大 72 字节，超出部分截断
    password_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码是否与数据库中存储的哈希值匹配。"""
    password_bytes = plain_password.encode("utf-8")[:72]
    return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """根据用户数据签发 JWT Access Token。

    Args:
        data: 要编码到 Token 中的数据，至少包含 "sub"（用户名）
        expires_delta: 自定义过期时间，默认从配置读取

    Returns:
        编码后的 JWT 字符串
    """
    to_encode = data.copy()
    expire_minutes = expires_delta or timedelta(minutes=JWT_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expire_minutes
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """解析并验证 JWT Token，返回其中包含的数据。

    Token 过期、签名无效、格式错误等情况统一返回 None，不抛出异常。
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError as exc:
        logger.debug("JWT 解析失败: %s", exc)
        return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI 鉴权依赖项：从请求头 Bearer Token 中解析当前登录用户。

    此函数可直接作为 FastAPI 路由的 Depends 参数使用。
    鉴权失败时抛出 401 HTTPException。

    Args:
        credentials: 从 Authorization 头提取的 Bearer Token
        db: 数据库会话

    Returns:
        当前登录用户的 ORM 对象

    Raises:
        HTTPException(401): Token 无效、过期或用户不存在
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="登录凭证无效或已过期，请重新登录。",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username: str | None = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=401,
            detail="Token 中缺少用户标识。",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="用户不存在或已被删除。",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: Session = Depends(get_db),
) -> User | None:
    """可选鉴权依赖项：有 Token 时返回用户，无 Token 时返回 None。

    用于既允许登录用户访问、也允许匿名访问的接口。
    """
    if credentials is None:
        return None

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        return None

    username = payload.get("sub")
    if username is None:
        return None

    return db.query(User).filter(User.username == username).first()