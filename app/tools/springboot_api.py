from langchain.tools import tool
from ..utils.http.client import get, post, APIError, APITimeoutError, APIConnectionError


# ==================== 文章相关工具 ====================

@tool
async def search_blog_posts(keyword: str) -> str:
    """
    关键词搜索已发布文章。当用户想查找某主题的文章时调用。
    搜索范围：标题、简介、内容（模糊匹配）。
    返回：文章ID、标题、简介、发布时间、标签。
    Args:
        keyword: 搜索关键词
    """
    try:
        items = await get("/article/search", params={"keyword": keyword})

        if not items:
            return f"未找到与关键词「{keyword}」相关的文章"

        result = f"🔍 关键词搜索「{keyword}」共找到 {len(items)} 篇文章：\n\n"
        for idx, item in enumerate(items, 1):
            article_id = item.get('articleId')
            title = item.get('title', '无标题')
            description = item.get('description', '')
            publish_time = item.get('publishTime', '')
            tag_names = item.get('tagNames') or ''

            result += f"【{idx}】📄 《{title}》(ID: {article_id})\n"
            if publish_time:
                result += f"    📅 发布时间：{publish_time}\n"
            if description:
                result += f"    📝 简介：{description}\n"
            if tag_names:
                result += f"    🏷️ 标签：{tag_names}\n"
            result += "\n"
        return result

    except APIError as e:
        return f"搜索文章失败：{e.msg}"
    except APITimeoutError:
        return "服务超时，请稍后再试"
    except APIConnectionError as e:
        return f"网络连接失败：{e.msg}"
    except Exception as e:
        return f"搜索文章异常：{str(e)}"


@tool
async def get_blog_post(post_id: int) -> str:
    """
    根据文章ID获取完整文章内容。当用户需要阅读某篇具体文章时调用。
    Args:
        post_id: 文章ID
    """
    try:
        item = await get(f"/article/{post_id}")

        if not item:
            return f"未找到ID为 {post_id} 的文章"

        title = item.get('title', '无标题')
        content = item.get('content', '无内容')
        description = item.get('description', '')

        result = f"📄 标题：{title}\n\n"
        if description:
            result += f"📝 简介：{description}\n\n"
        result += f"📖 正文：\n{content}"
        return result

    except APIError as e:
        return f"获取文章失败：{e.msg}"
    except APITimeoutError:
        return "服务超时，请稍后再试"
    except APIConnectionError as e:
        return f"网络连接失败：{e.msg}"
    except Exception as e:
        return f"获取文章异常：{str(e)}"


@tool
async def get_blog_posts_by_tag(tag_name: str) -> str:
    """
    根据标签名查询文章。当用户想查找带有某个标签的所有文章时调用。
    Args:
        tag_name: 标签名称（例如：Java、Spring Boot）
    """
    try:
        items = await get("/article/byTag", params={"tagName": tag_name})

        if not items:
            return f"未找到标签「{tag_name}」下的文章"

        result = f"🏷️ 标签「{tag_name}」下共有 {len(items)} 篇文章：\n\n"
        for idx, item in enumerate(items, 1):
            article_id = item.get('articleId')
            title = item.get('title', '无标题')
            description = item.get('description', '')
            publish_time = item.get('publishTime', '')

            result += f"【{idx}】📄 《{title}》(ID: {article_id})\n"
            if publish_time:
                result += f"    📅 发布时间：{publish_time}\n"
            if description:
                result += f"    📝 简介：{description}\n"
            result += "\n"
        return result

    except APIError as e:
        return f"按标签查询文章失败：{e.msg}"
    except APITimeoutError:
        return "服务超时，请稍后再试"
    except APIConnectionError as e:
        return f"网络连接失败：{e.msg}"
    except Exception as e:
        return f"按标签查询文章异常：{str(e)}"


@tool
async def get_all_tags() -> str:
    """
    获取全部标签列表。当用户想了解博客有哪些标签分类时调用。
    """
    try:
        items = await get("/tag")

        if not items:
            return "博客目前还没有设置任何标签"

        result = f"🏷️ 博客共有 {len(items)} 个标签：\n\n"
        for idx, item in enumerate(items, 1):
            tag_id = item.get('tagId')
            tag_name = item.get('tagName', '')
            color = item.get('color', '')

            result += f"【{idx}】{tag_name} (ID: {tag_id})"
            if color:
                result += f" 颜色：{color}"
            result += "\n"
        return result

    except APIError as e:
        return f"获取标签列表失败：{e.msg}"
    except APITimeoutError:
        return "服务超时，请稍后再试"
    except APIConnectionError as e:
        return f"网络连接失败：{e.msg}"
    except Exception as e:
        return f"获取标签列表异常：{str(e)}"


