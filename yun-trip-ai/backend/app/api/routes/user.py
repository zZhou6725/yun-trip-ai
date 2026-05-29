# =============================================================================
# 云途 AI 行程规划 - 用户认证路由
# =============================================================================
# 提供用户注册与登录接口：
#   POST /user/register - 用户注册（返回用户信息）
#   POST /user/login    - 用户登录（返回 JWT Token）
#
# 密码使用 bcrypt 哈希存储，Token 使用 HS256 算法签名。
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.db_models import User
from app.models.schemas import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.utils.auth_util import create_access_token, get_current_user, hash_password, verify_password
from app.utils.logger import setup_logger

router = APIRouter(prefix="/user", tags=["user"])

logger = setup_logger(__name__)


@router.post("/register", response_model=UserResponse, status_code=201)
def register(request: UserRegisterRequest, db: Session = Depends(get_db)) -> UserResponse:
    """用户注册接口：创建新用户并返回用户信息。

    规则：
    - 用户名和邮箱必须全局唯一
    - 密码长度不小于 6 位
    - 密码使用 bcrypt 哈希后存储，不保留明文
    """
    # 检查用户名是否已被占用
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user is not None:
        raise HTTPException(status_code=409, detail="用户名已被占用，请更换后重试。")

    # 检查邮箱是否已被注册
    existing_email = db.query(User).filter(User.email == request.email).first()
    if existing_email is not None:
        raise HTTPException(status_code=409, detail="该邮箱已被注册，请直接登录或使用其他邮箱。")

    # 创建用户（密码哈希后存储）
    new_user = User(
        username=request.username,
        email=request.email,
        hashed_password=hash_password(request.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info("新用户注册成功: username=%s, user_id=%d", new_user.username, new_user.id)
    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        created_at=new_user.created_at,
    )


@router.post("/login", response_model=TokenResponse)
def login(request: UserLoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """用户登录接口：验证用户名密码，返回 JWT Access Token。

    Token 过期时间由配置 JWT_EXPIRE_MINUTES 控制，默认 24 小时。
    后续请求在 Authorization 头中携带 `Bearer <token>` 即可鉴权。
    """
    # 查找用户
    user = db.query(User).filter(User.username == request.username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误。")

    # 验证密码
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误。")

    # 签发 JWT Token
    access_token = create_access_token(data={"sub": user.username, "user_id": user.id})

    logger.info("用户登录成功: username=%s, user_id=%d", user.username, user.id)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            created_at=user.created_at,
        ),
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """获取当前登录用户信息（需携带有效 Token）。"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        created_at=current_user.created_at,
    )