import json
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data_access.db import Base
from app.data_access.repositories.stored_file_repository import StoredFileRepository
from app.data_access.utils import utc_now

if TYPE_CHECKING:
    from app.data_access.models.chat import Chat


class Message(Base):
    __tablename__ = "messages"

    class Role(StrEnum):
        USER = "user"
        ASSISTANT = "assistant"
        DEVELOPER = "developer"
        SYSTEM = "system"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    chat_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    _content: Mapped[str] = mapped_column("content", Text, nullable=False)
    show: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    chat: Mapped["Chat"] = relationship(back_populates="messages")

    @property
    def content(self) -> dict[str, Any]:
        return json.loads(self._content)

    @content.setter
    def content(self, value: dict[str, Any]) -> None:
        self._content = json.dumps(value, ensure_ascii=False)

    def __repr__(self) -> str:
        preview = str(self.content)[:30]
        return f"Message(id={self.id!r}, show={self.show!r}, content={preview!r})"

    def add_file(
            self,
            filename: str,
            mime_type: str,
            data: bytes,
            aux_file_id: str | None = None,
    ):
        return StoredFileRepository.create_for_message(
            message_id=self.id,
            chat_id=self.chat_id,
            filename=filename,
            mime_type=mime_type,
            data=data,
            aux_file_id=aux_file_id,
        )

    def add_files(
            self,
            files: list[dict],
    ):
        return StoredFileRepository.create_many_for_message(
            message_id=self.id,
            chat_id=self.chat_id,
            files=files,
        )

    def get_files(self):
        return StoredFileRepository.get_by_message(self.id)