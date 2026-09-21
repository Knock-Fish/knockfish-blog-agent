"""messages 表持久层"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.conversation import Message


async def insert_message(
    *,
    thread_id: uuid.UUID,
    role: str,
    content: str,
    now: datetime,
    session: AsyncSession,
    tool_calls: Optional[list] = None,
    tool_call_id: Optional[str] = None,
    tokens: Optional[int] = None,
) -> Message:
    """插入消息记录"""
    msg = Message(
        thread_id=thread_id,
        role=role,
        content=content,
        tool_calls=tool_calls,
        tool_call_id=tool_call_id,
        tokens=tokens,
        created_at=now,
    )
    session.add(msg)
    await session.flush()
    return msg




async def list_messages(
    thread_id: uuid.UUID, session: AsyncSession
) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.thread_id == thread_id)
        .order_by(Message.created_at.asc())
    )
    return list((await session.execute(stmt)).scalars().all())
