"""
LangGraph 状态定义模块
定义图中流动的状态结构
"""

from typing import Annotated, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    # add_messages 是消息合并reducer，自动append消息，不会覆盖
    messages: Annotated[list, add_messages]
    user_query: str
    user_id: Optional[int]
    # 已拼接好的长期记忆上下文（字符串，直接注入系统提示词占位符）
    long_term_context: Optional[str]
    # 用户偏好字典（摘要用，可直接展示 user_preferences 占位符）
    user_preferences: Optional[str]
    # 用户身份摘要（如 "博客作者小明"，默认"访客"）
    user_identity: Optional[str]
    # 选用的提示词模板 key（如 "system_prompt" / "summary_prompt"），默认 system_prompt
    prompt_key: Optional[str]
