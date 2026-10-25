from typing import Optional, Any

from sqlalchemy import select

from app.data_access.db import _DatabaseManager
from app.data_access.models.chat import Chat
from app.data_access.models.message import Message
from app.data_access.utils import utc_now


class ChatRepository:
    @staticmethod
    def get_by_id(chat_id: str) -> Optional[Chat]:
        with _DatabaseManager.session() as session:
            return session.get(Chat, chat_id)

    @staticmethod
    def add_message(chat_id: str, content: dict[str, Any], show: bool = False) -> Message:
        if not content:
            raise ValueError("Message content cannot be empty.")

        now = utc_now()

        with _DatabaseManager.session() as session:
            db_chat = session.get(Chat, chat_id)
            if db_chat is None:
                raise ValueError(f"Chat with id {chat_id} does not exist.")

            message = Message(
                chat_id=chat_id,
                show=show,
                created_at=now,
            )
            message.content = content

            db_chat.updated_at = now
            db_chat.last_interaction_at = now

            session.add(message)
            session.commit()
            session.refresh(message)

            return message

    @staticmethod
    def add_messages(chat_id: str, contents: list[dict[str, Any]], show: bool = False) -> list[Message]:
        if not contents:
            return []

        if not all(isinstance(content, dict) and content for content in contents):
            raise ValueError("All messages must be non-empty dicts.")

        now = utc_now()
        created_messages: list[Message] = []

        with _DatabaseManager.session() as session:
            db_chat = session.get(Chat, chat_id)
            if db_chat is None:
                raise ValueError(f"Chat with id {chat_id} does not exist.")

            for content in contents:
                message = Message(
                    chat_id=chat_id,
                    show=show,
                    created_at=now,
                )
                message.content = content
                session.add(message)
                created_messages.append(message)

            db_chat.updated_at = now
            db_chat.last_interaction_at = now

            session.commit()

            for message in created_messages:
                session.refresh(message)

            return created_messages

    @staticmethod
    def get_messages(chat_id: str) -> list[Message]:
        with _DatabaseManager.session() as session:
            stmt = (
                select(Message)
                .filter_by(chat_id=chat_id)
                .order_by(Message.created_at.asc())
            )
            return list(session.scalars(stmt).all())

    @staticmethod
    def get_last_message(chat_id: str) -> Optional[Message]:
        with _DatabaseManager.session() as session:
            stmt = (
                select(Message)
                .filter_by(chat_id=chat_id)
                .order_by(Message.created_at.desc())
            )
            return session.scalars(stmt).first()

    @staticmethod
    def delete(chat_id: str) -> None:
        with _DatabaseManager.session() as session:
            db_chat = session.get(Chat, chat_id)
            if db_chat is not None:
                session.delete(db_chat)
                session.commit()

    @staticmethod
    def save(chat: Chat) -> None:
        with _DatabaseManager.session() as session:
            db_chat = session.get(Chat, chat.id)
            if db_chat is None:
                raise ValueError(f"Chat with id {chat.id} does not exist.")

            db_chat.title = chat.title
            db_chat._memory = chat._memory
            db_chat.updated_at = chat.updated_at
            db_chat.last_interaction_at = chat.last_interaction_at
            session.commit()