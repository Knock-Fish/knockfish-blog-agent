"""
LangGraph 状态定义模块
定义图中流动的状态结构
"""
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # add_messages 是消息合并reducer，自动append消息，不会覆盖
    messages: Annotated[list, add_messages]
    user_query: str
