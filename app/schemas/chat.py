"""Pydantic 请求 / 响应模型

命名约定：请求模型用 BaseModel（snake_case），响应模型用 CamelModel（对外驼峰），
与全局 wire format 约定一致。
"""
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from .base import CamelModel


class ChatRequest(BaseModel):
    """聊天请求体"""

    message: str = Field(..., min_length=1, description="用户本轮输入")
    thread_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="会话 ID，同一会话的多轮请求需保持一致；不传则新建",
    )
    user_id: Optional[int] = Field(default=None, description="用户 ID")
    user_identity: Optional[str] = Field(default="访客", description="用户身份摘要")
    user_preferences: Optional[str] = Field(default=None, description="用户偏好")
    long_term_context: Optional[str] = Field(default=None, description="长期记忆上下文")
    prompt_key: Optional[str] = Field(
        default=None, description="选用的提示词模板 key，默认 system_prompt"
    )


class ChatResponse(CamelModel):
    """聊天响应体（对外驼峰：reply / threadId）"""

    reply: str = Field(..., description="助手回复内容")
    thread_id: str = Field(..., description="本次会话 ID")
