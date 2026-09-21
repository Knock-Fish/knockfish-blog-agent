"""请求级上下文：在 chat 入口设置当前用户 id，供工具（无需参数）读取，实现用户隔离。

为什么不用参数传 user_id？
    - 工具由 LangGraph 的 ToolNode 按 LLM 的 tool_calls 参数调用，工具签名只接受 LLM 传来的
      参数；若把 user_id 暴露成工具参数，等于让 LLM 决定「为谁存记忆」，存在越权/串号风险。
    - 改用 contextvar：在已鉴权的 chat 端点入口（已拿到可信 user_id）set 一次，工具内读取，
      与 app/utils/http/client.py 透传 JWT 的思路一致。

注意：contextvar 在同一 asyncio 任务及其子任务内可见。chat 端点与 graph.ainvoke 运行在
同一任务上下文中，因此工具内能正确读到入口设置的 user_id。
"""
from contextvars import ContextVar
from typing import Optional

_user_id_var: ContextVar[Optional[int]] = ContextVar("current_user_id", default=None)


def set_current_user_id(user_id: int) -> None:
    """在请求入口设置当前用户 id（覆盖式）。"""
    _user_id_var.set(user_id)


def get_current_user_id() -> Optional[int]:
    """读取当前用户 id；未设置（非 chat 请求路径）时返回 None。"""
    return _user_id_var.get()
