"""SSE 流式事件模型

Agent 通过 `text/event-stream` 向前端推送增量文本与状态。所有事件均继承 CamelModel，
序列化时字段名转驼峰，与 REST 响应、前端 `Api.Agent.*` 类型保持同一 wire format
（例如 done 事件携带的 thread_id 输出为 `threadId`）。

事件协议（前端 stream.ts 对应解析）：
    {"type":"token","content":"..."}   逐 token 增量文本
    {"type":"done","threadId":"..."}   流正常结束（可选携带本次会话 ID）
    {"type":"error","message":"..."}   流内业务错误
"""
from pydantic import BaseModel

from .base import CamelModel


class SSEEvent(CamelModel):
    """SSE 事件基类，`type` 标识事件种类。"""

    type: str


class TokenEvent(SSEEvent):
    """LLM 逐 token 增量。"""

    content: str


class DoneEvent(SSEEvent):
    """流正常结束，可选携带本次会话 ID（驼峰 `threadId`）。"""

    thread_id: str | None = None


class ErrorEvent(SSEEvent):
    """流内捕获的异常，转为 error 事件下发给前端。"""

    message: str
