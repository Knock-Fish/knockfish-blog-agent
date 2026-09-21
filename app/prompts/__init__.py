"""提示词包：对外暴露注册表，逻辑实现见 registry 模块。"""
from .registry import (
    DEFAULT_PROMPT_KEY,
    PROMPTS,
    PromptTemplate,
    load_prompts,
)

__all__ = ["PROMPTS", "DEFAULT_PROMPT_KEY", "PromptTemplate", "load_prompts"]