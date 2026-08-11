"""聊天接口"""
import uuid
from fastapi.responses import StreamingResponse
from typing import Any, Dict, AsyncGenerator
import json
from fastapi import APIRouter, Header
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from app.graph.workflow import get_compiled_graph
from app.utils.http.client import set_current_token

router = APIRouter()


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., description="用户消息")
    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="会话ID，传入相同值可保持多轮对话上下文",
    )


class ChatResponse(BaseModel):
    """聊天响应"""
    session_id: str
    reply: str


@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    authorization: str = Header(default=None),
) -> StreamingResponse:
    """
    流式聊天接口：使用 LangGraph 工作流，逐块返回 LLM 生成的文本。
    返回 Server-Sent Events (SSE) 流。
    通过 Authorization 头传入 JWT，供工具调用 SpringBoot API 使用。
    """
    # 提取 JWT 并注入请求上下文，工具内通过 get_current_token() 读取
    if authorization and authorization.lower().startswith("bearer "):
        set_current_token(authorization[7:])

    graph = await get_compiled_graph()
    config = {"configurable": {"thread_id": req.session_id}}

    # 异步生成器，产生 SSE 格式的数据块
    async def event_generator() -> AsyncGenerator[str, None]:
        # 使用 astream_events 可获取更细粒度的事件（包括流式消息块）
        # 版本号 v2 是推荐的
        async for event in graph.astream_events(
                {"messages": [HumanMessage(content=req.message)]},
                config=config,
                version="v2"
        ):
            # 只捕获 on_chat_model_stream 事件，即模型流式输出块
            if event["event"] == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                # chunk 是 AIMessageChunk，其 content 属性包含增量文本
                if chunk.content:
                    # 包装成 SSE 格式：data: {json}\n\n
                    yield f"data: {json.dumps({'content': chunk.content}, ensure_ascii=False)}\n\n"

        # 发送结束标记
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
