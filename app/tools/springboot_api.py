"""
Spring Boot 博客后端 API 工具集（LangChain Tools）

约定：
- HTTP_BASE_URL 已含 /api/agent 前缀（见 .env），因此这里只写相对路径，如 "/article/search"。
- HTTP 客户端（app/utils/http/client.py）已自动解析 {code, msg, data} 统一响应并返回 data，
  业务码非 200 会抛 APIError；JWT 透传由客户端统一处理（这些接口为 @PublicApi，无需登录）。
- 工具返回值必须是字符串（最终作为上下文喂给 LLM），因此统一做可读化格式化。
"""
from langchain_core.tools import tool

from ..utils.http.client import APIError, get


# ---------------- 文章 ----------------

@tool
async def search_articles(keyword: str) -> str:
    """
    按关键词搜索已发布文章（标题/简介/正文模糊匹配）。
    当用户想找某个主题的文章、但不知道文章ID或标签时调用。
    Args:
        keyword: 搜索关键词
    """
    try:
        items = await get("/article/search", params={"keyword": keyword})
    except APIError as e:
        return f"搜索文章失败：{e.msg}"
    if not items:
        return f"未找到与「{keyword}」相关的文章"
    lines = [f"找到 {len(items)} 篇与「{keyword}」相关的文章："]
    for a in items:
        lines.append(
            f"- #{a.get('articleId')} {a.get('title', '无标题')}"
            f"（标签：{a.get('tagNames') or '无'}）"
            f"\n  简介：{a.get('description') or '无'}"
        )
    return "\n".join(lines)


@tool
async def get_blog_post(post_id: int) -> str:
    """
    根据文章ID获取完整文章正文。
    当用户已锁定某篇文章、需要阅读完整内容时调用；
    可配合 search_articles / get_blog_posts_by_tag 得到的 articleId 使用。
    Args:
        post_id: 文章ID（articleId）
    """
    try:
        item = await get(f"/article/{post_id}")
    except APIError as e:
        return f"获取文章失败：{e.msg}"
    if not item:
        return f"未找到ID为 {post_id} 的文章"
    title = item.get("title", "无标题")
    desc = item.get("description") or ""
    content = item.get("content", "无内容")
    head = f"标题：{title}"
    if desc:
        head += f"\n简介：{desc}"
    return f"{head}\n\n正文：\n{content}"


@tool
async def get_blog_posts_by_tag(tag_name: str) -> str:
    """
    根据标签名查询该标签下的所有文章。
    当用户想按分类浏览（如“Spring Boot 相关的文章”）时调用；
    若不确定有哪些标签，先调用 get_all_tags。
    Args:
        tag_name: 标签名称（如 Java、Spring Boot）
    """
    try:
        items = await get("/article/byTag", params={"tagName": tag_name})
    except APIError as e:
        return f"查询标签文章失败：{e.msg}"
    if not items:
        return f"未找到标签为「{tag_name}」的文章"
    lines = [f"标签「{tag_name}」下共 {len(items)} 篇文章："]
    for a in items:
        lines.append(f"- #{a.get('articleId')} {a.get('title', '无标题')}：{a.get('description') or ''}")
    return "\n".join(lines)


@tool
async def get_all_tags() -> str:
    """
    获取博客全部标签列表（含标签名与颜色）。
    当用户想了解有哪些文章分类/标签，或在按标签查询前需确认准确标签名时调用。
    """
    try:
        items = await get("/tag")
    except APIError as e:
        return f"获取标签失败：{e.msg}"
    if not items:
        return "暂无标签"
    return "全部标签：" + "、".join(t.get("tagName", "") for t in items)


# ---------------- 笔记 ----------------