# ==================== 代码片段工具 ====================

@tool
async def search_code_snippets(keyword: str) -> str:
    """
    代码片段关键词检索。当用户想查找某主题的代码示例时调用。
    搜索范围：标题、代码内容（模糊匹配）。
    Args:
        keyword: 搜索关键词（例如：Python、数据库、排序）
    """
    try:
        items = await get("/code/search", params={"keyword": keyword})

        if not items:
            return f"未找到与关键词「{keyword}」相关的代码片段"

        result = f"💻 关键词搜索「{keyword}」共找到 {len(items)} 个代码片段：\n\n"
        for idx, item in enumerate(items, 1):
            snippet_id = item.get('codeSnippetId')
            title = item.get('title', '无标题')
            category_id = item.get('codeCategoryId')
            create_time = item.get('createTime', '')

            result += f"【{idx}】📝 《{title}》(ID: {snippet_id})\n"
            if category_id:
                result += f"    📂 分类ID：{category_id}\n"
            if create_time:
                result += f"    📅 创建时间：{create_time}\n"
            result += "\n"
        return result

    except APIError as e:
        return f"搜索代码片段失败：{e.msg}"
    except APITimeoutError:
        return "服务超时，请稍后再试"
    except APIConnectionError as e:
        return f"网络连接失败：{e.msg}"
    except Exception as e:
        return f"搜索代码片段异常：{str(e)}"


@tool
async def get_code_snippets_by_category(category_id: int) -> str:
    """
    根据语言分类查询代码。当用户想看某个编程语言/分类下的全部代码时调用。
    Args:
        category_id: 代码分类ID（可先通过 get_all_code_categories 获取）
    """
    try:
        items = await get("/code/byCategory", params={"categoryId": category_id})

        if not items:
            return f"分类ID {category_id} 下没有代码片段"

        result = f"📂 分类ID {category_id} 下共有 {len(items)} 个代码片段：\n\n"
        for idx, item in enumerate(items, 1):
            snippet_id = item.get('codeSnippetId')
            title = item.get('title', '无标题')
            create_time = item.get('createTime', '')

            result += f"【{idx}】📝 《{title}》(ID: {snippet_id})\n"
            if create_time:
                result += f"    📅 创建时间：{create_time}\n"
            result += "\n"
        return result

    except APIError as e:
        return f"按分类查询代码失败：{e.msg}"
    except APITimeoutError:
        return "服务超时，请稍后再试"
    except APIConnectionError as e:
        return f"网络连接失败：{e.msg}"
    except Exception as e:
        return f"按分类查询代码异常：{str(e)}"


@tool
async def get_all_code_categories() -> str:
    """
    获取所有代码语言分类。当用户想了解有哪些代码分类时调用。
    """
    try:
        items = await get("/code/category")

        if not items:
            return "目前还没有代码分类"

        result = "📚 代码语言分类列表：\n\n"
        for idx, item in enumerate(items, 1):
            category_id = item.get('codeCategoryId')
            category_name = item.get('codeCategoryName', '')
            sort = item.get('sort')

            result += f"【{idx}】{category_name} (ID: {category_id})"
            if sort is not None:
                result += f" 排序：{sort}"
            result += "\n"
        return result

    except APIError as e:
        return f"获取代码分类失败：{e.msg}"
    except APITimeoutError:
        return "服务超时，请稍后再试"
    except APIConnectionError as e:
        return f"网络连接失败：{e.msg}"
    except Exception as e:
        return f"获取代码分类异常：{str(e)}"


# ==================== 笔记工具 ====================

@tool
async def search_notes(keyword: str) -> str:
    """
    笔记关键词搜索。当用户想查找某主题的学习笔记时调用。
    搜索范围：标题、笔记内容（模糊匹配）。
    Args:
        keyword: 搜索关键词
    """
    try:
        items = await get("/note/search", params={"keyword": keyword})

        if not items:
            return f"未找到与关键词「{keyword}」相关的笔记"

        result = f"📒 关键词搜索「{keyword}」共找到 {len(items)} 篇笔记：\n\n"
        for idx, item in enumerate(items, 1):
            note_id = item.get('noteId')
            title = item.get('noteTitle', '无标题')
            create_time = item.get('createTime', '')

            result += f"【{idx}】📝 《{title}》(ID: {note_id})\n"
            if create_time:
                result += f"    📅 创建时间：{create_time}\n"
            result += "\n"
        return result

    except APIError as e:
        return f"搜索笔记失败：{e.msg}"
    except APITimeoutError:
        return "服务超时，请稍后再试"
    except APIConnectionError as e:
        return f"网络连接失败：{e.msg}"
    except Exception as e:
        return f"搜索笔记异常：{str(e)}"


