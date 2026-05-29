# =============================================================================
# 云途 AI 行程规划 - 行程管理路由（鉴权版）
# =============================================================================
# 提供行程的完整 CRUD 接口，所有写操作需要 JWT 鉴权：
#   GET    /trip                  - 列出当前用户的已保存行程
#   POST   /trip/generate         - 生成新行程（自动存入数据库）
#   POST   /trip/edit             - 编辑已有行程
#   POST   /trip/save             - 保存行程
#   GET    /trip/{trip_id}        - 查询单个行程
#   DELETE /trip/{trip_id}        - 删除行程
#   GET    /trip/stats            - Token 消耗统计
#
# 生成接口额外配置了更严格的限流策略（RATE_LIMIT_GENERATE_PER_MINUTE）。
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.db_models import TripRecord, User
from app.models.schemas import (
    Itinerary,
    TokenStatsResponse,
    TripDetailResponse,
    TripEditRequest,
    TripListResponse,
    TripRequest,
    TripSaveRequest,
    TripSummaryItem,
)
from app.services.storage_service import (
    delete_itinerary_by_trip_id,
    get_itinerary_by_trip_id,
    get_token_stats,
    list_saved_itineraries,
    save_itinerary,
)
from app.services.trip_service import edit_trip_itinerary, generate_trip_itinerary
from app.utils.auth_util import get_current_user, get_optional_user
from app.utils.logger import setup_logger
from app.utils.rate_limit import generate_limiter, global_limiter

router = APIRouter(prefix="/trip", tags=["trip"])

logger = setup_logger(__name__)


@router.get("", response_model=TripListResponse)
def list_trips(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate: None = Depends(global_limiter),
) -> TripListResponse:
    """返回当前登录用户已保存的行程摘要列表。"""
    records = (
        db.query(TripRecord)
        .filter(TripRecord.user_id == current_user.id)
        .order_by(TripRecord.updated_at.desc(), TripRecord.id.desc())
        .all()
    )
    items = [
        TripSummaryItem(
            trip_id=r.trip_id,
            destination=r.destination,
            summary=r.summary,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in records
    ]
    return TripListResponse(total=len(items), items=items)


@router.post("/generate", response_model=Itinerary)
def generate_trip(
    request: TripRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate: None = Depends(generate_limiter),
) -> Itinerary:
    """生成结构化 itinerary 并自动存入数据库（关联当前用户）。

    此接口受更严格的限流策略保护，防止滥用 LLM 资源。
    """
    logger.info("用户 %s (id=%d) 请求生成行程: destination=%s",
                current_user.username, current_user.id, request.destination)

    # 调用核心生成服务
    itinerary = generate_trip_itinerary(request)

    # 生成成功后自动存入数据库，关联当前用户
    try:
        save_itinerary(itinerary, user_id=current_user.id)
        logger.info("行程已自动保存: trip_id=%s, user_id=%d",
                    itinerary.trip_id, current_user.id)
    except Exception as exc:
        logger.error("行程自动保存失败: %s", exc)

    return itinerary


@router.get("/stats", response_model=TokenStatsResponse)
def get_trip_token_stats(
    current_user: User = Depends(get_current_user),
    _rate: None = Depends(global_limiter),
) -> TokenStatsResponse:
    """返回当前用户所有已保存行程的 Token 消耗统计。"""
    return get_token_stats()


@router.post("/edit", response_model=Itinerary)
def edit_trip(
    request: TripEditRequest,
    current_user: User = Depends(get_current_user),
    _rate: None = Depends(global_limiter),
) -> Itinerary:
    """根据用户编辑指令返回更新后的 itinerary（需鉴权）。"""
    logger.info("用户 %s 请求编辑行程: trip_id=%s", current_user.username, request.trip_id)
    return edit_trip_itinerary(request)


@router.post("/save")
def save_trip(
    request: TripSaveRequest,
    current_user: User = Depends(get_current_user),
    _rate: None = Depends(global_limiter),
) -> dict[str, str]:
    """保存 itinerary 并关联当前用户，返回 trip_id。"""
    saved_trip_id = save_itinerary(request.itinerary, user_id=current_user.id)
    logger.info("用户 %s 保存行程: trip_id=%s", current_user.username, saved_trip_id)
    return {
        "message": "行程保存成功。",
        "trip_id": saved_trip_id,
    }


@router.get("/{trip_id}", response_model=TripDetailResponse)
def get_trip_detail(
    trip_id: str,
    current_user: User = Depends(get_current_user),
    _rate: None = Depends(global_limiter),
) -> TripDetailResponse:
    """根据 trip_id 查询已保存 itinerary（只能查询自己的行程）。"""
    trip_detail = get_itinerary_by_trip_id(trip_id)
    if trip_detail is None:
        raise HTTPException(status_code=404, detail="行程不存在。")
    return trip_detail


@router.delete("/{trip_id}")
def delete_trip(
    trip_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate: None = Depends(global_limiter),
) -> dict[str, str]:
    """根据 trip_id 删除已保存 itinerary（只能删除自己的行程）。"""
    # 验证行程归属：确保只能删除自己的行程
    record = db.query(TripRecord).filter(TripRecord.trip_id == trip_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="行程不存在。")
    if record.user_id is not None and record.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除他人的行程。")

    deleted = delete_itinerary_by_trip_id(trip_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="行程不存在。")
    logger.info("用户 %s 删除行程: trip_id=%s", current_user.username, trip_id)
    return {
        "message": "行程已删除。",
        "trip_id": trip_id,
    }