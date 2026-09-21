"""会话历史接口"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.db import get_session
from app.core.security import get_current_user
from app.models.conversation import Message, Thread
from app.schemas.base import ApiResponse
from app.schemas.history import (
    MessageOut,
    ThreadCreate,
    ThreadDeleteOut,
    ThreadOut,
    ThreadUpdate,
)
from app.services import memory_service

router = APIRouter(prefix="/memory")


@router.post("/threads", response_model=ApiResponse[ThreadOut], summary="创建会话并写入首条消息")
async def create_thread(
    payload: ThreadCreate,
    user_id: int = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[ThreadOut]:
    # 会话归属以 token 解析出的 user_id 为准，不信前端传参
    payload.user_id = user_id
    thread = await memory_service.create_thread_with_message(payload, session)
    return ApiResponse(data=thread)


@router.get("/threads", response_model=ApiResponse[list[ThreadOut]], summary="会话列表")
async def list_threads(
    user_id: int = Depends(get_current_user),
    limit: int = Query(default=20, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[ThreadOut]]:
    threads = await memory_service.list_threads(user_id, limit, offset, session)
    return ApiResponse(data=threads)


@router.get(
    "/threads/{thread_id}/messages",
    response_model=ApiResponse[list[MessageOut]],
    summary="某会话的消息列表",
)
async def list_thread_messages(
    thread_id: UUID,
    user_id: int = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[MessageOut]]:
    """返回指定会话的全部消息（按时间正序），并校验会话归属当前用户。"""
    messages = await memory_service.list_messages(
        thread_id=thread_id, user_id=user_id, session=session
    )
    return ApiResponse(data=messages)


@router.patch(
    "/threads/{thread_id}",
    response_model=ApiResponse[ThreadOut],
    summary="更新会话标题（部分更新）",
)
async def update_thread(
    thread_id: UUID,
    payload: ThreadUpdate,
    user_id: int = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[ThreadOut]:
    """更新指定会话的标题，返回刷新后的会话。

    会话归属以 token 解析出的 user_id 为准；
    会话不存在，或存在但不属于当前用户，统一返回 404（不泄露资源存在性）。
    """
    thread = await memory_service.update_thread_title(
        thread_id=thread_id, user_id=user_id, title=payload.title, session=session
    )
    return ApiResponse(data=thread)


@router.delete(
    "/threads/{thread_id}",
    response_model=ApiResponse[ThreadDeleteOut],
    summary="删除会话（其消息由数据库级联删除）",
)
async def delete_thread(
    thread_id: UUID,
    user_id: int = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[ThreadDeleteOut]:
    """删除指定会话。

    该会话下的 messages 由外键 ON DELETE CASCADE 自动清理，无需逐条删除。
    会话不存在，或存在但不属于当前用户，统一返回 404。
    """
    await memory_service.delete_thread(
        thread_id=thread_id, user_id=user_id, session=session
    )
    return ApiResponse(data=ThreadDeleteOut(thread_id=thread_id, deleted=True))
