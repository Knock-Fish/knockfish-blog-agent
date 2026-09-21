"""异步数据库会话
提供引擎、会话工厂与 FastAPI 依赖，供路由层通过 Depends 注入。
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import settings

# 异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,   # 取连接前探活，避免拿到已被数据库断开的连接
    pool_size=10,
    max_overflow=20,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 提交后不让对象属性失效
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """每个请求一个 session，请求结束自动关闭。"""
    async with SessionLocal() as session:
        yield session


async def init_models() -> None:
    """幂等建表：仅创建尚未存在的业务表（如 memory_items），已有表（threads/messages）自动跳过。

    项目未引入 Alembic，业务表此前由手动 SQL / 外部脚本创建；此处对 SQLAlchemy metadata
    做一次 create_all（checkfirst 默认开启，已存在的表不会重建），保证新增模型自包含落地。
    """
    # 确保模型已注册到 Base.metadata（import 触发类定义时的注册副作用）
    from ..models.conversation import Base  # noqa: F401  Thread / Message

    import app.models.memory  # noqa: F401  MemoryItem

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
