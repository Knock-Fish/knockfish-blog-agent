"""会话历史业务层：编排 repository，事务只在这里提交"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.exception import ForbiddenException, NotFoundException
from ..models.conversation import Message, Thread
from ..repositories import message_repo, thread_repo
from ..schemas.history import ThreadCreate


def _utcnow() -> datetime:
    """统一时间出口：全部由代码生成，不依赖数据库"""
    return datetime.now(timezone.utc)


async def create_thread_with_message(
    payload: ThreadCreate, session: AsyncSession
) -> Thread:
    """创建会话 + 写入首条消息（同一事务：要么都成功，要么都回滚）"""
    now = _utcnow()
    thread_id = uuid.uuid4()
    title = payload.title or payload.first_message[:20] or "新会话"

    # threads
    thread = await thread_repo.insert_thread(
        thread_id=thread_id,
        user_id=payload.user_id,
        title=title,
        last_message=payload.first_message,
        message_count=1,
        now=now,
        session=session,
    )

    # messages
    await message_repo.insert_message(
        thread_id=thread_id,
        role="user",
        content=payload.first_message,
        now=now,
        session=session,
    )

    # 唯一提交点
    await session.commit()
    return thread


async def list_threads(
    user_id: int, limit: int, offset: int, session: AsyncSession
) -> list[Thread]:
    return await thread_repo.list_threads(user_id, limit, offset, session)


async def list_messages(
    *, thread_id: uuid.UUID, user_id: int, session: AsyncSession
) -> list[Message]:
    """按会话拉取消息列表，带用户归属校验。

    - 会话不存在 → NotFoundException(404)
    - 会话存在但不属于当前用户 → ForbiddenException(403)
    - 校验通过 → 返回该会话全部消息（按 created_at 正序）
    """
    thread = await thread_repo.get_thread(thread_id, session)
    if thread is None:
        raise NotFoundException("会话不存在")
    if thread.user_id != user_id:
        raise ForbiddenException("无权访问该会话的消息")
    return await message_repo.list_messages(thread_id, session)


async def update_thread_title(
    *, thread_id: uuid.UUID, user_id: int, title: str, session: AsyncSession
) -> Thread:
    """更新会话标题（部分更新，带归属校验），返回刷新后的会话。

    Returns:
        Thread: 更新后的会话对象（含新的 title / updated_at）。

    Raises:
        NotFoundException: 会话不存在，或存在但不属于当前用户。

    说明：越权情形这里统一抛 404 而不是 403 —— 返回 403 等于告诉调用方
    「会话存在，只是你不该访问」，会泄露资源存在性；统一 404 对外更安全。
    """
    ok = await thread_repo.update_thread(
        thread_id=thread_id, title=title, user_id=user_id, session=session
    )
    if not ok:
        raise NotFoundException("会话不存在")
    await session.commit()

    # 重新查询以返回带新 title / updated_at 的完整对象
    thread = await thread_repo.get_thread(thread_id, session)
    if thread is None:  # 理论不可达：更新成功即说明记录存在，防御性兜底
        raise NotFoundException("会话不存在")
    return thread


async def delete_thread(
    *, thread_id: uuid.UUID, user_id: int, session: AsyncSession
) -> bool:
    """删除会话（带归属校验）。

    messages 无需手动删除：models.Message 的外键声明了 ondelete="CASCADE"
    且关系带 passive_deletes=True，由数据库级联清理。

    Returns:
        bool: 删除成功恒为 True。

    Raises:
        NotFoundException: 会话不存在，或存在但不属于当前用户（同上，统一 404）。
    """
    ok = await thread_repo.delete_thread(
        thread_id=thread_id, user_id=user_id, session=session
    )
    if not ok:
        raise NotFoundException("会话不存在")
    await session.commit()
    return True


async def append_turn(
    *,
    thread_id: str,
    user_text: str,
    assistant_text: str,
    session: AsyncSession,
    user_id: int | None = None,
) -> None:
    """把一轮对话（user + assistant）追加写入业务表，并兼容会话尚未创建的情况。

    事务只在这里统一 commit。
    """
    tid = uuid.UUID(thread_id)
    now = _utcnow()

    # 会话不存在则先建（兼容直接 /chat 而未走 POST /threads 的场景）
    existing = await thread_repo.get_thread(tid, session)
    if existing is None:
        await thread_repo.insert_thread(
            thread_id=tid,
            user_id=user_id or 0,
            title=(user_text[:20] or "新会话"),
            last_message=user_text,
            message_count=0,
            now=now,
            session=session,
        )

    # 写 user 消息
    await message_repo.insert_message(
        thread_id=tid, role="user", content=user_text, now=now, session=session)
    # 写 assistant 消息
    await message_repo.insert_message(
        thread_id=tid, role="assistant", content=assistant_text, now=now, session=session)
    # 更新 threads：末条消息 / 消息数 +2（本轮 user+assistant）/ 更新时间
    await thread_repo.touch_thread(
        thread_id=tid, last_message=assistant_text, now=now, session=session)

    await session.commit()
