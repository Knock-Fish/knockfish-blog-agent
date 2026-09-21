"""长期记忆工具：让 LLM 自主「记住 / 回忆」关于用户的事实

与 springboot_api.py（调远程后端）不同，本模块直接读写本地 PostgreSQL 的 memory_items 表。
为避免把 user_id 暴露成工具参数（越权风险），user_id 通过 request_context 的 contextvar
获取——它已在 chat 端点入口由可信的鉴权结果 set 好。DB session 则在工具内部自建，自包含。

docstring 是给 LLM 看的：务必写清「何时调用 + 参数含义」，否则模型不会主动使用。
"""
from langchain_core.tools import tool

from ..core.db import SessionLocal
from ..core.request_context import get_current_user_id
from ..services import long_term_memory_service as ltm


@tool
async def remember_user_fact(key: str, value: str, category: str = "fact") -> str:
    """当用户在对话中透露了关于自己的稳定信息（技术栈、身份、目标、偏好等）时，主动调用本工具将其记住，以便后续对话更个性化。例如用户说「我主要做前端，用 Vue3」或「我在准备秋招」，应分别记住 tech_stack=Vue3 / goal=秋招。

    Args:
        key: 记忆条目的简短键名，建议语义化，如 tech_stack（技术栈）、role（身份）、goal（目标）、preference_theme（主题偏好）
        value: 记忆条目的具体值，如 "Vue3 + TypeScript"、"应届生正在秋招"、"喜欢简洁的回答"
        category: 分类，profile=用户身份画像，preference=偏好，fact=其他事实（默认 fact）
    """
    user_id = get_current_user_id()
    if user_id is None:
        return "无法识别当前用户，记忆未保存（请确认请求已通过鉴权）"
    async with SessionLocal() as session:
        await ltm.remember_fact(
            user_id=user_id, key=key, value=value, category=category, session=session
        )
    return f"已记住：{key} = {value}"


@tool
async def recall_user_profile() -> str:
    """当需要了解用户是谁、有什么偏好或历史信息时调用，例如用户问「你还记得我之前说的吗」「你知道我是做什么的吗」。返回已保存的用户记忆摘要。

    Returns:
        已保存的用户记忆文本；若还没有任何记忆则返回提示文案。
    """
    user_id = get_current_user_id()
    if user_id is None:
        return "无法识别当前用户"
    async with SessionLocal() as session:
        profile = await ltm.recall_profile(user_id=user_id, session=session)
    if profile["context"] == "暂无":
        return "目前还没有关于你的记忆，对话中透露的信息我会主动帮你记住。"
    return f"已保存的用户记忆：\n{profile['context']}"
