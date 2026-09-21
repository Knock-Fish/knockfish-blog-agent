import logging

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
import json
from typing import AsyncGenerator

from pydantic import BaseModel

import app.graph.workflow as wf
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.chat import ChatRequest, ChatResponse
from ..schemas.sse import DoneEvent, ErrorEvent, TokenEvent
from ..services import long_term_memory_service as ltm
from ..services import memory_service

logger = logging.getLogger(__name__)


def _build_inputs(req: ChatRequest) -> dict:
    """组装图的初始输入。"""
    return {
        "messages": [HumanMessage(content=req.message)],
        "user_id": req.user_id,
        "user_identity": req.user_identity,
        "user_preferences": req.user_preferences,
        "long_term_context": req.long_term_context,
        "prompt_key": req.prompt_key,
    }


async def chat_once(req: ChatRequest, session: AsyncSession) -> ChatResponse:
    # thread_id 透传给 graph，checkpointer 据此恢复/存储会话历史
    config: RunnableConfig = {"configurable": {"thread_id": req.thread_id}}

    inputs = _build_inputs(req)

    graph = await wf.get_graph()
    # 跑完整张图（含工具循环），recursion_limit 防死循环
    result = await graph.ainvoke(inputs, config=config, recursion_limit=wf.DEFAULT_RECURSION_LIMIT)

    # 取最后一条消息作为最终回复
    last = result["messages"][-1]
    reply = last.content if isinstance(last.content, str) else str(last.content)

    # 持久化本轮对话（user + assistant）到业务 messages 表
    await memory_service.append_turn(
        thread_id=req.thread_id,
        user_text=req.message,
        assistant_text=reply,
        user_id=req.user_id,
        session=session,
    )

    # 累计到阈值时自动生成跨会话对话摘要（写入长期记忆）；失败不影响已完成的回复
    try:
        await ltm.summarize_conversation(
            thread_id=req.thread_id, user_id=req.user_id, session=session
        )
    except Exception as exc:  # 摘要是增强能力，不应让对话本身失败
        logger.warning("对话摘要生成失败（已忽略）: %s", exc)

    return ChatResponse(reply=reply, thread_id=req.thread_id)


async def chat_stream(req: ChatRequest, session: AsyncSession) -> AsyncGenerator[str, None]:
    config = {"configurable": {"thread_id": req.thread_id}}
    inputs = _build_inputs(req)

    graph = await wf.get_graph()

    try:
        # 收集完整回复文本，流结束后再落库
        parts: list[str] = []

        # v2 事件 schema：LLM 的逐 token 会以 on_chat_model_stream 吐出
        async for event in graph.astream_events(
                inputs, config=config, version="v2",
                recursion_limit=wf.DEFAULT_RECURSION_LIMIT,
        ):
            if event["event"] != "on_chat_model_stream":
                continue
            chunk = event["data"]["chunk"]  # AIMessageChunk
            text = _extract_text(chunk.content)  # 兼容 str / list 两种 content
            if text:
                parts.append(text)
                yield _sse(TokenEvent(type="token", content=text))

        full = "".join(parts)

        # 流结束后一次性落库（user + assistant）
        await memory_service.append_turn(
            thread_id=req.thread_id,
            user_text=req.message,
            assistant_text=full,
            user_id=req.user_id,
            session=session,
        )

        # 累计到阈值时自动生成跨会话对话摘要（写入长期记忆）；失败不影响已完成的回复
        try:
            await ltm.summarize_conversation(
                thread_id=req.thread_id, user_id=req.user_id, session=session
            )
        except Exception as exc:  # 摘要是增强能力，不应让对话本身失败
            logger.warning("对话摘要生成失败（已忽略）: %s", exc)

        yield _sse(DoneEvent(type="done", thread_id=req.thread_id))

    except Exception as exc:  # 流式里异常无法走标准 HTTP 错误体，转成 error 事件
        yield _sse(ErrorEvent(type="error", message=str(exc)))


def _extract_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):  # 多模态 content 形如 [{"type":"text","text":...}, ...]
        return "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return ""


def _sse(event: BaseModel) -> str:
    """将 SSE 事件模型序列化为 `data: <json>` 行。

    统一用 CamelModel 的别名（by_alias=True）输出驼峰字段名，保证与 REST 响应、
    前端 Api.Agent.* 类型一致；mode="json" 确保 datetime / UUID 等类型正确序列化，
    exclude_none 避免可选字段输出 null 污染前端。
    """
    payload = event.model_dump(by_alias=True, mode="json", exclude_none=True)
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
