from app.data_access import AuthService
from app.data_access.models.user import User


def test_register_user_persists_in_database(fresh_database):
    user = AuthService.register_user("marcos", "1234")

    assert user.id is not None
    assert user.login == "marcos"
    assert user.is_active is True

    db_user = User.get_by_id(user.id)
    assert db_user is not None
    assert db_user.login == "marcos"


def test_register_user_rejects_duplicate_login(fresh_database):
    AuthService.register_user("marcos", "1234")

    try:
        AuthService.register_user("marcos", "5678")
        assert False, "Expected ValueError for duplicate login"
    except ValueError as exc:
        assert str(exc) == "Login already exists."


def test_user_create_chat_persists_chat(fresh_database):
    user = AuthService.register_user("marcos", "1234")

    chat = user.create_chat("Mi chat")

    assert chat.id is not None
    assert chat.user_id == user.id
    assert chat.title == "Mi chat"

    chats = user.get_chats()
    assert len(chats) == 1
    assert chats[0].id == chat.id
    assert chats[0].title == "Mi chat"


def test_user_create_chat_uses_default_title_when_empty(fresh_database):
    user = AuthService.register_user("marcos", "1234")

    chat = user.create_chat("   ")

    assert chat.title == "New chat"


def test_user_get_chat_returns_only_own_chat(fresh_database):
    user1 = AuthService.register_user("marcos", "1234")
    user2 = AuthService.register_user("lucia", "abcd")

    chat1 = user1.create_chat("Chat de Marcos")

    assert user1.get_chat(chat1.id) is not None
    assert user2.get_chat(chat1.id) is None


def test_user_save_updates_fields(fresh_database):
    user = AuthService.register_user("marcos", "1234")

    user.set_system_prompt("   hola sistema   ")
    user.deactivate()

    db_user = User.get_by_id(user.id)
    assert db_user is not None
    assert db_user.system_prompt == "hola sistema"
    assert db_user.is_active is False

    user.activate()
    db_user = User.get_by_id(user.id)
    assert db_user.is_active is True