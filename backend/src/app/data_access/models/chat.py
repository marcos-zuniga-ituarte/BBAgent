import base64
import json
from datetime import datetime
from typing import Optional, TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data_access.db import Base
from app.data_access.models.message import Message
from app.data_access.utils import utc_now

if TYPE_CHECKING:
    from app.data_access.models.user import User


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    _memory: Mapped[str] = mapped_column("memory", Text, nullable=False, default="{}")
    last_interaction_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    user: Mapped["User"] = relationship(back_populates="chats")

    messages: Mapped[list[Message]] = relationship(
        back_populates="chat",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    def change_title(self, new_title: str) -> None:
        cleaned = new_title.strip()
        if not cleaned:
            raise ValueError("Chat title cannot be empty.")

        self.title = cleaned
        self.updated_at = utc_now()
        self.save()

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
        self.updated_at = utc_now()
        self.save()

    def add_message(self, message: dict[str, Any], show: bool = False) -> Message:
        from app.data_access.repositories.chat_repository import ChatRepository

        return ChatRepository.add_message(self.id, message, show=show)

    def add_messages(self, messages: list[dict[str, Any]], show: bool = False) -> list[
        Message]:
        from app.data_access.repositories.chat_repository import ChatRepository

        return ChatRepository.add_messages(self.id, messages, show=show)

    def get_messages(self) -> list[Message]:
        from app.data_access.repositories.chat_repository import ChatRepository
        return ChatRepository.get_messages(self.id)

    def _normalize_content_for_ui(self, content) -> dict:
        result = {
            "text": "",
        }

        if content is None:
            return result

        if isinstance(content, str):
            result["text"] = content
            return result

        if isinstance(content, list):
            text_parts = []

            for item in content:
                if isinstance(item, str):
                    if item.strip():
                        text_parts.append(item)
                    continue

                if not isinstance(item, dict):
                    continue

                item_type = item.get("type")

                if item_type in {"input_text", "output_text", "text"}:
                    text_value = item.get("text", "")
                    if isinstance(text_value, str):
                        if text_value.strip():
                            text_parts.append(text_value)
                    elif text_value is not None:
                        text_parts.append(str(text_value))

            result["text"] = "\n".join(text_parts).strip()
            return result

        if isinstance(content, dict):
            if "text" in content:
                text_value = content.get("text", "")
                result["text"] = text_value if isinstance(text_value, str) else str(text_value or "")
                return result

            result["text"] = json.dumps(content, ensure_ascii=False)
            return result

        result["text"] = str(content)
        return result

    def get_messages_for_ui(self) -> list[dict]:
        result = []

        for m in self.get_messages():
            if not m.show:
                continue

            payload = dict(m.content)
            role = payload.get("role", "assistant")
            content = payload.get("content", "")

            normalized = self._normalize_content_for_ui(content)

            files = []
            for stored_file in m.get_files():
                if stored_file.mime_type.startswith("image/"):
                    base64_data = base64.b64encode(stored_file.data).decode("utf-8")
                    files.append({
                        "id": stored_file.id,
                        "type": "image",
                        "filename": stored_file.filename,
                        "image_url": f"data:{stored_file.mime_type};base64,{base64_data}",
                    })
                else:
                    files.append({
                        "id": stored_file.id,
                        "type": "file",
                        "filename": stored_file.filename,
                    })

            result.append({
                "id": m.id,
                "role": role,
                "content": {
                    "text": normalized["text"],
                    "files": files,
                },
            })

        return result

    def get_messages_dict(self) -> list[dict]:
        return [m.content for m in self.get_messages()]

    def get_messages_partitioned_for_openai(
            self,
            cutoff_message_id: str,
            runs_above_cutoff: int
    ) -> tuple[list[dict], list[dict]]:
        if runs_above_cutoff < 0:
            raise ValueError("runs_above_cutoff must be >= 0.")

        messages = self.get_messages()
        if not messages:
            return [], []

        # Buscar el cutoff en todos los mensajes reales del chat
        cutoff_index = None
        cutoff_payload = None

        for i, message in enumerate(messages):
            payload = dict(message.content)
            if message.id == cutoff_message_id:
                cutoff_index = i
                cutoff_payload = payload
                break

        if cutoff_index is None:
            raise ValueError(f"Cutoff message with id {cutoff_message_id} does not exist.")

        cutoff_role = cutoff_payload.get("role")
        if cutoff_role != "user" and cutoff_role != Message.Role.USER:
            raise ValueError("Cutoff message must be a user message.")

        # Parte reciente: desde el cutoff en adelante, sin filtros
        recent_messages = [
            dict(message.content)
            for message in messages[cutoff_index:]
        ]

        # Parte histórica: solo mensajes anteriores al cutoff
        historical_messages = messages[:cutoff_index]

        # De la parte histórica, solo nos quedamos con user/assistant
        historical_valid: list[dict[str, Any]] = []

        for message in historical_messages:
            payload = dict(message.content)
            role = payload.get("role")

            if role in {"user", "assistant", Message.Role.USER, Message.Role.ASSISTANT}:
                historical_valid.append(payload)

        # Construir runs históricos:
        # cada run = un user + todos los assistant siguientes hasta el próximo user
        runs: list[list[dict[str, Any]]] = []
        current_run: list[dict[str, Any]] | None = None

        for payload in historical_valid:
            role = payload.get("role")

            if role == "user" or role == Message.Role.USER:
                if current_run is not None:
                    runs.append(current_run)

                current_run = [payload]

            elif role == "assistant" or role == Message.Role.ASSISTANT:
                if current_run is None:
                    # Assistant suelto antes del primer user: se ignora
                    continue
                current_run.append(payload)

        if current_run is not None:
            runs.append(current_run)

        # Seleccionar hasta N runs anteriores completos
        selected_historical_runs = runs[-runs_above_cutoff:] if runs_above_cutoff > 0 else []

        # Este segundo valor es el run más antiguo de la ventana seleccionada,
        # pero solo si la ventana está completa.
        run_to_summarize_next = []
        if (
                runs_above_cutoff > 0
                and len(runs) >= runs_above_cutoff
                and selected_historical_runs
        ):
            run_to_summarize_next = selected_historical_runs[0]

        result: list[dict] = []

        for run in selected_historical_runs:
            result.extend(run)

        # Añadimos la parte reciente cruda (incluyendo el cutoff)
        result.extend(recent_messages)

        return result, run_to_summarize_next

    def get_last_message(self) -> Optional[Message]:
        from app.data_access.repositories.chat_repository import ChatRepository
        return ChatRepository.get_last_message(self.id)

    def delete(self) -> None:
        from app.data_access.repositories.chat_repository import ChatRepository
        ChatRepository.delete(self.id)

    def save(self) -> None:
        from app.data_access.repositories.chat_repository import ChatRepository
        ChatRepository.save(self)

    @staticmethod
    def get_by_id(chat_id: str) -> Optional["Chat"]:
        from app.data_access.repositories.chat_repository import ChatRepository
        return ChatRepository.get_by_id(chat_id)

    def add_file(
            self,
            filename: str,
            mime_type: str,
            data: bytes,
            aux_file_id: str | None = None,
    ):
        from app.data_access.repositories.stored_file_repository import StoredFileRepository
        return StoredFileRepository.create(
            user_id=self.user_id,
            chat_id=self.id,
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
            user_id=self.user_id,
            chat_id=self.id,
            files=files,
        )

    def get_files(self):
        from app.data_access.repositories.stored_file_repository import StoredFileRepository
        return StoredFileRepository.get(chat_id=self.id)

    def __repr__(self) -> str:
        return f"Chat(id={self.id!r}, title={self.title!r}, user_id={self.user_id!r})"
