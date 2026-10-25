import json
from typing import Any

from sqlalchemy import select

from app.data_access.db import _DatabaseManager
from app.data_access.models.message import Message
from app.data_access.utils import utc_now


class MessageRepository:

    @staticmethod
    def create(chat_id: str, content: dict[str, Any], show: bool = False) -> Message:
        if not content:
            raise ValueError("Message content cannot be empty.")

        message = Message(
            chat_id=chat_id,
            show=show,
            created_at=utc_now(),
        )
        message.content = content

        with _DatabaseManager.session() as session:
            session.add(message)
            session.commit()
            session.refresh(message)

        return message

    @staticmethod
    def get_by_id(message_id: str) -> Message | None:
        with _DatabaseManager.session() as session:
            return session.get(Message, message_id)

    @staticmethod
    def get_by_chat(chat_id: str) -> list[Message]:
        with _DatabaseManager.session() as session:
            stmt = (
                select(Message)
                .filter_by(chat_id=chat_id)
                .order_by(Message.created_at.asc())
            )
            return list(session.scalars(stmt).all())

    @staticmethod
    def delete(message_id: str) -> None:
        with _DatabaseManager.session() as session:
            message = session.get(Message, message_id)
            if message:
                session.delete(message)
                session.commit()