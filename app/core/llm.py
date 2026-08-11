from langchain_openai import ChatOpenAI
from .config import settings


# 全局单例 LLM 对象


def get_chat_llm() -> ChatOpenAI:
    """
    获取对话大模型实例，全局复用
    """
    return ChatOpenAI(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL if hasattr(settings, "LLM_BASE_URL") else None,
        model=settings.LLM_MODEL_ID,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=2048,
        timeout=settings.LLM_TIMEOUT
    )


# 导出全局实例，项目各处直接导入 llm 使用
llm = get_chat_llm()
