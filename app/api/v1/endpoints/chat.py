"""聊天接口"""
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.db import get_session
from ....core.request_context import set_current_user_id
from ....core.security import get_current_user
from ....schemas.base import ApiResponse
from ....schemas.chat import ChatRequest, ChatResponse
from ....services import long_term_memory_service as ltm
from ....services.chat_service import chat_once, chat_stream

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat")


@router.post("/", response_model=ApiResponse[ChatResponse], summary="非流式对话")
async def chat(
    req: ChatRequest,
    user_id: int = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[ChatResponse]:
    # 用户身份一律以 token 解析结果为准，覆盖请求体中的 user_id，防止越权
    req.user_id = user_id
    set_current_user_id(user_id)
    # 自动回忆长期记忆并注入系统提示词，使本次回答按用户画像个性化
    profile = await ltm.recall_profile(user_id=user_id, session=session)
    req.user_identity = profile["identity"]
    req.user_preferences = profile["preferences"]
    req.long_term_context = profile["context"]
    result = await chat_once(req, session)
    return ApiResponse(data=result)


@router.post("/stream", summary="流式对话(SSE)")
async def chat_stream_endpoint(
    req: ChatRequest,
    user_id: int = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    req.user_id = user_id
    set_current_user_id(user_id)
    # 自动回忆长期记忆并注入系统提示词，使本次回答按用户画像个性化
    profile = await ltm.recall_profile(user_id=user_id, session=session)
    req.user_identity = profile["identity"]
    req.user_preferences = profile["preferences"]
    req.long_term_context = profile["context"]
    return StreamingResponse(
        chat_stream(req, session),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
