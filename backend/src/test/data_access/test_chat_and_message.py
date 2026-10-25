from app.data_access import Message
from app.data_access.models.chat import Chat
from app.data_access.auth_service import AuthService


def test_chat_add_message_persists_message(fresh_database):
    user = AuthService.register_user("marcos", "1234")
    chat = user.create_chat("Mi chat")

    message = chat.add_message({"role": Message.Role.USER.value, "content": "Hola mundo"}, show=True)

    assert message.id is not None
    assert message.chat_id == chat.id
    assert message.content["role"] == Message.Role.USER.value
    assert message.show is True
    assert message.content["content"] == "Hola mundo"


def test_chat_get_messages_returns_messages_in_order(fresh_database):
    user = AuthService.register_user("marcos", "1234")
    chat = user.create_chat("Mi chat")

    m1 = chat.add_message({"role": Message.Role.USER.value, "content": "Primero"}, show=True)
    m2 = chat.add_message({"role": Message.Role.ASSISTANT.value, "content": "Segundo"}, show=True)

    messages = chat.get_messages()

    assert len(messages) == 2
    assert messages[0].id == m1.id
    assert messages[1].id == m2.id
    assert messages[0].content["content"] == "Primero"
    assert messages[1].content["content"] == "Segundo"


def test_chat_get_last_message_returns_latest_one(fresh_database):
    user = AuthService.register_user("marcos", "1234")
    chat = user.create_chat("Mi chat")

    chat.add_message({"role": Message.Role.USER.value, "content": "Uno"}, show=True)
    last = chat.add_message({"role": Message.Role.ASSISTANT.value, "content": "Dos"}, show=True)

    db_last = chat.get_last_message()

    assert db_last is not None
    assert db_last.id == last.id
    assert db_last.content["content"] == "Dos"


def test_chat_change_title_updates_database(fresh_database):
    user = AuthService.register_user("marcos", "1234")
    chat = user.create_chat("Viejo título")

    chat.change_title("Nuevo título")

    db_chat = Chat.get_by_id(chat.id)
    assert db_chat is not None
    assert db_chat.title == "Nuevo título"


def test_chat_delete_removes_chat(fresh_database):
    user = AuthService.register_user("marcos", "1234")
    chat = user.create_chat("Mi chat")

    chat.delete()

    db_chat = Chat.get_by_id(chat.id)
    assert db_chat is None
    assert user.get_chats() == []


def test_add_message_rejects_empty_content(fresh_database):
    user = AuthService.register_user("marcos", "1234")
    chat = user.create_chat("Mi chat")

    try:
        chat.add_message({})
        assert False, "Expected ValueError for empty message"
    except ValueError as exc:
        assert str(exc) == "Message content cannot be empty."