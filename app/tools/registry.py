"""工具注册中心：集中管理所有可供 agent 使用的工具"""
from langchain.tools import BaseTool

from .springboot_api import (
    get_blog_post,
    search_blog_posts,
    get_blog_posts_by_tag,
    get_all_tags,
    search_code_snippets,
    get_code_snippets_by_category,
    get_all_code_categories,
    search_notes,
    get_note,
    get_links,
    get_site_list,
    get_files_by_reference,
    get_site_info,
    get_blogger_info,
)

# 所有可供 agent 使用的工具列表
tools: list[BaseTool] = [
    # 文章相关
    search_blog_posts,
    get_blog_post,
    get_blog_posts_by_tag,
    get_all_tags,
    # 代码片段相关
    search_code_snippets,
    get_code_snippets_by_category,
    get_all_code_categories,
    # 笔记相关
    search_notes,
    get_note,
    # 友链 & 站点导航
    get_links,
    get_site_list,
    # 资源 & 基础信息
    get_files_by_reference,
    get_site_info,
    get_blogger_info,
]
