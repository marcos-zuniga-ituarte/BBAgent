import json
import queue as queue_module
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from app.data_access import User


class NoTerminalClient(Exception):
    pass


class PendingCommandError(Exception):
    pass


class SessionNotFoundError(Exception):
    pass


def sse_event(data: str, event: str | None = None) -> str:
    parts = []
    if event:
        parts.append(f"event: {event}")
    parts.append(f"data: {data}")
    return "\n".join(parts) + "\n\n"


@dataclass
class PendingResult:
    done: threading.Event = field(default_factory=threading.Event)
    value: Optional[str] = None
    error: Optional[BaseException] = None


@dataclass
class ClientConnection:
    event_queue: queue_module.Queue = field(default_factory=queue_module.Queue)
    last_pong: float = field(default_factory=time.time)
    closed: bool = False


@dataclass
class ServerSessionState:
    chat_id: str
    created_at: str
    pending_result: Optional[PendingResult] = None
    closed: bool = False


class TerminalSessionService:
    PING_INTERVAL_SECONDS = 10
    PONG_TIMEOUT_SECONDS = 60
    STREAM_KEEPALIVE_SECONDS = 15

    def __init__(self) -> None:
        self._clients: dict[str, ClientConnection] = {}
        self._sessions: dict[str, dict[str, ServerSessionState]] = {}
        self._lock = threading.RLock()
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self._heartbeat_thread is not None and self._heartbeat_thread.is_alive():
            return

        self._stop_event.clear()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            name="terminal-session-heartbeat",
            daemon=True,
        )
        self._heartbeat_thread.start()

    def shutdown(self) -> None:
        self._stop_event.set()

        if self._heartbeat_thread is not None:
            self._heartbeat_thread.join(timeout=2)
            self._heartbeat_thread = None

        with self._lock:
            user_ids = list(set(self._clients.keys()) | set(self._sessions.keys()))

        for user_id in user_ids:
            self._close_user_state(user_id, reason="Service shutdown")

    def open_stream(self, user_id: str) -> ClientConnection:
        with self._lock:
            new_conn = ClientConnection()
            old_conn = self._clients.get(user_id)

            if old_conn is not None:
                try:
                    old_conn.event_queue.put(("disconnect", "replaced"))
                except Exception:
                    pass
                self._close_client_connection_nolock(
                    user_id,
                    reason="replaced",
                    expected_conn=old_conn,
                )

            self._clients[user_id] = new_conn
            new_conn.last_pong = time.time()
            new_conn.event_queue.put(("connected", "ok"))

            # Ping inicial inmediato para que el cliente se sincronice pronto
            initial_payload = json.dumps(
                {"sessions": self._build_server_sessions_payload_nolock(user_id)},
                ensure_ascii=False,
            )
            new_conn.event_queue.put(("ping", initial_payload))

            return new_conn

    def close_stream(self, user_id: str, conn: Optional[ClientConnection] = None) -> None:
        with self._lock:
            self._close_client_connection_nolock(
                user_id=user_id,
                reason="Stream cerrado",
                expected_conn=conn,
            )

    def register_pong(self, user_id: str, client_sessions: list[dict]) -> None:
        with self._lock:
            conn = self._clients.get(user_id)
            if conn is not None and not conn.closed:
                conn.last_pong = time.time()

            client_keys: set[tuple[str, str]] = set()
            for item in client_sessions:
                if not isinstance(item, dict):
                    continue

                chat_id = item.get("chat_id")
                created_at = item.get("created_at")

                if isinstance(chat_id, str) and isinstance(created_at, str):
                    client_keys.add((chat_id, created_at))

            user_sessions = self._sessions.get(user_id, {})
            sessions_to_close: list[tuple[str, str]] = []

            # Si el cliente ya no tiene una sesión que el servidor creía viva,
            # la cerramos en servidor para no dejar pending colgados.
            for state in user_sessions.values():
                if state.closed:
                    continue

                key = (state.chat_id, state.created_at)
                if key not in client_keys:
                    sessions_to_close.append(key)

            for chat_id, created_at in sessions_to_close:
                self._close_session_nolock(
                    user_id=user_id,
                    chat_id=chat_id,
                    created_at=created_at,
                    reason="La sesión ya no existe en el cliente",
                    send_close_event=False,
                )

            if user_id in self._sessions and not self._sessions[user_id]:
                self._sessions.pop(user_id, None)

    def create_session(self, user: User, chat_id: str, created_at: str) -> None:
        with self._lock:
            conn = self._clients.get(user.id)
            if conn is None or conn.closed:
                raise NoTerminalClient("No hay stream activo para este usuario")

            user_sessions = self._sessions.setdefault(user.id, {})
            current = user_sessions.get(chat_id)

            if current is not None:
                if current.created_at == created_at and not current.closed:
                    return
                self._close_session_nolock(
                    user_id=user.id,
                    chat_id=chat_id,
                    created_at=current.created_at,
                    reason="Session reemplazada por create",
                    send_close_event=True,
                )

            state = ServerSessionState(chat_id=chat_id, created_at=created_at)
            user_sessions[chat_id] = state

            payload = json.dumps(
                {
                    "chat_id": chat_id,
                    "created_at": created_at,
                },
                ensure_ascii=False,
            )
            conn.event_queue.put(("create", payload))

    def close_session(self, user: User, chat_id: str, created_at: str) -> bool:
        with self._lock:
            return self._close_session_nolock(
                user_id=user.id,
                chat_id=chat_id,
                created_at=created_at,
                reason="Session cerrada por servidor",
                send_close_event=True,
            )

    def submit_result(self, user_id: str, chat_id: str, created_at: str, result: str) -> bool:
        with self._lock:
            session = self._get_session_nolock(user_id, chat_id, created_at)
            if session is None or session.pending_result is None:
                return False

            pending = session.pending_result
            session.pending_result = None

            pending.value = result
            pending.done.set()
            return True

    def send_command(
        self,
        user: User,
        chat_id: str,
        created_at: str,
        command_data: dict,
        timeout_seconds: Optional[float] = None,
    ) -> str:
        with self._lock:
            conn = self._clients.get(user.id)
            if conn is None or conn.closed:
                raise NoTerminalClient("No hay stream activo para este usuario")

            session = self._get_session_nolock(user.id, chat_id, created_at)

            if session is None:
                user_sessions = self._sessions.setdefault(user.id, {})
                current = user_sessions.get(chat_id)

                if current is not None:
                    self._close_session_nolock(
                        user_id=user.id,
                        chat_id=chat_id,
                        created_at=current.created_at,
                        reason="Session reemplazada por auto-create en send_command",
                        send_close_event=True,
                    )

                session = ServerSessionState(chat_id=chat_id, created_at=created_at)
                user_sessions[chat_id] = session

                create_payload = json.dumps(
                    {
                        "chat_id": chat_id,
                        "created_at": created_at,
                    },
                    ensure_ascii=False,
                )
                conn.event_queue.put(("create", create_payload))

            if session.pending_result is not None and not session.pending_result.done.is_set():
                raise PendingCommandError("Ya hay un comando pendiente para esta sesión")

            pending = PendingResult()
            session.pending_result = pending

            payload_data = {
                "chat_id": chat_id,
                "created_at": created_at,
                **command_data,
            }

            try:
                payload = json.dumps(payload_data, ensure_ascii=False)
                conn.event_queue.put(("command", payload))
            except Exception:
                session.pending_result = None
                raise

        completed = pending.done.wait(timeout=timeout_seconds)

        if not completed:
            with self._lock:
                current = self._get_session_nolock(user.id, chat_id, created_at)
                if current is session and session.pending_result is pending:
                    session.pending_result = None
            raise TimeoutError("Timeout esperando la respuesta del comando remoto")

        if pending.error is not None:
            raise pending.error

        return pending.value or ""

    def stream_generator(self, user_id: str):
        conn = self.open_stream(user_id)

        try:
            while not conn.closed:
                try:
                    event_name, payload = conn.event_queue.get(timeout=self.STREAM_KEEPALIVE_SECONDS)
                except queue_module.Empty:
                    payload = json.dumps(
                        {"sessions": self._build_server_sessions_payload(user_id)},
                        ensure_ascii=False,
                    )
                    yield sse_event(payload, event="ping")
                    continue

                if event_name == "_close":
                    break

                yield sse_event(payload, event=event_name)
        finally:
            # Muy importante: solo cerramos si este generator sigue siendo
            # el stream actual. Así un stream viejo no mata al nuevo.
            self.close_stream(user_id, conn=conn)

    def has_active_stream(self, user_id: str) -> bool:
        with self._lock:
            conn = self._clients.get(user_id)
            return conn is not None and not conn.closed

    def _heartbeat_loop(self) -> None:
        while not self._stop_event.wait(self.PING_INTERVAL_SECONDS):
            now = time.time()

            with self._lock:
                snapshot = list(self._clients.items())

            stale_users: list[tuple[str, ClientConnection]] = []

            for user_id, conn in snapshot:
                if conn.closed:
                    continue

                if (now - conn.last_pong) > self.PONG_TIMEOUT_SECONDS:
                    stale_users.append((user_id, conn))
                    continue

                try:
                    sessions_payload = self._build_server_sessions_payload(user_id)
                    payload = json.dumps(
                        {"sessions": sessions_payload},
                        ensure_ascii=False,
                    )
                    conn.event_queue.put(("ping", payload))
                except Exception:
                    stale_users.append((user_id, conn))

            for user_id, conn in stale_users:
                with self._lock:
                    self._close_client_connection_nolock(
                        user_id=user_id,
                        reason="Cliente desconectado por timeout de pong",
                        expected_conn=conn,
                    )

    def _build_server_sessions_payload(self, user_id: str) -> list[dict]:
        with self._lock:
            return self._build_server_sessions_payload_nolock(user_id)

    def _build_server_sessions_payload_nolock(self, user_id: str) -> list[dict]:
        user_sessions = self._sessions.get(user_id, {})
        return [
            {
                "chat_id": state.chat_id,
                "created_at": state.created_at,
            }
            for state in user_sessions.values()
            if not state.closed
        ]

    def _close_user_state(self, user_id: str, reason: str) -> None:
        with self._lock:
            self._close_client_connection_nolock(user_id, reason=reason)

            user_sessions = list(self._sessions.get(user_id, {}).values())
            for session in user_sessions:
                self._close_session_nolock(
                    user_id=user_id,
                    chat_id=session.chat_id,
                    created_at=session.created_at,
                    reason=reason,
                    send_close_event=False,
                )

            self._sessions.pop(user_id, None)

    def _close_client_connection_nolock(
        self,
        user_id: str,
        reason: str,
        expected_conn: Optional[ClientConnection] = None,
    ) -> None:
        conn = self._clients.get(user_id)
        if conn is None:
            return

        if expected_conn is not None and conn is not expected_conn:
            return

        conn.closed = True
        self._clients.pop(user_id, None)

        try:
            conn.event_queue.put(("_close", reason))
        except Exception:
            pass

    def _close_session_nolock(
        self,
        user_id: str,
        chat_id: str,
        created_at: str,
        reason: str,
        send_close_event: bool,
    ) -> bool:
        user_sessions = self._sessions.get(user_id, {})
        current = user_sessions.get(chat_id)

        if current is None:
            return False

        if current.created_at != created_at:
            return False

        current.closed = True
        user_sessions.pop(chat_id, None)

        if current.pending_result is not None and not current.pending_result.done.is_set():
            current.pending_result.error = RuntimeError(reason)
            current.pending_result.done.set()
            current.pending_result = None

        if send_close_event:
            conn = self._clients.get(user_id)
            if conn is not None and not conn.closed:
                payload = json.dumps(
                    {
                        "chat_id": chat_id,
                        "created_at": created_at,
                    },
                    ensure_ascii=False,
                )
                try:
                    conn.event_queue.put(("close", payload))
                except Exception:
                    pass

        return True

    def _get_session_nolock(
        self,
        user_id: str,
        chat_id: str,
        created_at: str,
    ) -> Optional[ServerSessionState]:
        user_sessions = self._sessions.get(user_id, {})
        session = user_sessions.get(chat_id)

        if session is None:
            return None
        if session.created_at != created_at:
            return None
        if session.closed:
            return None
        return session


terminal_session_service = TerminalSessionService()
terminal_session_service.start()