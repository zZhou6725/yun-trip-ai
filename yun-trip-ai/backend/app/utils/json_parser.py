# =============================================================================
# 云途 AI 行程规划 - JSON 输出解析器
# =============================================================================
# 为 LLM 调用提供结构化输出约束。先从原始文本中提取 JSON，
# 再用 Pydantic 模型校验，失败时返回 None 供 Service 层回退。
# =============================================================================

from __future__ import annotations

import json
import re
from typing import TypeVar

from pydantic import BaseModel

from app.utils.logger import setup_logger

logger = setup_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class JsonOutputParser:
    """通用 JSON 输出解析器，约束 LLM 返回结构化 JSON。"""

    def __init__(self, pydantic_model: type[T]):
        self._model = pydantic_model

    def get_format_instructions(self) -> str:
        """生成格式约束指令，嵌入 system prompt。"""
        raw = self._model.model_json_schema()
        fields = raw.get("properties", {})

        instructions = "你必须严格输出以下 JSON 结构：\n"
        for field_name, info in fields.items():
            field_type = info.get("type", "any")
            desc = info.get("description", "")
            instructions += f'  "{field_name}": {field_type}  — {desc}\n'

        instructions += "\n只返回 JSON 对象，不要 Markdown、不要解释文字。"
        return instructions

    def parse(self, raw_text: str) -> T | None:
        """从原始文本中提取并校验 JSON。"""
        json_str = self._extract_json(raw_text)
        if json_str is None:
            logger.warning("JsonOutputParser: 无法从文本中提取 JSON，预览: %s", raw_text[:200])
            return None

        try:
            parsed = json.loads(json_str)
            return self._model.model_validate(parsed)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("JsonOutputParser: 解析/校验失败: %s", exc)
            return None

    @staticmethod
    def _extract_json(text: str) -> str | None:
        """从 LLM 原始输出中提取 JSON 字符串。"""
        text = text.strip()

        # 去掉 Markdown 代码块
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
            if text.lower().startswith("json"):
                text = text[4:].strip()

        # 尝试直接解析
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass

        # 从文本中找首尾大括号
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None

        candidate = text[start:end + 1]
        # 尝试修复常见错误：尾逗号
        candidate = re.sub(r",\s*}", "}", candidate)
        candidate = re.sub(r",\s*]", "]", candidate)

        return candidate


def create_parser(model: type[T]) -> JsonOutputParser:
    """便捷工厂函数。"""
    return JsonOutputParser(model)