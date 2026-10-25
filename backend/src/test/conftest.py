from pathlib import Path
from dotenv import dotenv_values
import pytest

from app.data_access.db import _DatabaseManager, DataAccess, Base


@pytest.fixture
def fresh_database(tmp_path):
    db_file = tmp_path / 'test.db'
    if _DatabaseManager._engine is not None:
        _DatabaseManager._engine.dispose()
    _DatabaseManager._engine = None
    _DatabaseManager._session_factory = None
    _DatabaseManager._configured = False
    _DatabaseManager._db_path = None
    DataAccess.configure(str(db_file))
    try:
        yield str(db_file)
    finally:
        if _DatabaseManager._engine is not None:
            Base.metadata.drop_all(_DatabaseManager._engine)
            _DatabaseManager._engine.dispose()
        _DatabaseManager._engine = None
        _DatabaseManager._session_factory = None
        _DatabaseManager._configured = False
        _DatabaseManager._db_path = None


@pytest.fixture
def api_client(fresh_database, monkeypatch):
    from fastapi.testclient import TestClient

    backend = Path(__file__).resolve().parents[2]
    for name, value in dotenv_values(backend / '.env.example').items():
        if value is not None:
            monkeypatch.setenv(name, value)
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key-not-for-network-use')
    monkeypatch.setenv('DATABASE_PATH', fresh_database)
    from app.main import app

    with TestClient(app) as client:
        yield client
