# =============================================================================
# 云途 AI 行程规划 - 行程规划 Agent
# =============================================================================
# 封装大模型调用逻辑：
#   1. JsonOutputParser 约束 LLM 输出结构化 JSON
#   2. 指数退避重试 + 熔断保护
#   3. LLM 调用失败 -> 返回 None，由 service 层回退到规则生成
# =============================================================================

from __future__ import annotations

from pydantic import BaseModel, Field

from app.agents.tools.rag_tool import get_destination_guide_context
from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MAX_RETRIES, LLM_MODEL, LLM_TIMEOUT_SECONDS
from app.models.schemas import DayPlan, TripEditRequest, TripRequest
from app.utils.circuit_breaker import CircuitBreakerOpenError, get_llm_circuit_breaker
from app.utils.json_parser import JsonOutputParser
from app.utils.logger import setup_logger
from app.utils.retry import retry_on_failure

logger = setup_logger(__name__)


# =============================================================================
# Pydantic Draft 模型
# =============================================================================

class PlannerDayDraft(BaseModel):
    day_index: int = Field(..., ge=1, description="第几天，从 1 开始")
    theme: str = Field(..., description="当天简短主题")
    spot_name: str = Field(..., description="当天主要景点名称")
    spot_description: str = Field(..., description="推荐该景点的简短理由")
    meal_name: str = Field(..., description="当天餐饮/餐厅建议")
    meal_notes: str = Field(..., description="简短用餐说明")
    daily_note: str = Field(..., description="当天简短规划备注")


class PlannerDraft(BaseModel):
    summary: str = Field(..., description="整趟旅行简短概述")
    tips: list[str] = Field(default_factory=list)
    days: list[PlannerDayDraft] = Field(default_factory=list)


class DayEditDraft(BaseModel):
    theme: str = Field(..., description="编辑后的当天主题")
    spot_name: str = Field(..., description="编辑后的主要景点名称")
    spot_description: str = Field(..., description="编辑后的景点说明")
    meal_name: str = Field(..., description="编辑后的餐饮名称")
    meal_notes: str = Field(..., description="编辑后的餐饮说明")
    daily_note: str = Field(..., description="编辑后的当天备注")


# =============================================================================
# JsonOutputParser 实例
# =============================================================================

planner_parser = JsonOutputParser(PlannerDraft)
day_edit_parser = JsonOutputParser(DayEditDraft)


# =============================================================================
# LLM 构建 + 调用
# =============================================================================

def _build_chat_llm():
    if not LLM_API_KEY:
        return None
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        return None
    return ChatOpenAI(
        model=LLM_MODEL,
        temperature=0.3,
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL or None,
        timeout=LLM_TIMEOUT_SECONDS,
        max_retries=1,
    )


def _extract_token_usage(response) -> dict[str, int]:
    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    metadata = getattr(response, "response_metadata", None) or {}
    token_usage = metadata.get("token_usage", {})
    if token_usage:
        usage["prompt_tokens"] = token_usage.get("prompt_tokens", 0)
        usage["completion_tokens"] = token_usage.get("completion_tokens", 0)
    return usage


@retry_on_failure(max_attempts=3, base_delay=2.0, backoff=2.0, jitter=0.2)
def _invoke_llm(llm, messages: list) -> tuple:
    """带重试的 LLM 调用。"""
    breaker = get_llm_circuit_breaker()
    if not breaker.allow_request():
        raise CircuitBreakerOpenError("LLM 熔断器已打开")
    try:
        response = llm.invoke(messages)
        breaker.on_success()
        return response
    except Exception as exc:
        breaker.on_failure(exc)
        raise


# =============================================================================
# 公开接口
# =============================================================================

def collect_trip_context(
    destination: str,
    preferences: list[str] | None = None,
    pace: str | None = None,
    special_notes: str | None = None,
    top_k: int = 5,
) -> tuple[list[str], dict[str, int], dict[str, int], dict[str, int]]:
    return get_destination_guide_context(
        destination=destination,
        preferences=preferences,
        pace=pace,
        special_notes=special_notes,
        top_k=top_k,
    )


