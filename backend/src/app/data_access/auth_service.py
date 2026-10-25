from datetime import timedelta
from typing import Optional
import secrets

from app.data_access.models.user import User
from app.data_access.models.user_session import UserSession
from app.data_access.repositories.user_repository import UserRepository
from app.data_access.repositories.user_session_repository import UserSessionRepository
from app.data_access.db import _DatabaseManager
from app.data_access.utils import utc_now, hash_password, verify_password


class AuthService:

    @staticmethod
    def generate_token() -> str:
        return secrets.token_urlsafe(32)

    @classmethod
    def register_user(cls, login: str, password: str) -> User:
        cleaned_login = login.strip()
        cleaned_password = password

        if not cleaned_login:
            raise ValueError("Login cannot be empty.")

        if not cleaned_password:
            raise ValueError("Password cannot be empty.")

        existing_user = UserRepository.get_by_login(cleaned_login)
        if existing_user is not None:
            raise ValueError("Login already exists.")

        user = User(
            login=cleaned_login,
            password_hash=hash_password(cleaned_password),
            system_prompt=None,
            is_active=True,
        )

        with _DatabaseManager.session() as session:
            session.add(user)
            session.commit()
            session.refresh(user)

        return user

    @classmethod
    def change_password_by_user(cls, user: User, new_password: str) -> None:
        if not new_password:
            raise ValueError("New password cannot be empty.")

        # evitar mismo password
        if verify_password(new_password, user.password_hash):
            raise ValueError("New password must be different.")

        user.set_password_hash(hash_password(new_password))

        # invalidar sesiones
        cls.revoke_user_sessions(user.id)

    @classmethod
    def create_session(cls, user: User, duration_hours: int = 24) -> UserSession:
        if not user.is_active:
            raise ValueError("User is inactive.")

        now = utc_now()
        session_obj = UserSession(
            token=cls.generate_token(),
            user_id=user.id,
            created_at=now,
            expires_at=now + timedelta(hours=duration_hours),
        )

        with _DatabaseManager.session() as session:
            session.add(session_obj)
            session.commit()
            session.refresh(session_obj)

        return session_obj

    @classmethod
    def authenticate(cls, login: str, password: str) -> UserSession:
        cleaned_login = login.strip()
        if not cleaned_login:
            raise ValueError("Login cannot be empty.")

        user = UserRepository.get_by_login(cleaned_login)

        if user is None:
            raise ValueError("Invalid credentials.")

        if not user.is_active:
            raise ValueError("User is inactive.")

        if not verify_password(password, user.password_hash):
            raise ValueError("Invalid credentials.")

        return cls.create_session(user, 24)

    @classmethod
    def get_user_by_token(cls, token: str) -> Optional[User]:
        user_session = UserSessionRepository.get_by_token(token)

        if user_session is None:
            return None

        if user_session.is_expired():
            UserSessionRepository.delete(token)
            return None

        return User.get_by_id(user_session.user_id)

    @classmethod
    def revoke_session(cls, token: str) -> None:
        UserSessionRepository.delete(token)

    @classmethod
    def revoke_user_sessions(cls, user_id: str) -> None:
        UserSessionRepository.revoke_user_sessions(user_id)