from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data_access.db import Base
from app.data_access.utils import utc_now

if TYPE_CHECKING:
    from app.data_access.models.user import User


class UserSession(Base):
    __tablename__ = "user_sessions"

    token: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship(back_populates="sessions")

    def is_expired(self) -> bool:
        return utc_now() >= self.expires_at

    def delete(self) -> None:
        from app.data_access.repositories.user_session_repository import UserSessionRepository
        UserSessionRepository.delete(self.token)

    @staticmethod
    def get_by_token(token: str) -> Optional["UserSession"]:
        from app.data_access.repositories.user_session_repository import UserSessionRepository
        return UserSessionRepository.get_by_token(token)

    def __repr__(self) -> str:
        return f"UserSession(token=<redacted>, user_id={self.user_id!r})"
