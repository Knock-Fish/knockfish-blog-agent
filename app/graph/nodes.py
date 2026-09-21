"""
LangGraph 节点定义模块
定义图中的各种节点（工具节点、LLM节点等）
"""
from typing import Any, Optional

from langchain_core.messages import AIMessageChunk, AnyMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt.tool_node import ToolNode

from ..core.llm import llm  # 导入全局llm实例
from ..tools.registry import tools
from .state import AgentState
from ..prompts import PROMPTS, DEFAULT_PROMPT_KEY
# 绑定工具后的 LLM：模型能感知工具描述并决定是否调用
llm_with_tools = llm.bind_tools(tools)

# 工具执行节点：接收 LLM 的 tool_calls，执行对应工具，返回 ToolMessage
tool_node = ToolNode(tools)

def build_system_message(
    state: AgentState,
    prompt_key: Optional[str] = None,
) -> SystemMessage:
    """根据状态中的长期记忆/用户画像渲染系统提示词。

    模板选择优先级：显式 prompt_key 参数 > state 中的 prompt_key > 默认值。

    Args:
        state: 当前图状态。
        prompt_key: 选用的提示词模板 key；为 None 时回退到 state 或默认值。

    Returns:
        渲染后的 SystemMessage。

    Raises:
        KeyError: prompt_key 不存在或模板占位符缺失。
    """
    from ..core.config import settings  # 局部导入，避免与配置模块循环依赖

    key = prompt_key or state.get("prompt_key") or DEFAULT_PROMPT_KEY
    template = PROMPTS.get(key) or PROMPTS[DEFAULT_PROMPT_KEY]
    content = template.render(
        app_name=settings.APP_NAME,
        user_identity=state.get("user_identity") or "访客",
        user_preferences=state.get("user_preferences") or "暂无",
        long_term_context=state.get("long_term_context") or "暂无",
    )
    return SystemMessage(content=content)


async def llm_chat_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    """
    LLM 对话节点：用提示词模板格式化后调用 LLM，并注入长期记忆/用户画像。

    使用 `astream` 把逐片返回的内容累加，最终合并成一条完整的
    AIMessage 写回 state（add_messages reducer 负责追加）。

    Args:
        state: 当前图状态，包含 messages 与记忆字段。
        config: LangGraph 注入的 RunnableConfig（内含 thread_id、回调等）。

    Returns:
        只含 messages 的状态增量，由 add_messages reducer 追加。

    Raises:
        RuntimeError: LLM 未返回任何内容时抛出。
    """
    messages: list[AnyMessage] = [build_system_message(state), *state.get("messages", [])]

    full_chunk: Optional[AIMessageChunk] = None
    # config 必须透传给 LLM，内含 thread_id，供 checkpointer 恢复/写入会话历史
    async for chunk in llm_with_tools.astream(messages, config=config):
        full_chunk = chunk if full_chunk is None else full_chunk + chunk

    if full_chunk is None:
        raise RuntimeError("LLM 未返回任何内容")

    return {"messages": [full_chunk]}
