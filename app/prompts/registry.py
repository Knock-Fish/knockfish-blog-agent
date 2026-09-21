"""提示词注册表：启动时扫描 prompts 目录下的 *.md，按 key 建立索引。

模板格式：文件开头用 YAML front-matter 声明元数据，正文顶格书写。

    ---
    key: system_prompt
    version: 1.0.0
    description: 技术博客问答助手系统提示词
    ---
    你是「{app_name}」...

front-matter 用 yaml.safe_load 解析（支持嵌套，比逐行 split(":") 更稳），
正文保持 Markdown 原样，不做缩进，避免 YAML 块标量漏写 `|` 吞掉换行的问题。

注册表在导入时一次性加载全部模板到进程内单例 PROMPTS，
build_system_message 再按 prompt_key 从中选取，避免每次请求读盘。
"""
from __future__ import annotations

import re

import yaml
from pathlib import Path
from typing import Dict, Tuple

_PROMPTS_DIR = Path(__file__).resolve().parent
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)


class PromptTemplate:
    """单个提示词模板，封装元信息与正文，并提供类型安全的渲染。"""

    def __init__(
        self,
        key: str,
        version: str,
        description: str,
        template: str,
    ) -> None:
        self.key = key
        self.version = version
        self.description = description
        self.template = template  # 提示词正文

    def render(self, **kwargs) -> str:
        """用给定上下文渲染模板。

        Args:
            **kwargs: 占位符键值（如 app_name、user_identity）。

        Returns:
            渲染后的提示词字符串。

        Raises:
            KeyError: 模板引用了未提供的占位符（fail-fast，便于早暴露问题）。
        """
        # str.format 会忽略模板中未出现的多余 kwargs，因此无占位符的
        # 模板（如 summary_prompt）即使收到 chat 类参数也能安全渲染。
        return self.template.format(**kwargs)


def _parse_frontmatter(text: str) -> Tuple[dict, str]:
    """剥离 YAML front-matter，返回 (元数据字典, 正文)。

    front-matter 交由 yaml.safe_load 解析，因此支持嵌套结构与标准 YAML 类型；
    解析结果不是字典时降级为空字典，避免元数据污染。
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    meta = yaml.safe_load(match.group(1))
    if not isinstance(meta, dict):
        meta = {}
    return meta, text[match.end():]


def load_prompts(directory: Path = _PROMPTS_DIR) -> Dict[str, PromptTemplate]:
    """扫描目录下所有 *.md，构建 key -> PromptTemplate 映射。

    Args:
        directory: 提示词目录，默认当前包目录。

    Returns:
        以模板 key 为索引的字典。

    Raises:
        RuntimeError: 目录下没有任何 .md 模板时抛出。
    """
    prompts: Dict[str, PromptTemplate] = {}
    for path in sorted(directory.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(raw)
        key = meta.get("key") or path.stem
        prompts[key] = PromptTemplate(
            key=key,
            version=str(meta.get("version", "0.0.0")),
            description=meta.get("description", ""),
            template=body.strip(),
        )
    if not prompts:
        raise RuntimeError(f"未找到任何提示词模板: {directory}")
    return prompts


# 进程内单例：只在导入时加载一次
PROMPTS: Dict[str, PromptTemplate] = load_prompts()
DEFAULT_PROMPT_KEY: str = "system_prompt"
