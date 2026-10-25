import importlib.util
from pathlib import Path
import sys

import pytest

source = Path(__file__).resolve().parents[2] / "clients/libraries/client_config.py"
spec = importlib.util.spec_from_file_location("client_config", source)
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)


def test_local_client_default(monkeypatch):
    monkeypatch.delenv("BBAGENT_API_URL", raising=False)
    monkeypatch.setattr(sys, "argv", ["client.py"])
    assert config.get_backend_url() == "http://localhost:8000"


def test_cli_url_overrides_environment(monkeypatch):
    monkeypatch.setenv("BBAGENT_API_URL", "https://old.example.com")
    monkeypatch.setattr(sys, "argv", ["client.py", "--url", "https://api.example.com/"])
    assert config.get_backend_url() == "https://api.example.com"


@pytest.mark.parametrize("value", ["javascript:alert(1)", "https://user:password@example.com", "https://example.com?token=example"])
def test_client_rejects_invalid_urls_without_showing_credentials(monkeypatch, capsys, value):
    monkeypatch.setattr(sys, "argv", ["client.py", "--url", value])
    with pytest.raises(SystemExit):
        config.get_backend_url()
    assert value not in capsys.readouterr().err
