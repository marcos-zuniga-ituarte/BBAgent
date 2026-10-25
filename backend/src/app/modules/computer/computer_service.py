import json
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Optional


class NoComputerClient(Exception):
    pass


class PendingComputerCallError(Exception):
    pass


class PendingScreenshotError(Exception):
    pass


@dataclass
class PendingCall:
    event: threading.Event = field(default_factory=threading.Event)
    result: Optional[dict] = None


@dataclass
class PendingScreenshot:
    event: threading.Event = field(default_factory=threading.Event)
    result: Optional[dict] = None


@dataclass
class ComputerClientState:
    user_id: str
    event_queue: queue.Queue = field(default_factory=queue.Queue)
    last_ping_at: float = field(default_factory=time.monotonic)
    connected: bool = True
    busy: bool = False
    pending_call: Optional[PendingCall] = None
    pending_screenshot: Optional[PendingScreenshot] = None


class ComputerSessionService:
    # Más relajado para VPS / red pública / microcortes
    PING_INTERVAL_SECONDS = 10
    PING_GRACE_SECONDS = 90
    WAIT_FOR_CLIENT_SECONDS = 15.0
    WAIT_FOR_CLIENT_POLL_SECONDS = 0.2

    def __init__(self):
        self._lock = threading.RLock()
        self._clients_by_user_id: dict[str, ComputerClientState] = {}
        self._stop_event = threading.Event()
        self._heartbeat_thread: Optional[threading.Thread] = None

    def start(self):
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            return

        self._stop_event.clear()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            name="computer-client-heartbeat",
            daemon=True,
        )
        self._heartbeat_thread.start()

    def shutdown(self):
        self._stop_event.set()

        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=1)

        with self._lock:
            clients = list(self._clients_by_user_id.values())
            self._clients_by_user_id.clear()

        for client in clients:
            try:
                client.connected = False
                client.event_queue.put_nowait(None)
            except Exception:
                pass

            if client.pending_call is not None:
                client.pending_call.result = {
                    "ok": False,
                    "error": "Computer service shutdown",
                }
                client.pending_call.event.set()
                client.pending_call = None

            if client.pending_screenshot is not None:
                client.pending_screenshot.result = {
                    "ok": False,
                    "error": "Computer service shutdown",
                    "image_base64": "",
                }
                client.pending_screenshot.event.set()
                client.pending_screenshot = None

            client.busy = False

    def stream_generator(self, user_id: str):
        event_queue = queue.Queue()
        user_id = str(user_id)

        with self._lock:
            previous = self._clients_by_user_id.get(user_id)
            if previous is not None:
                try:
                    previous.connected = False
                    previous.event_queue.put_nowait(
                        {
                            "event": "disconnect",
                            "data": "replaced",
                        }
                    )
                    previous.event_queue.put_nowait(None)
                except Exception:
                    pass

                if previous.pending_call is not None:
                    previous.pending_call.result = {
                        "ok": False,
                        "error": "Cliente reemplazado por una nueva conexión",
                    }
                    previous.pending_call.event.set()
                    previous.pending_call = None

                if previous.pending_screenshot is not None:
                    previous.pending_screenshot.result = {
                        "ok": False,
                        "error": "Cliente reemplazado por una nueva conexión",
                        "image_base64": "",
                    }
                    previous.pending_screenshot.event.set()
                    previous.pending_screenshot = None

            client = ComputerClientState(
                user_id=user_id,
                event_queue=event_queue,
                last_ping_at=time.monotonic(),
                connected=True,
            )
            self._clients_by_user_id[user_id] = client

        yield self._format_sse("connected", "ok")

        try:
            while True:
                try:
                    item = event_queue.get(timeout=15)
                except queue.Empty:
                    # keepalive SSE por si no hay eventos
                    yield self._format_sse("ping", json.dumps({}, ensure_ascii=False))
                    continue

                if item is None:
                    break

                yield self._format_sse(item["event"], item["data"])
        finally:
            with self._lock:
                current = self._clients_by_user_id.get(user_id)
                if current is client:
                    self._clients_by_user_id.pop(user_id, None)

            if client.pending_call is not None:
                client.pending_call.result = {
                    "ok": False,
                    "error": "Cliente desconectado",
                }
                client.pending_call.event.set()
                client.pending_call = None

            if client.pending_screenshot is not None:
                client.pending_screenshot.result = {
                    "ok": False,
                    "error": "Cliente desconectado",
                    "image_base64": "",
                }
                client.pending_screenshot.event.set()
                client.pending_screenshot = None

            client.connected = False
            client.busy = False

    def register_pong(self, *, user_id: str, busy: bool):
        with self._lock:
            client = self._clients_by_user_id.get(str(user_id))
            if client is None or not client.connected:
                return

            client.last_ping_at = time.monotonic()

            # Solo aceptamos busy=True si realmente hay una operación pendiente
            client.busy = bool(busy) and (
                client.pending_call is not None or client.pending_screenshot is not None
            )

    def submit_result(self, *, user_id: str, result: dict) -> bool:
        with self._lock:
            client = self._clients_by_user_id.get(str(user_id))
            if client is None or client.pending_call is None:
                return False

            pending = client.pending_call
            client.pending_call = None
            client.busy = client.pending_screenshot is not None

            pending.result = dict(result)
            pending.event.set()
            return True

    def submit_screenshot(self, *, user_id: str, screenshot_data: dict) -> bool:
        with self._lock:
            client = self._clients_by_user_id.get(str(user_id))
            if client is None or client.pending_screenshot is None:
                return False

            pending = client.pending_screenshot
            client.pending_screenshot = None
            client.busy = client.pending_call is not None

            pending.result = dict(screenshot_data)
            pending.event.set()
            return True

    def send_computer_call(
        self,
        *,
        user,
        computer_call: dict,
        timeout_seconds: float = 60,
    ) -> dict:
        self._wait_for_client(str(user.id))

        with self._lock:
            current = self._clients_by_user_id.get(str(user.id))
            if current is None or not current.connected:
                raise NoComputerClient("No hay cliente computer conectado para este usuario")

            if (
                current.pending_call is not None
                or current.pending_screenshot is not None
                or current.busy
            ):
                raise PendingComputerCallError("Ya hay una ejecución pendiente para este usuario")

            pending = PendingCall()
            current.pending_call = pending
            current.busy = True

            current.event_queue.put_nowait(
                {
                    "event": "command",
                    "data": json.dumps(
                        {"computer_call": computer_call},
                        ensure_ascii=False,
                    ),
                }
            )

        completed = pending.event.wait(timeout=timeout_seconds)
        if not completed:
            with self._lock:
                latest = self._clients_by_user_id.get(str(user.id))
                if latest is not None and latest.pending_call is pending:
                    latest.pending_call = None
                    latest.busy = latest.pending_screenshot is not None

            raise TimeoutError("Timeout esperando resultado del cliente computer")

        return pending.result or {
            "ok": False,
            "error": "Resultado vacío",
        }

    def request_screenshot(
        self,
        *,
        user,
        timeout_seconds: float = 60,
    ) -> dict:
        self._wait_for_client(str(user.id))

        with self._lock:
            current = self._clients_by_user_id.get(str(user.id))
            if current is None or not current.connected:
                raise NoComputerClient("No hay cliente computer conectado para este usuario")

            if (
                current.pending_call is not None
                or current.pending_screenshot is not None
                or current.busy
            ):
                raise PendingScreenshotError("Ya hay una operación pendiente para este usuario")

            pending = PendingScreenshot()
            current.pending_screenshot = pending
            current.busy = True

            current.event_queue.put_nowait(
                {
                    "event": "screenshot",
                    "data": json.dumps({}, ensure_ascii=False),
                }
            )

        completed = pending.event.wait(timeout=timeout_seconds)
        if not completed:
            with self._lock:
                latest = self._clients_by_user_id.get(str(user.id))
                if latest is not None and latest.pending_screenshot is pending:
                    latest.pending_screenshot = None
                    latest.busy = latest.pending_call is not None

            raise TimeoutError("Timeout esperando screenshot del cliente computer")

        return pending.result or {
            "ok": False,
            "error": "Resultado de screenshot vacío",
            "image_base64": "",
        }

    def _wait_for_client(self, user_id: str) -> ComputerClientState:
        deadline = time.monotonic() + self.WAIT_FOR_CLIENT_SECONDS

        while True:
            with self._lock:
                client = self._clients_by_user_id.get(user_id)
                if client is not None and client.connected:
                    return client

            if time.monotonic() >= deadline:
                raise NoComputerClient("No hay cliente computer conectado para este usuario")

            time.sleep(self.WAIT_FOR_CLIENT_POLL_SECONDS)

    def _heartbeat_loop(self):
        while not self._stop_event.wait(self.PING_INTERVAL_SECONDS):
            now = time.monotonic()

            with self._lock:
                snapshot = list(self._clients_by_user_id.items())

            stale_users = []

            for user_id, client in snapshot:
                if not client.connected:
                    continue

                if (now - client.last_ping_at) > self.PING_GRACE_SECONDS:
                    stale_users.append(user_id)
                    continue

                try:
                    client.event_queue.put_nowait(
                        {
                            "event": "ping",
                            "data": json.dumps({}, ensure_ascii=False),
                        }
                    )
                except Exception:
                    stale_users.append(user_id)

            for user_id in stale_users:
                self._close_user_state(
                    user_id=user_id,
                    reason="Cliente desconectado",
                )

    def _close_user_state(self, user_id: str, reason: str):
        with self._lock:
            client = self._clients_by_user_id.pop(user_id, None)

        if client is None:
            return

        client.connected = False

        try:
            client.event_queue.put_nowait(None)
        except Exception:
            pass

        if client.pending_call is not None:
            client.pending_call.result = {
                "ok": False,
                "error": reason,
            }
            client.pending_call.event.set()
            client.pending_call = None

        if client.pending_screenshot is not None:
            client.pending_screenshot.result = {
                "ok": False,
                "error": reason,
                "image_base64": "",
            }
            client.pending_screenshot.event.set()
            client.pending_screenshot = None

        client.busy = False

    @staticmethod
    def _format_sse(event: str, data: str) -> str:
        return f"event: {event}\ndata: {data}\n\n"


computer_session_service = ComputerSessionService()
computer_session_service.start()