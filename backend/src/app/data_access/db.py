import os

from sqlalchemy import (
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    sessionmaker,
)


class Base(DeclarativeBase):
    pass


class _DatabaseManager:
    _engine = None
    _session_factory = None
    _configured = False
    _db_path = None

    @classmethod
    def configure(cls, db_path: str) -> None:
        directory = os.path.dirname(db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        cls._engine = create_engine(f"sqlite:///{db_path}", echo=False)
        cls._session_factory = sessionmaker(bind=cls._engine, expire_on_commit=False)
        Base.metadata.create_all(cls._engine)
        cls._configured = True
        cls._db_path = db_path

    @classmethod
    def ensure_configured(cls) -> None:
        if not cls._configured:
            raise RuntimeError(
                "Database not configured. Call DataAccess.configure(path) first."
            )

    @classmethod
    def session(cls):
        cls.ensure_configured()
        return cls._session_factory()


class DataAccess:
    @classmethod
    def configure(cls, db_path: str = "chat.db") -> None:
        _DatabaseManager.configure(db_path)