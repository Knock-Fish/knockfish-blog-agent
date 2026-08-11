import os

import aiosqlite
from langgraph.graph import StateGraph
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from .state import AgentState
from .nodes import llm_chat_node, tool_node, should_use_tools

# 确保数据目录存在
os.makedirs("./data", exist_ok=True)
# SQLite 数据库路径
_DB_PATH = "./data/graph_memory.db"


async def build_agent_workflow_async():
    """异步构建图：使用 AsyncSqliteSaver 以支持 ainvoke"""
    conn = await aiosqlite.connect(_DB_PATH)
    checkpointer = AsyncSqliteSaver(conn)
    # 初始化检查点表
    await checkpointer.setup()

    builder = StateGraph(AgentState)
    builder.add_node("chat_llm", llm_chat_node)
    builder.add_node("tools", tool_node)

    # 流程：入口 -> LLM -> (有工具调用?) -> tools -> 回到 LLM 循环；无则结束
    builder.set_entry_point("chat_llm")
    builder.add_conditional_edges("chat_llm", should_use_tools)
    builder.add_edge("tools", "chat_llm")

    graph = builder.compile(checkpointer=checkpointer)
    return graph


# 全局缓存：首次访问时异步构建，后续复用
_compiled_graph = None


async def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = await build_agent_workflow_async()
    return _compiled_graph
