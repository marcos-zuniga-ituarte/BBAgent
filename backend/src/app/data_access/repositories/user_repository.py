from typing import Optional

from sqlalchemy import select

from app.data_access.db import _DatabaseManager
from app.data_access.models.chat import Chat
from app.data_access.models.user import User


class UserRepository:
    @staticmethod
    def get_by_id(user_id: str) -> Optional[User]:
        with _DatabaseManager.session() as session:
            return session.get(User, user_id)

    @staticmethod
    def get_by_login(login: str) -> Optional[User]:
        cleaned_login = login.strip()
        with _DatabaseManager.session() as session:
            stmt = select(User).filter_by(login=cleaned_login)
            return session.scalars(stmt).first()

    @staticmethod
    def create_chat(user_id: str, title: str = None) -> Chat:
        if title is None or not title.strip():
            cleaned = "New chat"
        else:
            cleaned = title.strip()

        chat = Chat(
            user_id=user_id,
            title=cleaned,
        )

        with _DatabaseManager.session() as session:
            session.add(chat)
            session.commit()
            session.refresh(chat)

        return chat

    @staticmethod
    def get_chats(user_id: str) -> list[Chat]:
        with _DatabaseManager.session() as session:
            stmt = (
                select(Chat)
                .filter_by(user_id=user_id)
                .order_by(Chat.last_interaction_at.desc())
            )
            return list(session.scalars(stmt).all())

    @staticmethod
    def get_chat(user_id: str, chat_id: str) -> Optional[Chat]:
        with _DatabaseManager.session() as session:
            stmt = select(Chat).filter_by(id=chat_id, user_id=user_id)
            return session.scalars(stmt).first()

    @staticmethod
    def save(user: User) -> None:
        with _DatabaseManager.session() as session:
            db_user = session.get(User, user.id)
            if db_user is None:
                raise ValueError(f"User with id {user.id} does not exist.")

            db_user.password_hash = user.password_hash
            db_user.system_prompt = user.system_prompt
            db_user.is_active = user.is_active
            db_user._memory = user._memory
            session.commit()