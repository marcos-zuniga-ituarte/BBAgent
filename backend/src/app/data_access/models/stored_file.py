from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import String, DateTime, ForeignKey, Integer, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data_access.db import Base
from app.data_access.utils import utc_now

if TYPE_CHECKING:
    from app.data_access.models.user import User
    from app.data_access.models.chat import Chat
    from app.data_access.models.message import Message


class StoredFile(Base):
    __tablename__ = "stored_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    chat_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("chats.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    message_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    aux_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    filename: Mapped[str] = mapped_column(String(500), nullable=False)

    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)

    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    user: Mapped["User"] = relationship()
    chat: Mapped[Optional["Chat"]] = relationship()
    message: Mapped[Optional["Message"]] = relationship()

    def __repr__(self) -> str:
        return (
            f"StoredFile(id={self.id!r}, filename={self.filename!r}, "
            f"size={self.size_bytes!r}, user_id={self.user_id!r})"
        )