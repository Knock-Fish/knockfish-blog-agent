"""工具注册中心测试：防止新增 @tool 后忘记在 registry.py 里 import。"""
from app.tools.registry import tools
from langchain_core.tools import BaseTool


def test_tool_count_is_16():
    assert len(tools) == 16


def test_all_are_langchain_tools():
    assert all(isinstance(t, BaseTool) for t in tools)


def test_core_tools_present():
    names = {t.name for t in tools}
    for name in ("get_current_time", "recall_user_profile", "search_articles"):
        assert name in names
