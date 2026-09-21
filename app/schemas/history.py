"""会话历史的请求 / 响应模型

命名约定：
    - 请求模型（ThreadCreate）继承 pydantic.BaseModel，字段为 snake_case（服务端内部约定）。
    - 响应模型（ThreadOut / MessageOut）继承 ORMModel(CamelModel)，对外序列化为驼峰字段名，
      与前端 Api.Agent.* 类型及 Spring Boot 的 wire format 对齐。
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .base import CamelModel, ORMModel


class ThreadCreate(BaseModel):
    """创建会话请求体

    user_id 由服务端从 JWT token 解析并覆盖，前端无需传（传了也会被忽略）。
    """

    user_id: Optional[int] = Field(
        default=None, description="用户 ID（服务端从 token 解析，前端无需传）"
    )
    title: Optional[str] = Field(default=None, max_length=255, description="会话标题")
    first_message: str = Field(..., min_length=1, description="首条消息内容")


class ThreadUpdate(BaseModel):
    """更新会话请求体（部分更新，对应 PATCH 语义）

    目前仅开放 title：user_id / message_count / last_message 等字段由服务端维护，
    不接受前端传入，避免越权篡改。
    """

    title: str = Field(..., min_length=1, max_length=255, description="新的会话标题")


class ThreadDeleteOut(CamelModel):
    """删除会话响应体（对外驼峰，与 ThreadOut 的 wire format 保持一致）"""

    thread_id: uuid.UUID
    deleted: bool = True


class ThreadOut(ORMModel):
    """会话响应体（从 ORM 对象转换而来，字段序列化为驼峰）"""

    thread_id: uuid.UUID
    user_id: int
    title: Optional[str] = None
    last_message: Optional[str] = None
    message_count: int
    created_at: datetime
    updated_at: datetime


class MessageOut(ORMModel):
    """消息响应体（从 ORM 对象转换而来，按时间正序返回，字段序列化为驼峰）"""

    message_id: int
    thread_id: uuid.UUID
    role: str
    content: str
    tool_calls: Optional[list] = None
    tool_call_id: Optional[str] = None
    tokens: Optional[int] = None
    created_at: datetime
