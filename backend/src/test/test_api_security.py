from io import BytesIO
from zipfile import ZipFile
from urllib.parse import quote

from app.data_access import AuthService
from app.data_access.repositories.stored_file_repository import StoredFileRepository
from app.services.command_approval_manager import approval_manager


def login(client, name):
    user = AuthService.register_user(name, "test-only-passphrase")
    result = client.post("/auth/login", json={"login": name, "password": "test-only-passphrase"})
    assert result.status_code == 200
    return user, {"Authorization": "Bearer " + result.json()["access_token"]}


def test_authentication_logout_and_private_routes(api_client):
    assert api_client.get("/chat").status_code == 401
    assert api_client.get("/tool-client/download").status_code == 401
    _, headers = login(api_client, "demo-owner")
    assert api_client.get("/chat", headers=headers).status_code == 200
    assert api_client.post("/auth/logout", headers=headers).status_code == 200
    assert api_client.get("/chat", headers=headers).status_code == 401


def test_users_cannot_read_chats_or_approve_another_users_tools(api_client):
    owner, owner_headers = login(api_client, "owner")
    _, outsider_headers = login(api_client, "outsider")
    chat = owner.create_chat("Private demo")
    assert api_client.get(f"/chat/{chat.id}/messages", headers=outsider_headers).status_code == 404
    approval_manager.create_session(chat.id)
    try:
        decision = api_client.post(f"/tool-approval/sessions/{chat.id}/response", json={"decision": True}, headers=outsider_headers)
        assert decision.status_code == 404
        assert approval_manager.wait_for_decision(chat.id, timeout_seconds=0) is None
        own_decision = api_client.post(f"/tool-approval/sessions/{chat.id}/response", json={"decision": True}, headers=owner_headers)
        assert own_decision.status_code == 200
        assert approval_manager.wait_for_decision(chat.id, timeout_seconds=0) is True
    finally:
        approval_manager.remove_session(chat.id)


def test_files_are_private_and_filenames_are_encoded(api_client):
    owner, owner_headers = login(api_client, "owner")
    _, outsider_headers = login(api_client, "outsider")
    filename = 'informe á\r\nX-Injected: 1.txt'
    file = StoredFileRepository.create(owner.id, filename, "text/plain", b"demo")
    assert api_client.get(f"/files/{file.id}", headers=outsider_headers).status_code == 404
    response = api_client.get(f"/files/{file.id}", headers=owner_headers)
    assert response.status_code == 200
    assert response.content == b"demo"
    assert response.headers["Content-Disposition"] == "attachment; filename*=UTF-8''" + quote(filename, safe="")
    assert "X-Injected" not in response.headers


def test_cors_accepts_local_web_but_not_unknown_origins(api_client):
    local = api_client.options("/chat", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
    assert local.status_code == 200
    assert local.headers["access-control-allow-origin"] == "http://localhost:5173"
    remote = api_client.options("/chat", headers={"Origin": "https://untrusted.example", "Access-Control-Request-Method": "GET"})
    assert remote.status_code == 400
    assert "access-control-allow-origin" not in remote.headers


def test_client_download_excludes_local_secrets_and_caches(api_client, tmp_path, monkeypatch):
    import app.controller.tool_client_router as router

    clients = tmp_path / "clients"
    clients.mkdir()
    (clients / "client.py").write_text("pass\n", encoding="utf-8")
    (clients / "requirements.txt").write_text("-r requirements-terminal.txt\nPillow\nPyAutoGUI\n", encoding="utf-8")
    (clients / "requirements-terminal.txt").write_text("requests==2.33.1\n", encoding="utf-8")
    (clients / "README.md").write_text("# Client setup\n", encoding="utf-8")
    (clients / "requirements-private.txt").write_text("private local configuration", encoding="utf-8")
    (clients / "credentials.json").write_text('{"password": "test-only-example"}', encoding="utf-8")
    (clients / ".env").write_text("LOCAL_PASSWORD=test-only-example", encoding="utf-8")
    cache = clients / "__pycache__"
    cache.mkdir()
    (cache / "private.py").write_text("pass\n", encoding="utf-8")
    environment = clients / "venv"
    environment.mkdir()
    (environment / "private.py").write_text("pass\n", encoding="utf-8")
    monkeypatch.setattr(router, "_get_clients_dir", lambda: clients)
    _, headers = login(api_client, "owner")
    response = api_client.get("/tool-client/download", headers=headers)
    assert response.status_code == 200
    with ZipFile(BytesIO(response.content)) as archive:
        assert set(archive.namelist()) == {
            "clients/client.py", "clients/README.md",
            "clients/requirements.txt", "clients/requirements-terminal.txt",
        }
        assert archive.read("clients/requirements.txt").decode("utf-8").startswith("-r requirements-terminal.txt")
