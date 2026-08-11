"""提示词模板加载中心

将 prompt 目录下的 .md 文件加载为 ChatPromptTemplate。
- 含 {var} 占位符的模板，运行时通过 invoke 传参填充
- 无占位符的模板，作为静态 system 消息使用
"""
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

_PROMPT_DIR = Path(__file__).parent


def _load(name: str) -> str:
    """读取指定名称的 .md 提示词文件"""
    return (_PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8")


# ---- 角色设定模板（含占位符 {current_time} 等）----
role_prompt = ChatPromptTemplate.from_messages([
    ("system", _load("role")),
    MessagesPlaceholder(variable_name="messages"),
]).partial(
    # 预填有默认值的占位符，运行时只需提供 current_time 和 messages
    user_identity="访客",
    user_preferences="无",
)

# ---- 文章检索 Agent 系统提示词（静态，无占位符）----
article_agent_prompt = ChatPromptTemplate.from_messages([
    ("system", _load("article_agent_system")),
    MessagesPlaceholder(variable_name="messages"),
])
