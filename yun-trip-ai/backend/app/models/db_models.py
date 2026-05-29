# =============================================================================
# 云途 AI 行程规划 - 数据库 ORM 模型
# =============================================================================
# 使用 SQLAlchemy 2.0 风格定义数据库表结构：
#   - User: 用户表（用户名、邮箱、密码哈希）
#   - TripRecord: 行程记录表（关联用户，存储完整 itinerary JSON 快照）
# =============================================================================

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import Base


class User(Base):
    """用户表：存储注册用户的基本信息与密码哈希。"""

    __tablename__ = "users"

    # 主键，自增
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 用户名，唯一索引，用于登录
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    # 邮箱，唯一索引
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    # bcrypt 加密后的密码哈希，不存储明文
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=False)
    # 注册时间
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 一对多关系：一个用户可拥有多个行程记录
    trips: Mapped[list["TripRecord"]] = relationship("TripRecord", back_populates="user")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"


class TripRecord(Base):
    """行程记录表：存储用户生成的完整 itinerary JSON 快照。"""

    __tablename__ = "trip_records"

    # 数据库内部主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 业务侧使用的 itinerary 标识
    trip_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    # 目的地
    destination: Mapped[str] = mapped_column(String(100))
    # 行程摘要
    summary: Mapped[str] = mapped_column(Text)
    # 完整 itinerary 的 JSON 字符串
    itinerary_json: Mapped[str] = mapped_column(Text)
    # 外键：关联到用户表，级联删除（用户删除时其所有行程一并删除）
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    # 更新时间（每次更新自动刷新）
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # 多对一关系：反向引用到用户
    user: Mapped["User"] = relationship("User", back_populates="trips")

    def __repr__(self) -> str:
        return f"<TripRecord(id={self.id}, trip_id='{self.trip_id}', destination='{self.destination}')>"