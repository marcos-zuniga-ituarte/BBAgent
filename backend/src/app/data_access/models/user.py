import json
from datetime import datetime
from typing import Optional, TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import String, Text, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data_access.db import Base
from app.data_access.utils import utc_now

if TYPE_CHECKING:
    from app.data_access.models.chat import Chat
    from app.data_access.models.user_session import UserSession


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    login: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    _memory: Mapped[str] = mapped_column("memory", Text, nullable=False, default="{}")
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)

    chats: Mapped[list["Chat"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="Chat.created_at",
    )

    sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="UserSession.created_at",
    )

    def set_password_hash(self, password_hash: str) -> None:
        self.password_hash = password_hash
        self.save()

    def set_system_prompt(self, system_prompt: Optional[str]) -> None:
        self.system_prompt = system_prompt.strip() if system_prompt and system_prompt.strip() else None
        self.save()

    def deactivate(self) -> None:
        self.is_active = False
        self.save()

    def activate(self) -> None:
        self.is_active = True
        self.save()

    def create_chat(self, title: str = None) -> "Chat":
        from app.data_access.repositories.user_repository import UserRepository
        return UserRepository.create_chat(self.id, title)

    def get_chats(self) -> list["Chat"]:
        from app.data_access.repositories.user_repository import UserRepository
        return UserRepository.get_chats(self.id)

    def get_chat(self, chat_id: str) -> Optional["Chat"]:
        from app.data_access.repositories.user_repository import UserRepository
        return UserRepository.get_chat(self.id, chat_id)

    def save(self) -> None:
        from app.data_access.repositories.user_repository import UserRepository
        UserRepository.save(self)

    @staticmethod
    def get_by_id(user_id: str) -> Optional["User"]:
        from app.data_access.repositories.user_repository import UserRepository
        return UserRepository.get_by_id(user_id)

    @staticmethod
    def get_by_login(login: str) -> Optional["User"]:
        from app.data_access.repositories.user_repository import UserRepository
        return UserRepository.get_by_login(login)

    @property
    def memory(self) -> dict[str, Any]:
        return json.loads(self._memory)

    @memory.setter
    def memory(self, value: dict[str, Any]) -> None:
        if value is None:
            value = {}
        self._memory = json.dumps(value, ensure_ascii=False)

    def get_memory(self) -> dict[str, Any]:
        return self.memory

    def set_memory(self, memory: dict[str, Any]) -> None:
        self.memory = memory
        self.save()

    def add_file(
            self,
            filename: str,
            mime_type: str,
            data: bytes,
            aux_file_id: str | None = None,
    ):
        from app.data_access.repositories.stored_file_repository import StoredFileRepository
        return StoredFileRepository.create(
            user_id=self.id,
            filename=filename,
            mime_type=mime_type,
            data=data,
            aux_file_id=aux_file_id,
        )

    def add_files(
            self,
            files: list[dict],
    ):
        from app.data_access.repositories.stored_file_repository import StoredFileRepository
        return StoredFileRepository.create_many(
            user_id=self.id,
            files=files,
        )

    def get_files(self):
        from app.data_access.repositories.stored_file_repository import StoredFileRepository
        return StoredFileRepository.get(user_id=self.id)

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, login={self.login!r}, is_active={self.is_active!r})"