def generate_planner_draft(
    request: TripRequest,
    rag_contexts: list[str],
    day_count: int,
) -> tuple[PlannerDraft | None, dict[str, int]]:
    empty_usage = {"prompt_tokens": 0, "completion_tokens": 0}
    llm = _build_chat_llm()
    if llm is None:
        return None, empty_usage

    guide_context = "\n\n".join(rag_contexts) if rag_contexts else "暂无本地攻略上下文。"

    format_instructions = planner_parser.get_format_instructions()

    system_prompt = (
        "你是一名旅行规划助手。请用中文生成简洁的结构化旅行草稿。\n"
        "你必须严格遵守用户给出的目的地、预算、节奏和本地攻略上下文。\n"
        + format_instructions
    )

    human_prompt = f"""
目的地：{request.destination}
出发日期：{request.start_date.isoformat()}
结束日期：{request.end_date.isoformat()}
天数：{day_count}
人数：{request.travelers}
预算：{request.budget}
偏好：{'、'.join(request.preferences) if request.preferences else '无特别偏好'}
节奏：{request.pace or '适中'}
饮食偏好：{'、'.join(request.dietary_preferences) if request.dietary_preferences else '无'}
酒店档次：{request.hotel_level or '舒适型'}
额外备注：{request.special_notes or '无'}

本地攻略上下文：
{guide_context}

要求：
1. 输出 {day_count} 天的 daily draft，day_index 从 1 到 {day_count}。
2. 每天只给一个主要景点、一个餐饮建议和一条当天备注。
3. 如果额外备注里有明确要求（想看日落、不想早起、拍照等），必须体现在对应天的安排中。
4. 每天安排符合"{request.pace or '适中'}"节奏。
5. 餐饮建议优先使用本地攻略上下文中出现的特色餐饮。
"""

    logger.info("调用 LLM: model=%s, base_url=%s, timeout=%ds",
                LLM_MODEL, LLM_BASE_URL or '<DEFAULT>', LLM_TIMEOUT_SECONDS)

    try:
        response = _invoke_llm(llm, [("system", system_prompt), ("human", human_prompt)])
    except (CircuitBreakerOpenError, Exception) as exc:
        logger.warning("LLM 调用失败: %s: %s", type(exc).__name__, exc)
        return None, empty_usage

    token_usage = _extract_token_usage(response)
    logger.info("LLM 调用完成: prompt=%d, completion=%d",
                token_usage["prompt_tokens"], token_usage["completion_tokens"])

    raw_text = getattr(response, "content", "")
    if isinstance(raw_text, list):
        raw_text = "".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in raw_text
        )

    result = planner_parser.parse(str(raw_text))
    if result is None:
        logger.warning("LLM JSON 解析失败，原始返回预览: %s", str(raw_text)[:300])
        return None, token_usage

    if len(result.days) != day_count:
        logger.warning("行程天数不匹配: expected=%d, actual=%d", day_count, len(result.days))
        return None, token_usage

    return result, token_usage


def generate_day_edit_draft(
    request: TripEditRequest,
    target_day: DayPlan,
) -> tuple[DayEditDraft | None, dict[str, int]]:
    empty_usage = {"prompt_tokens": 0, "completion_tokens": 0}
    llm = _build_chat_llm()
    if llm is None:
        return None, empty_usage

    import json

    current_day_payload = {
        "day_index": target_day.day_index,
        "date": target_day.date.isoformat() if target_day.date else None,
        "theme": target_day.theme,
        "spots": [spot.model_dump(mode="json") for spot in target_day.spots],
        "meals": [meal.model_dump(mode="json") for meal in target_day.meals],
        "notes": list(target_day.notes),
    }

    format_instructions = day_edit_parser.get_format_instructions()

    system_prompt = (
        "你是一名旅行行程编辑助手。请根据用户编辑指令，只重写目标那一天的核心安排。\n"
        "编辑结果要尽量保留原 itinerary 的整体风格和预算结构。\n"
        + format_instructions
    )

    human_prompt = f"""
当前完整 itinerary：
{json.dumps(request.current_itinerary.model_dump(mode="json"), ensure_ascii=False, indent=2)}

需要重点编辑的目标 day：
{json.dumps(current_day_payload, ensure_ascii=False, indent=2)}

用户编辑指令：{request.user_instruction}
编辑范围：{request.edit_scope or '未指定'}
保留约束：{', '.join(request.preserve_constraints) if request.preserve_constraints else '无'}

请只输出编辑后的当天结果，不要输出额外的天。
"""

    logger.info("LLM 单日编辑: model=%s", LLM_MODEL)

    try:
        response = _invoke_llm(llm, [("system", system_prompt), ("human", human_prompt)])
    except (CircuitBreakerOpenError, Exception) as exc:
        logger.warning("单日编辑 LLM 调用失败: %s: %s", type(exc).__name__, exc)
        return None, empty_usage

    token_usage = _extract_token_usage(response)
    logger.info("单日编辑完成: prompt=%d, completion=%d",
                token_usage["prompt_tokens"], token_usage["completion_tokens"])

    raw_text = getattr(response, "content", "")
    if isinstance(raw_text, list):
        raw_text = "".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in raw_text
        )

    result = day_edit_parser.parse(str(raw_text))
    if result is None:
        logger.warning("单日编辑 JSON 解析失败: %s", str(raw_text)[:300])
        return None, token_usage

    return result, token_usage