"""
工具注册中心：集中管理所有可供 agent 使用的工具

注意：在 springboot_api.py / time_tools.py 等模块中新增 @tool 后，
必须同时在这里导入并加入 tools 列表，否则该工具不会被 agent 感知到。
"""
from langchain_core.tools import BaseTool
from .springboot_api import (
    get_all_tags,
    get_blog_post,
    get_blog_posts_by_tag,
    get_blogger_info,
    get_note,
    get_site_info,
    search_articles,
    search_code_snippets,
    search_notes,
)
from .time_tools import (
    calculate_time_difference,
    convert_timezone,
    countdown,
    get_current_time,
    parse_date,
)
from .memory_tools import (
    remember_user_fact,
    recall_user_profile,
)

# 所有可供 agent 使用的工具列表
tools: list[BaseTool] = [
    search_articles,
    get_blog_post,
    get_blog_posts_by_tag,
    get_all_tags,
    search_notes,
    get_note,
    search_code_snippets,
    get_site_info,
    get_blogger_info,
    get_current_time,
    convert_timezone,
    calculate_time_difference,
    countdown,
    parse_date,
    remember_user_fact,
    recall_user_profile,
]
