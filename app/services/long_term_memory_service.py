"""长期记忆业务层：编排 repository，事务只在这里提交

与 memory_service（会话级短期记忆）职责分离：本模块专注「关于用户的稳定事实」的
remember / recall，以及跨会话的「对话摘要」，支撑 Agent 个性化。
"""
import uuid
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.llm import llm
from ..models.memory import MemoryItem
from ..prompts import PROMPTS
from ..repositories import memory_repo, message_repo


def _utcnow() -> datetime:
    """统一时间出口：全部由代码生成，不依赖数据库"""
    return datetime.now(timezone.utc)


async def remember_fact(
    *,
    user_id: int,
    key: str,
    value: str,
    category: str = "fact",
    session: AsyncSession,
) -> MemoryItem:
    """记住一条关于用户的稳定事实（同一 key 覆盖更新）。"""
    item = await memory_repo.upsert_item(
        user_id=user_id,
        memory_key=key,
        memory_value=value,
        category=category,
        now=_utcnow(),
        session=session,
    )
    # 唯一提交点
    await session.commit()
    return item


async def list_facts(*, user_id: int, session: AsyncSession) -> list[MemoryItem]:
    """列出某用户全部记忆条目。"""
    return await memory_repo.list_by_user(user_id, session)


async def recall_profile(*, user_id: int, session: AsyncSession) -> dict:
    """读取某用户全部记忆并组装成系统提示词需要的维度。

    记忆分四类呈现：
    - identity：身份画像（category=profile），无则 "已登录用户"
    - preferences：偏好（category=preference），无则 "暂无明确偏好"
    - summary：对话摘要（category=summary），无则 "暂无"
    - context：长期记忆总文本，摘要以段落呈现、其余事实以列表呈现，无则 "暂无"

    Returns:
        dict: {"identity", "preferences", "summary", "context"}
    """
    items = await memory_repo.list_by_user(user_id, session)
    identity_parts: list[str] = []
    pref_parts: list[str] = []
    summary_parts: list[str] = []
    fact_lines: list[str] = []
    for it in items:
        if it.category == "profile":
            identity_parts.append(f"{it.memory_key}: {it.memory_value}")
        elif it.category == "preference":
            pref_parts.append(f"{it.memory_key}: {it.memory_value}")
        elif it.category == "summary":
            summary_parts.append(it.memory_value)
        else:
            fact_lines.append(f"- {it.memory_key}: {it.memory_value}")

    summary_block = "\n".join(summary_parts)
    context_parts: list[str] = []
    if summary_block:
        context_parts.append("对话摘要：\n" + summary_block)
    if fact_lines:
        context_parts.append("其他记忆：\n" + "\n".join(fact_lines))
    context = "\n\n".join(context_parts) or "暂无"

    return {
        "identity": "; ".join(identity_parts) or "已登录用户",
        "preferences": "; ".join(pref_parts) or "暂无明确偏好",
        "summary": summary_block or "暂无",
        "context": context,
    }


# 对话摘要写入 memory_items 的固定键；与 (user_id, memory_key) 唯一约束配合实现覆盖更新
SUMMARY_MEMORY_KEY = "conversation_summary"
SUMMARY_CATEGORY = "summary"
# 每累计多少条消息（约半数即一轮 user+assistant）触发一次摘要；取整数倍避免每轮都调 LLM
SUMMARY_TRIGGER_MESSAGES = 10


async def summarize_conversation(
    *, thread_id: str | uuid.UUID, user_id: int, session: AsyncSession
) -> None:
    """在对话累计到阈值时，用 summary_prompt 把近期对话压成长期摘要并落库。

    设计要点：
    - 触发条件：该线程消息数达到 SUMMARY_TRIGGER_MESSAGES 的整数倍（如 10/20/30…条），
      即每约 5 轮对话自动产出一次摘要，避免每轮都消耗一次 LLM 调用。
    - 滚动摘要：新摘要 = LLM(已有摘要 + 最近一个窗口的对话)。已有摘要以 (user_id,
      SUMMARY_MEMORY_KEY) 唯一键存储，每次覆盖更新；结合窗口截断保证喂给 LLM 的文本
      有界、输出长度有界（≤200 字），同时延续历史上下文。
    - 摘要按用户维度存储（非按线程），用于跨会话还原用户背景。
    """
    tid = uuid.UUID(str(thread_id))
    messages = await message_repo.list_messages(tid, session)
    count = len(messages)
    if count < SUMMARY_TRIGGER_MESSAGES or count % SUMMARY_TRIGGER_MESSAGES != 0:
        return

    # 最近一个窗口的对话（约 5 轮），保证输入有界
    window = messages[-SUMMARY_TRIGGER_MESSAGES:]
    window_text = "\n".join(f"{m.role}: {m.content}" for m in window)

    # 已有摘要（若存在）作为延续上下文
    existing_items = await memory_repo.list_by_user(user_id, session)
    existing_summary = next(
        (it.memory_value for it in existing_items if it.category == SUMMARY_CATEGORY),
        None,
    )
    base = f"【已有长期摘要】\n{existing_summary}\n\n" if existing_summary else ""
    payload = base + "【本轮新增对话】\n" + window_text

    template = PROMPTS["summary_prompt"].template
    resp = await llm.ainvoke(
        [HumanMessage(content=f"{template}\n\n以下是对话内容：\n{payload}")]
    )
    summary = resp.content if isinstance(resp.content, str) else str(resp.content)

    await memory_repo.upsert_item(
        user_id=user_id,
        memory_key=SUMMARY_MEMORY_KEY,
        memory_value=summary,
        category=SUMMARY_CATEGORY,
        now=_utcnow(),
        session=session,
    )
    await session.commit()