@tool
async def get_note(note_id: int) -> str:
    """
    笔记详情查询。当用户想阅读某篇具体笔记的完整内容时调用。
    Args:
        note_id: 笔记ID
    """
    try:
        item = await get(f"/note/{note_id}")

        if not item:
            return f"未找到ID为 {note_id} 的笔记"

        title = item.get('noteTitle', '无标题')
        content = item.get('noteContent', '无内容')

        result = f"📒 笔记标题：{title}\n\n"
        result += f"📖 笔记内容：\n{content}"
        return result

    except APIError as e:
        return f"获取笔记失败：{e.msg}"
    except APITimeoutError:
        return "服务超时，请稍后再试"
    except APIConnectionError as e:
        return f"网络连接失败：{e.msg}"
    except Exception as e:
        return f"获取笔记异常：{str(e)}"


# ==================== 友链 & 站点导航工具 ====================

@tool
async def get_links() -> str:
    """
    获取展示状态的友链列表。当用户想查看推荐的友情链接时调用。
    自动过滤掉未展示的链接。
    """
    try:
        items = await get("/link/list")

        if not items:
            return "目前还没有展示中的友情链接"

        result = f"🔗 友情链接（共 {len(items)} 个）：\n\n"
        for idx, item in enumerate(items, 1):
            link_id = item.get('linkId')
            link_name = item.get('linkName', '')
            link_url = item.get('linkUrl', '')
            avatar = item.get('avatar', '')
            description = item.get('description', '')

            result += f"【{idx}】🌐 {link_name} (ID: {link_id})\n"
            if link_url:
                result += f"    🔗 链接：{link_url}\n"
            if description:
                result += f"    📝 简介：{description}\n"
            result += "\n"
        return result

    except APIError as e:
        return f"获取友链列表失败：{e.msg}"
    except APITimeoutError:
        return "服务超时，请稍后再试"
    except APIConnectionError as e:
        return f"网络连接失败：{e.msg}"
    except Exception as e:
        return f"获取友链列表异常：{str(e)}"


@tool
async def get_site_list(category_id: int = None) -> str:
    """
    获取导航站点列表。当用户想查看推荐的网站导航时调用。
    可按分类ID过滤，不传则返回全部。
    Args:
        category_id: 分类ID（可选），不传则返回所有站点
    """
    try:
        params = {}
        if category_id is not None:
            params["categoryId"] = category_id

        items = await get("/site/list", params=params if params else None)

        if not items:
            suffix = f"分类ID {category_id} 下" if category_id is not None else ""
            return f"{suffix}没有导航站点"

        prefix = f"分类ID {category_id} 下的" if category_id is not None else ""
        result = f"🗺️ {prefix}导航站点（共 {len(items)} 个）：\n\n"
        for idx, item in enumerate(items, 1):
            site_id = item.get('siteId')
            site_name = item.get('siteName', '')
            site_url = item.get('siteUrl', '')
            category_name = item.get('categoryName', '')
            description = item.get('description', '')

            result += f"【{idx}】🌐 {site_name} (ID: {site_id})\n"
            if category_name:
                result += f"    📂 分类：{category_name}\n"
            if site_url:
                result += f"    🔗 链接：{site_url}\n"
            if description:
                result += f"    📝 简介：{description}\n"
            result += "\n"
        return result

    except APIError as e:
        return f"获取导航站点失败：{e.msg}"
    except APITimeoutError:
        return "服务超时，请稍后再试"
    except APIConnectionError as e:
        return f"网络连接失败：{e.msg}"
    except Exception as e:
        return f"获取导航站点异常：{str(e)}"


# ==================== 资源 & 基础信息工具 ====================

