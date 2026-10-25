from datetime import timedelta

from app.data_access import UserSession
from app.data_access.auth_service import AuthService
from app.data_access.repositories.user_session_repository import UserSessionRepository
from app.data_access.utils import utc_now


def test_authenticate_returns_session_for_valid_credentials(fresh_database):
    AuthService.register_user("marcos", "1234")

    session = AuthService.authenticate("marcos", "1234")

    assert session.token is not None
    assert session.user_id is not None
    assert session.expires_at > session.created_at


def test_authenticate_rejects_invalid_password(fresh_database):
    AuthService.register_user("marcos", "1234")

    try:
        AuthService.authenticate("marcos", "xxxx")
        assert False, "Expected ValueError for invalid credentials"
    except ValueError as exc:
        assert str(exc) == "Invalid credentials."


def test_get_user_by_token_returns_user(fresh_database):
    user = AuthService.register_user("marcos", "1234")
    session = AuthService.create_session(user)

    db_user = AuthService.get_user_by_token(session.token)

    assert db_user is not None
    assert db_user.id == user.id
    assert db_user.login == "marcos"


def test_get_user_by_token_returns_none_for_expired_session(fresh_database):
    user = AuthService.register_user("marcos", "1234")
    session = AuthService.create_session(user)

    session.expires_at = utc_now() - timedelta(hours=1)

    # según la estructura que montaste, lo normal sería guardar así
    UserSessionRepository.save(session)

    db_user = AuthService.get_user_by_token(session.token)

    assert db_user is None
    assert UserSession.get_by_token(session.token) is None


def test_revoke_session_deletes_session(fresh_database):
    user = AuthService.register_user("marcos", "1234")
    session = AuthService.create_session(user)

    AuthService.revoke_session(session.token)

    assert UserSession.get_by_token(session.token) is None


def test_revoke_user_sessions_deletes_all_user_sessions(fresh_database):
    user = AuthService.register_user("marcos", "1234")
    s1 = AuthService.create_session(user)
    s2 = AuthService.create_session(user)

    AuthService.revoke_user_sessions(user.id)

    assert UserSession.get_by_token(s1.token) is None
    assert UserSession.get_by_token(s2.token) is None