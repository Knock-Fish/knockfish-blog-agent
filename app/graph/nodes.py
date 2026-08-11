"""
LangGraph 节点定义模块
定义图中的各种节点（工具节点、LLM节点等）
"""
from datetime import datetime

from langgraph.graph import END
from langgraph.prebuilt import ToolNode

from .state import AgentState
from ..core.llm import llm  # 导入全局llm实例
from ..tools.registry import tools
from ..prompt import role_prompt  # 提示词模板

# 绑定工具后的 LLM：模型能感知工具描述并决定是否调用
llm_with_tools = llm.bind_tools(tools)

# 工具执行节点：接收 LLM 的 tool_calls，执行对应工具，返回 ToolMessage
tool_node = ToolNode(tools)


async def llm_chat_node(state: AgentState):
    """LLM 对话节点：用提示词模板格式化后调用 LLM"""
    messages = role_prompt.invoke({
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "messages": state["messages"],
    }).to_messages()
    resp = await llm_with_tools.ainvoke(messages)
    return {"messages": [resp]}


def should_use_tools(state: AgentState) -> str:
    """条件路由：判断 LLM 最后一条消息是否包含工具调用"""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END
