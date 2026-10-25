from typing import Optional

from sqlalchemy import select

from app.data_access.db import _DatabaseManager
from app.data_access.models.user_session import UserSession


class UserSessionRepository:
    @staticmethod
    def get_by_token(token: str) -> Optional[UserSession]:
        with _DatabaseManager.session() as session:
            stmt = select(UserSession).filter_by(token=token)
            return session.scalars(stmt).first()

    @staticmethod
    def delete(token: str) -> None:
        with _DatabaseManager.session() as session:
            db_session = session.get(UserSession, token)
            if db_session is not None:
                session.delete(db_session)
                session.commit()

    @staticmethod
    def revoke_user_sessions(user_id: str) -> None:
        with _DatabaseManager.session() as session:
            sessions = list(
                session.scalars(
                    select(UserSession).filter_by(user_id=user_id)
                ).all()
            )

            for db_session in sessions:
                session.delete(db_session)

            session.commit()

    @staticmethod
    def save(user_session: UserSession) -> None:
        with _DatabaseManager.session() as session:
            db_user_session = session.get(UserSession, user_session.token)
            if db_user_session is None:
                raise ValueError(f"Session with token {user_session.token} does not exist.")

            db_user_session.expires_at = user_session.expires_at
            session.commit()