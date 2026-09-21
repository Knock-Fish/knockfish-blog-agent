"""长期记忆 ORM 模型

memory_items 表：存储「关于用户的稳定事实」，由 Agent 通过 remember/recall 工具读写，
实现跨会话个性化（越用越懂你）。与 threads/messages（会话级短期记忆）互不影响。

字段约定：
    - memory_key：简短键名，如 tech_stack / role / goal / preference_theme
    - memory_value：具体值，如 "Vue3 + TypeScript" / "应届生正在秋招"
    - category：profile=用户身份画像 / preference=偏好 / fact=其他事实
    - (user_id, memory_key) 唯一：同一用户对同一 key 反复 remember 即覆盖更新
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .conversation import Base


class MemoryItem(Base):
    """长期记忆条目 —— 对应 memory_items 表"""

    __tablename__ = "memory_items"
    __table_args__ = (
        UniqueConstraint("user_id", "memory_key", name="uq_memory_user_key"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="BIGSERIAL，数据库自增"
    )
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="用户 ID，按用户隔离记忆")
    memory_key: Mapped[str] = mapped_column(String(128), nullable=False, comment="记忆键名")
    memory_value: Mapped[str] = mapped_column(Text, nullable=False, comment="记忆值")
    category: Mapped[str] = mapped_column(
        String(32), nullable=False, default="fact", comment="分类：profile / preference / fact"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return f"<MemoryItem {self.id} user={self.user_id} key={self.memory_key}>"
