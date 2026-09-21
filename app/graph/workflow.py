"""
LangGraph 工作流装配模块
负责把节点编排成图并编译为可执行的 graph。
checkpointer 使用 PostgreSQL（AsyncPostgresSaver），实现对话状态持久化。
"""
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import tools_condition
from psycopg_pool import AsyncConnectionPool

from .nodes import llm_chat_node, tool_node
from .state import AgentState
from ..core.config import settings

# 工具调用循环的最大步数，防止模型反复调用工具导致死循环
DEFAULT_RECURSION_LIMIT = 25

# 全局图实例，由 lifespan（或首次调用 get_graph）异步初始化
graph: CompiledStateGraph | None = None

# 全局 psycopg 连接池，与 graph 同生命周期（应用关闭时由 lifespan 负责关闭）
_pool: AsyncConnectionPool | None = None


async def build_graph() -> CompiledStateGraph:
    """
    构建并编译 LangGraph 状态图，使用 PostgreSQL checkpointer 做持久化。

    图结构：
        START -> llm_chat --(需要工具)--> tools -> llm_chat
                          --(无需工具)--> END

    Returns:
        编译后的 CompiledStateGraph，可直接 .astream() / .ainvoke()。
    """
    # AsyncPostgresSaver 3.x 要求 psycopg 连接/池，不再接受 SQLAlchemy AsyncEngine。
    # psycopg 用纯 postgresql:// （去掉 SQLAlchemy 的 +asyncpg 前缀）。
    global _pool
    conninfo = settings.DATABASE_URL.replace("+asyncpg", "")
    # autocommit=True：setup() 里的 CREATE INDEX CONCURRENTLY 必须在非事务中执行
    _pool = AsyncConnectionPool(
        conninfo=conninfo, open=False, max_size=10, kwargs={"autocommit": True}
    )
    await _pool.open()

    checkpointer = AsyncPostgresSaver(_pool)
    await checkpointer.setup()  # 首次建 langgraph 自己的表（checkpoints / writes / blobs）

    builder = StateGraph(AgentState)

    builder.add_node("llm_chat", llm_chat_node)
    builder.add_node("tools", tool_node)

    builder.add_edge(START, "llm_chat")
    builder.add_conditional_edges(
        "llm_chat",
        tools_condition,
        {"tools": "tools", END: END},
    )
    builder.add_edge("tools", "llm_chat")

    return builder.compile(checkpointer=checkpointer, name="knockfish-blog-agent")


async def get_graph() -> CompiledStateGraph:
    """惰性获取全局图实例：未初始化时自动构建（同时供 lifespan 预热）。"""
    global graph
    if graph is None:
        graph = await build_graph()
    return graph


async def close_pool() -> None:
    """应用关闭时释放 psycopg 连接池（lifespan 的 shutdown 阶段调用）。"""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
