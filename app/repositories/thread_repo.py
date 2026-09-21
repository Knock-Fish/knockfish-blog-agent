"""threads 表持久层：只写 SQL，不提交事务"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import insert, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.conversation import Thread


async def insert_thread(
        *,
        thread_id: uuid.UUID,
        user_id: int,
        title: str | None,
        last_message: str | None,
        message_count: int,
        now: datetime,
        session: AsyncSession,
) -> Thread:
    """插入会话记录并返回 Thread 对象"""
    now = now or datetime.now(timezone.utc)
    stmt = (
        insert(Thread)
        .values(
            thread_id=thread_id,
            user_id=user_id,
            title=title,
            last_message=last_message,
            message_count=message_count,
            created_at=now,
            updated_at=now,
        )
        .returning(Thread)
    )
    result = await session.execute(stmt)
    await session.flush()
    return result.scalar_one()


async def delete_thread(
        thread_id: uuid.UUID,
        user_id: int,
        session: AsyncSession,
) -> bool:
    """删除会话。

    Returns:
        bool: True 表示确实删除了记录；False 表示会话不存在或不属于该用户。

    注意：messages 由数据库外键 ON DELETE CASCADE 级联清理，此处无需处理。
    """
    stmt = (
        delete(Thread)
        .where(
            Thread.thread_id == thread_id,
            Thread.user_id == user_id,  # 权限校验
        )
    )
    result = await session.execute(stmt)
    await session.flush()
    return result.rowcount > 0


async def update_thread(
        thread_id: uuid.UUID,
        title: str | None,
        user_id: int,
        session: AsyncSession,
) -> bool:
    """更新会话标题。返回 True 表示成功，False 表示会话不存在或不属于该用户。"""
    stmt = (
        update(Thread)
        .where(
            Thread.thread_id == thread_id,
            Thread.user_id == user_id,  # 权限校验
        )
        .values(
            title=title,
            updated_at=datetime.now(timezone.utc),
        )
    )
    result = await session.execute(stmt)
    await session.flush()
    return result.rowcount > 0


async def list_threads(
        user_id: int, limit: int, offset: int, session: AsyncSession
) -> list[Thread]:
    stmt = (
        select(Thread)
        .where(Thread.user_id == user_id)
        .order_by(Thread.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_thread(thread_id: uuid.UUID, session: AsyncSession) -> Thread | None:
    """按主键查询会话，不存在返回 None（供 append_turn 判断是否需要自动建会话）"""
    stmt = select(Thread).where(Thread.thread_id == thread_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def touch_thread(
    *, thread_id: uuid.UUID, last_message: str, now: datetime, session: AsyncSession,
) -> None:
    """更新会话末条消息、消息数 +2（本轮 user+assistant）、更新时间。"""
    stmt = (
        update(Thread)
        .where(Thread.thread_id == thread_id)
        .values(
            last_message=last_message,
            message_count=Thread.message_count + 2,
            updated_at=now,
        )
    )
    await session.execute(stmt)
    await session.flush()
