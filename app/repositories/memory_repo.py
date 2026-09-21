"""memory_items 持久层：只写 SQL，不提交事务（事务在 service 层统一提交）"""
from datetime import datetime, timezone

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.memory import MemoryItem


async def upsert_item(
    *,
    user_id: int,
    memory_key: str,
    memory_value: str,
    category: str,
    now: datetime,
    session: AsyncSession,
) -> MemoryItem:
    """插入或更新一条记忆（同一用户对同一 key 覆盖更新）。

    返回 upsert 后的 MemoryItem 对象。
    """
    existing = (
        await session.execute(
            select(MemoryItem).where(
                MemoryItem.user_id == user_id,
                MemoryItem.memory_key == memory_key,
            )
        )
    ).scalar_one_or_none()

    if existing is None:
        stmt = (
            insert(MemoryItem)
            .values(
                user_id=user_id,
                memory_key=memory_key,
                memory_value=memory_value,
                category=category,
                created_at=now,
                updated_at=now,
            )
            .returning(MemoryItem)
        )
    else:
        stmt = (
            update(MemoryItem)
            .where(MemoryItem.id == existing.id)
            .values(memory_value=memory_value, category=category, updated_at=now)
            .returning(MemoryItem)
        )

    result = await session.execute(stmt)
    await session.flush()
    return result.scalar_one()


async def list_by_user(user_id: int, session: AsyncSession) -> list[MemoryItem]:
    """列出某用户全部记忆，按更新时间倒序（最近的在前）。"""
    stmt = (
        select(MemoryItem)
        .where(MemoryItem.user_id == user_id)
        .order_by(MemoryItem.updated_at.desc())
    )
    return list((await session.execute(stmt)).scalars().all())
