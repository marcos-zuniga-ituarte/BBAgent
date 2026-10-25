import json
import threading
import time
import requests
import getpass
from dataclasses import dataclass

from libraries.terminal_pty import TerminalPTY
from libraries.user_client import UserManager
from libraries.client_config import get_backend_url


@dataclass
class LocalTerminalSession:
    chat_id: str
    created_at: str
    shell: TerminalPTY
    busy: bool = False


class TerminalStreamingClient:
    ALLOWED_EXECUTE_FIELDS = {
        "command",
        "pattern",
        "idle_timeout",
        "max_timeout",
        "head_lines",
        "tail_lines",
    }

    PING_TIMEOUT_SECONDS = 35
    STREAM_CONNECT_TIMEOUT_SECONDS = 10
    STREAM_READ_TIMEOUT_SECONDS = 35
    RECONNECT_DELAY_SECONDS = 2

    def __init__(self, base_url: str, auth_id: str):
        self.base_url = base_url.rstrip("/")
        self.auth_id = auth_id

        self.stream_http = self._new_stream_session()

        self.closed = False
        self.replaced = False

        self._sessions_lock = threading.RLock()
        self._sessions_by_chat: dict[str, LocalTerminalSession] = {}

        self._pending_results_lock = threading.RLock()
        self._pending_results: dict[tuple[str, str], str] = {}

        self._stream_resp_lock = threading.RLock()
        self._active_stream_response = None

        self._last_ping = time.monotonic()
        self._watchdog_thread = threading.Thread(
            target=self._ping_watchdog_loop,
            name="terminal-client-ping-watchdog",
            daemon=True,
        )

    def _auth_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.auth_id}",
        }

    def _new_stream_session(self) -> requests.Session:
        session = requests.Session()
        session.trust_env = False
        session.headers.update(
            {
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
        return session

    def _new_api_session(self) -> requests.Session:
        session = requests.Session()
        session.trust_env = False
        session.headers.update(
            {
                "Cache-Control": "no-cache",
                "Connection": "close",
            }
        )
        return session

    def run(self):
        self._watchdog_thread.start()

        try:
            while not self.closed and not self.replaced:
                try:
                    self._run_stream_once()
                except requests.RequestException as e:
                    if self.closed or self.replaced:
                        break
                    print(f"[stream] error de red: {e}")
                    self._force_break_stream()
                    time.sleep(self.RECONNECT_DELAY_SECONDS)
                except Exception as e:
                    if self.closed or self.replaced:
                        break
                    print(f"[stream] error: {e}")
                    self._force_break_stream()
                    time.sleep(self.RECONNECT_DELAY_SECONDS)
        finally:
            self.close()

    def _run_stream_once(self):
        url = f"{self.base_url}/terminal/events/stream"

        print(f"[stream] conectando a {url}")

        with self.stream_http.get(
            url,
            stream=True,
            timeout=(
                self.STREAM_CONNECT_TIMEOUT_SECONDS,
                self.STREAM_READ_TIMEOUT_SECONDS,
            ),
            headers=self._auth_headers(),
        ) as resp:
            with self._stream_resp_lock:
                self._active_stream_response = resp

            print(f"[stream] status={resp.status_code}")
            resp.raise_for_status()
            self._last_ping = time.monotonic()

            self._flush_pending_results_if_any()

            event_name = None
            data_lines = []

            try:
                for raw_line in resp.iter_lines(decode_unicode=True, chunk_size=1):
                    if self.closed or self.replaced:
                        return

                    if raw_line is None:
                        continue

                    line = raw_line.rstrip("\r")

                    if line == "":
                        if event_name is not None or data_lines:
                            payload = "\n".join(data_lines)
                            self._handle_event(event_name, payload)
                        event_name = None
                        data_lines = []
                        continue

                    if line.startswith(":"):
                        continue

                    if line.startswith("event:"):
                        event_name = line[len("event:"):].strip()
                    elif line.startswith("data:"):
                        data_lines.append(line[len("data:"):].lstrip())
            finally:
                with self._stream_resp_lock:
                    if self._active_stream_response is resp:
                        self._active_stream_response = None

    def _handle_event(self, event_name: str, payload: str):
        if event_name == "connected":
            print("[stream] conectado")
            return

        if event_name == "disconnect":
            print(f"[stream] desconectado por servidor: {payload}")
            if payload.strip() == "replaced":
                self.replaced = True
            return

        if event_name == "ping":
            self._last_ping = time.monotonic()
            self._handle_ping(payload)
            return

        if event_name == "create":
            self._handle_create(payload)
            return

        if event_name == "close":
            self._handle_close(payload)
            return

        if event_name == "command":
            self._handle_command(payload)
            return

        print(f"[stream] evento ignorado: {event_name} -> {payload}")

    def _handle_ping(self, payload: str):
        data = json.loads(payload) if payload else {}
        if not isinstance(data, dict):
            raise ValueError("El ping debe ser un JSON object")

        server_sessions = data.get("sessions", [])
        if not isinstance(server_sessions, list):
            server_sessions = []

        self._reconcile_local_sessions_with_server(server_sessions)
        self._flush_pending_results_if_any()

        try:
            self._send_heartbeat()
        except requests.RequestException as e:
            print(f"[heartbeat] error de red: {e}")
        except Exception as e:
            print(f"[heartbeat] error: {e}")

    def _handle_create(self, payload: str):
        data = json.loads(payload)
        chat_id = self._require_str(data, "chat_id")
        created_at = self._require_str(data, "created_at")

        with self._sessions_lock:
            current = self._sessions_by_chat.get(chat_id)

            if current is not None:
                if current.created_at == created_at:
                    return

                self._close_session_locked(current)

            self._sessions_by_chat[chat_id] = LocalTerminalSession(
                chat_id=chat_id,
                created_at=created_at,
                shell=TerminalPTY(),
            )

        print(f"[create] sesión creada chat_id={chat_id} created_at={created_at}")

    def _handle_close(self, payload: str):
        data = json.loads(payload)
        chat_id = self._require_str(data, "chat_id")
        created_at = self._require_str(data, "created_at")

        with self._sessions_lock:
            current = self._sessions_by_chat.get(chat_id)
            if current is None:
                return

            if current.created_at != created_at:
                return

            self._close_session_locked(current)
            self._sessions_by_chat.pop(chat_id, None)

        self._drop_pending_result(chat_id, created_at)
        print(f"[close] sesión cerrada chat_id={chat_id} created_at={created_at}")

    def _handle_command(self, payload: str):
        data = json.loads(payload)
        chat_id = self._require_str(data, "chat_id")
        created_at = self._require_str(data, "created_at")

        execute_kwargs = {
            key: value
            for key, value in data.items()
            if key in self.ALLOWED_EXECUTE_FIELDS
        }

        if "command" not in execute_kwargs or not isinstance(execute_kwargs["command"], str):
            raise ValueError("El campo 'command' es obligatorio y debe ser string")

        with self._sessions_lock:
            current = self._sessions_by_chat.get(chat_id)
            if current is None or current.created_at != created_at:
                self._queue_result_for_delivery(
                    chat_id=chat_id,
                    created_at=created_at,
                    result_text="La sesión no existe en el cliente",
                )
                self._flush_pending_results_if_any()
                return

            if current.busy:
                print(
                    f"[command] comando ignorado porque la sesión ya está busy "
                    f"chat_id={chat_id} created_at={created_at}"
                )
                return

            current.busy = True

        worker = threading.Thread(
            target=self._run_command_worker,
            args=(chat_id, created_at, execute_kwargs),
            name=f"terminal-command-{chat_id}",
            daemon=True,
        )
        worker.start()

    def _run_command_worker(self, chat_id: str, created_at: str, execute_kwargs: dict):
        result_text = ""

        try:
            with self._sessions_lock:
                current = self._sessions_by_chat.get(chat_id)
                if current is None or current.created_at != created_at:
                    return
                shell = current.shell

            result = shell.execute(**execute_kwargs)
            result_text = result or ""
        except Exception as e:
            result_text = str(e)
            print(f"[command] error ejecutando chat_id={chat_id}: {result_text}")

        self._queue_result_for_delivery(
            chat_id=chat_id,
            created_at=created_at,
            result_text=result_text,
        )
        self._flush_pending_results_if_any()

    def _queue_result_for_delivery(self, chat_id: str, created_at: str, result_text: str):
        key = (chat_id, created_at)

        with self._pending_results_lock:
            self._pending_results[key] = result_text

        with self._sessions_lock:
            current = self._sessions_by_chat.get(chat_id)
            if current is not None and current.created_at == created_at:
                current.busy = True

    def _drop_pending_result(self, chat_id: str, created_at: str):
        key = (chat_id, created_at)
        with self._pending_results_lock:
            self._pending_results.pop(key, None)

    def _mark_result_delivered(self, chat_id: str, created_at: str):
        self._drop_pending_result(chat_id, created_at)

        with self._sessions_lock:
            current = self._sessions_by_chat.get(chat_id)
            if current is not None and current.created_at == created_at:
                current.busy = False

    def _flush_pending_results_if_any(self) -> bool:
        with self._pending_results_lock:
            items = list(self._pending_results.items())

        for (chat_id, created_at), result_text in items:
            try:
                self._post_result_once(
                    chat_id=chat_id,
                    created_at=created_at,
                    result_text=result_text,
                )
                self._mark_result_delivered(chat_id, created_at)

            except requests.HTTPError as e:
                status_code = None
                try:
                    status_code = e.response.status_code
                except Exception:
                    pass

                print(
                    f"[result] error HTTP enviando resultado "
                    f"chat_id={chat_id} created_at={created_at}: {e}"
                )

                if status_code == 409:
                    self._mark_result_delivered(chat_id, created_at)
                    continue

                self._force_break_stream()
                return False

            except Exception as e:
                print(
                    f"[result] error enviando resultado "
                    f"chat_id={chat_id} created_at={created_at}: {e}"
                )
                self._force_break_stream()
                return False

        return True

    def _send_heartbeat(self):
        url = f"{self.base_url}/terminal/heartbeat"
        payload = {
            "sessions": self._list_local_sessions(),
        }

        print(f"[heartbeat] -> {url}")
        with self._new_api_session() as session:
            resp = session.post(
                url,
                json=payload,
                timeout=10,
                headers={
                    **self._auth_headers(),
                    "Content-Type": "application/json",
                },
            )
            print(f"[heartbeat] <- status={resp.status_code} body={resp.text}")
            resp.raise_for_status()

    def _post_result_once(self, chat_id: str, created_at: str, result_text: str):
        url = f"{self.base_url}/terminal/sessions/result"
        payload = {
            "chat_id": chat_id,
            "created_at": created_at,
            "output": result_text,
        }

        print(f"[result] -> {url}")
        with self._new_api_session() as session:
            resp = session.post(
                url,
                json=payload,
                timeout=60,
                headers={
                    **self._auth_headers(),
                    "Content-Type": "application/json",
                },
            )
            print(f"[result] <- status={resp.status_code} body={resp.text}")
            resp.raise_for_status()

    def _list_local_sessions(self) -> list[dict]:
        with self._sessions_lock:
            return [
                {
                    "chat_id": session.chat_id,
                    "created_at": session.created_at,
                }
                for session in self._sessions_by_chat.values()
            ]

    def _reconcile_local_sessions_with_server(self, server_sessions: list[dict]):
        server_keys = set()

        for item in server_sessions:
            if not isinstance(item, dict):
                continue

            chat_id = item.get("chat_id")
            created_at = item.get("created_at")

            if not isinstance(chat_id, str) or not isinstance(created_at, str):
                continue

            server_keys.add((chat_id, created_at))

        with self._sessions_lock:
            chats_to_remove = []

            for chat_id, local_session in self._sessions_by_chat.items():
                local_key = (local_session.chat_id, local_session.created_at)
                if local_key not in server_keys:
                    self._close_session_locked(local_session)
                    chats_to_remove.append((chat_id, local_session.created_at))

            for chat_id, created_at in chats_to_remove:
                self._sessions_by_chat.pop(chat_id, None)
                self._drop_pending_result(chat_id, created_at)

    def _force_break_stream(self):
        with self._stream_resp_lock:
            resp = self._active_stream_response
            self._active_stream_response = None

        if resp is not None:
            try:
                resp.close()
            except Exception:
                pass

        try:
            self.stream_http.close()
        except Exception:
            pass

        self.stream_http = self._new_stream_session()

    def _ping_watchdog_loop(self):
        while not self.closed and not self.replaced:
            elapsed = time.monotonic() - self._last_ping

            if elapsed > self.PING_TIMEOUT_SECONDS:
                print("[watchdog] timeout de ping, forzando reconnect del stream")
                self._force_break_stream()
                self._last_ping = time.monotonic()

            time.sleep(1.0)

    def _close_all_sessions(self):
        with self._sessions_lock:
            sessions = list(self._sessions_by_chat.values())
            self._sessions_by_chat.clear()

        for session in sessions:
            try:
                session.shell.close()
            except Exception:
                pass

        with self._pending_results_lock:
            self._pending_results.clear()

    def _close_session_locked(self, session: LocalTerminalSession):
        try:
            session.shell.close()
        except Exception:
            pass

    @staticmethod
    def _require_str(data: dict, key: str) -> str:
        value = data.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"El campo '{key}' es obligatorio y debe ser string")
        return value

    def close(self):
        if self.closed:
            return

        self.closed = True
        self._force_break_stream()
        self._close_all_sessions()


if __name__ == "__main__":
    url = get_backend_url()
    login = input("Login: ")
    password = getpass.getpass("Contraseña: ")

    user_client = UserManager(url)

    print("Login...")
    session_aut_id = user_client.login(login, password)
    print("Autenticación correcta. Cliente de terminal conectado.")

    terminal_client = TerminalStreamingClient(
        base_url=url,
        auth_id=session_aut_id,
    )
    terminal_client.run()
