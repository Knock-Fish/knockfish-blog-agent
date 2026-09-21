"""
会话与消息的 ORM 模型
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """所有 ORM 模型的基类"""
    pass


class Thread(Base):
    """会话线程 —— 对应 threads 表"""

    __tablename__ = "threads"

    thread_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, comment="会话 ID，应用层 uuid4 生成"
    )
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255))
    last_message: Mapped[Optional[str]] = mapped_column(Text)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="thread",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Thread {self.thread_id} count={self.message_count}>"


class Message(Base):
    """会话消息 —— 对应 messages 表"""

    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role IN ('user','assistant','system','tool')", name="ck_messages_role"),
        CheckConstraint("role <> 'tool' OR tool_call_id IS NOT NULL", name="ck_tool_needs_call_id"),
    )

    message_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="BIGSERIAL，数据库自增"
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("threads.thread_id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tool_calls: Mapped[Optional[list]] = mapped_column(JSONB)      # 工具调用列表（数组）
    tool_call_id: Mapped[Optional[str]] = mapped_column(String(64))
    tokens: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    thread: Mapped["Thread"] = relationship(back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message {self.message_id} role={self.role}>"
