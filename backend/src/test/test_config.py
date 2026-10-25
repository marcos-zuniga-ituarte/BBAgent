import pytest

from app.config import get_cors_origins


def test_local_cors_defaults(monkeypatch):
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    assert "http://localhost:5173" in get_cors_origins()


@pytest.mark.parametrize("value", ["*", "https://example.com/path", "https://user:password@example.com", "javascript:alert(1)"])
def test_invalid_cors_origins_are_rejected(monkeypatch, value):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", value)
    with pytest.raises(ValueError):
        get_cors_origins()