@tool
async def search_notes(keyword: str) -> str:
    """
    按关键词搜索笔记（标题/内容模糊匹配）。当用户想找某个主题的笔记时调用。
    Args:
        keyword: 搜索关键词
    """
    try:
        items = await get("/note/search", params={"keyword": keyword})
    except APIError as e:
        return f"搜索笔记失败：{e.msg}"
    if not items:
        return f"未找到与「{keyword}」相关的笔记"
    lines = [f"找到 {len(items)} 条与「{keyword}」相关的笔记："]
    for n in items:
        lines.append(f"- #{n.get('noteId')} {n.get('noteTitle', '无标题')}（{n.get('createTime') or '未知时间'}）")
    lines.append("提示：需要正文时调用 get_note 并传入 noteId。")
    return "\n".join(lines)


@tool
async def get_note(note_id: int) -> str:
    """
    根据笔记ID获取笔记完整内容。配合 search_notes 得到的 noteId 使用。
    Args:
        note_id: 笔记ID
    """
    try:
        item = await get(f"/note/{note_id}")
    except APIError as e:
        return f"获取笔记失败：{e.msg}"
    if not item:
        return f"未找到ID为 {note_id} 的笔记"
    return f"标题：{item.get('noteTitle', '无标题')}\n\n正文：\n{item.get('noteContent', '无内容')}"


# ---------------- 代码片段 ----------------

@tool
async def search_code_snippets(keyword: str) -> str:
    """
    按关键词搜索代码片段（标题/代码内容模糊匹配）。
    当用户需要示例代码、工具方法、配置片段时调用。
    Args:
        keyword: 搜索关键词（如 “Redis 配置”、“文件下载”）
    """
    try:
        items = await get("/code/search", params={"keyword": keyword})
    except APIError as e:
        return f"搜索代码片段失败：{e.msg}"
    if not items:
        return f"未找到与「{keyword}」相关的代码片段"
    lines = [f"找到 {len(items)} 个与「{keyword}」相关的代码片段："]
    for c in items:
        lines.append(f"- #{c.get('codeSnippetId')} {c.get('title', '无标题')}\n```\n{c.get('codeContent', '')}\n```")
    return "\n".join(lines)


# ---------------- 站点 & 博主 ----------------

@tool
async def get_site_info() -> str:
    """
    获取博客站点基础信息与内容统计（站点名、简介，及文章/标签/分类/笔记/代码片/友链/导航数量）。
    当用户问“这个博客有多少文章”“这个博客是做什么的”等概览性问题时调用。
    """
    try:
        info = await get("/site/info")
    except APIError as e:
        return f"获取站点信息失败：{e.msg}"
    if not info:
        return "暂无站点信息"
    return (
        f"站点：{info.get('siteName', '未命名')}\n"
        f"简介：{info.get('siteDescription') or '无'}\n"
        f"统计：文章 {info.get('articleCount', 0)} 篇 / 标签 {info.get('tagCount', 0)} 个 / "
        f"分类 {info.get('categoryCount', 0)} 个 / 笔记 {info.get('noteCount', 0)} 条 / "
        f"代码片段 {info.get('codeSnippetCount', 0)} 个 / 友链 {info.get('linkCount', 0)} 个 / "
        f"导航站点 {info.get('siteCount', 0)} 个"
    )


@tool
async def get_blogger_info() -> str:
    """
    获取博主公开个人信息（昵称、简介、邮箱、GitHub / B站链接、文章数等）。
    当用户问“博主是谁”“怎么联系博主”“博主有哪些社交账号”时调用。
    """
    try:
        u = await get("/user/info")
    except APIError as e:
        return f"获取博主信息失败：{e.msg}"
    if not u:
        return "暂无博主信息"
    lines = [
        f"昵称：{u.get('nickname', '匿名')}",
        f"简介：{u.get('description') or '无'}",
        f"邮箱：{u.get('email') or '未公开'}",
        f"发表文章：{u.get('articleCount', 0)} 篇",
    ]
    if u.get("githubUrl"):
        lines.append(f"GitHub：{u['githubUrl']}")
    if u.get("bilibiliUrl"):
        lines.append(f"B站：{u['bilibiliUrl']}")
    return "\n".join(lines)