@tool
async def get_files_by_reference(reference_type: str, reference_id: int) -> str:
    """
    业务附件查询。当用户想查看某篇文章、笔记等业务对象关联的附件文件时调用。
    Args:
        reference_type: 关联类型，例如 "article" 表示文章，"note" 表示笔记
        reference_id: 关联对象的ID，例如文章ID或笔记ID
    """
    try:
        items = await get("/file/list", params={
            "referenceType": reference_type,
            "referenceId": reference_id
        })

        if not items:
            return f"类型「{reference_type}」ID {reference_id} 没有关联的附件"

        result = f"📎 {reference_type} ID {reference_id} 关联的附件（共 {len(items)} 个）：\n\n"
        for idx, item in enumerate(items, 1):
            file_id = item.get('fileId')
            file_name = item.get('fileName', '')
            file_path = item.get('filePath', '')
            mime_type = item.get('mimeType', '')
            file_size = item.get('fileSize')
            create_time = item.get('createTime', '')

            result += f"【{idx}】📄 {file_name} (ID: {file_id})\n"
            if mime_type:
                result += f"    📦 类型：{mime_type}\n"
            if file_size is not None:
                result += f"    📏 大小：{file_size} 字节\n"
            if file_path:
                result += f"    📂 路径：{file_path}\n"
            if create_time:
                result += f"    📅 创建时间：{create_time}\n"
            result += "\n"
        return result

    except APIError as e:
        return f"查询附件失败：{e.msg}"
    except APITimeoutError:
        return "服务超时，请稍后再试"
    except APIConnectionError as e:
        return f"网络连接失败：{e.msg}"
    except Exception as e:
        return f"查询附件异常：{str(e)}"


@tool
async def get_site_info() -> str:
    """
    获取博客站点基础信息。当用户想了解博客的整体统计数据时调用。
    返回：站点名称、描述、文章数、标签数、分类数、笔记数、代码数、友链数、站点数。
    """
    try:
        info = await get("/site/info")

        if not info:
            return "暂时无法获取站点信息"

        site_name = info.get('siteName', '')
        site_description = info.get('siteDescription', '')
        article_count = info.get('articleCount', 0)
        tag_count = info.get('tagCount', 0)
        category_count = info.get('categoryCount', 0)
        note_count = info.get('noteCount', 0)
        code_count = info.get('codeSnippetCount', 0)
        link_count = info.get('linkCount', 0)
        site_count = info.get('siteCount', 0)

        result = f"🏠 {site_name}\n"
        if site_description:
            result += f"📝 {site_description}\n\n"
        else:
            result += "\n"
        result += "📊 站点统计：\n"
        result += f"  ✏️  已发布文章：{article_count} 篇\n"
        result += f"  🏷️  标签总数：{tag_count} 个\n"
        result += f"  📂 分类总数：{category_count} 个\n"
        result += f"  📒 笔记总数：{note_count} 篇\n"
        result += f"  💻 代码片段：{code_count} 个\n"
        result += f"  🔗 友情链接：{link_count} 个\n"
        result += f"  🗺️  导航站点：{site_count} 个\n"
        return result

    except APIError as e:
        return f"获取站点信息失败：{e.msg}"
    except APITimeoutError:
        return "服务超时，请稍后再试"
    except APIConnectionError as e:
        return f"网络连接失败：{e.msg}"
    except Exception as e:
        return f"获取站点信息异常：{str(e)}"


@tool
async def get_blogger_info() -> str:
    """
    获取博主公开个人信息。当用户想了解博主的资料时调用。
    敏感字段（密码等）已被屏蔽。
    返回：昵称、头像、简介、邮箱、GitHub、B站链接，以及文章数、标签数、站点数统计。
    """
    try:
        info = await get("/user/info")

        if not info:
            return "暂时无法获取博主信息"

        nickname = info.get('nickname', '博主')
        avatar = info.get('avatar', '')
        email = info.get('email', '')
        description = info.get('description', '')
        github_url = info.get('githubUrl', '')
        bilibili_url = info.get('bilibiliUrl', '')
        article_count = info.get('articleCount', 0)
        tag_count = info.get('tagCount', 0)
        site_count = info.get('siteCount', 0)

        result = f"👤 博主：{nickname}\n"
        if avatar:
            result += f"🖼️  头像：{avatar}\n"
        if description:
            result += f"📝 简介：{description}\n"
        if email:
            result += f"📧 邮箱：{email}\n"
        if github_url:
            result += f"💻 GitHub：{github_url}\n"
        if bilibili_url:
            result += f"📺 B站：{bilibili_url}\n"
        result += "\n📊 创作统计：\n"
        result += f"  ✏️  发布文章：{article_count} 篇\n"
        result += f"  🏷️  标签总数：{tag_count} 个\n"
        result += f"  🗺️  导航站点：{site_count} 个\n"
        return result

    except APIError as e:
        return f"获取博主信息失败：{e.msg}"
    except APITimeoutError:
        return "服务超时，请稍后再试"
    except APIConnectionError as e:
        return f"网络连接失败：{e.msg}"
    except Exception as e:
        return f"获取博主信息异常：{str(e)}"
