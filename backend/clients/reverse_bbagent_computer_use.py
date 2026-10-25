import base64
import io
import json
import threading
import time
import requests
import getpass

from PIL import ImageGrab

from libraries.computer_use import OpenAIComputerActionExecutor
from libraries.user_client import UserManager
from libraries.client_config import get_backend_url


class ComputerStreamingClient:
    PING_TIMEOUT_SECONDS = 35
    STREAM_CONNECT_TIMEOUT_SECONDS = 10
    STREAM_READ_TIMEOUT_SECONDS = 35
    RECONNECT_DELAY_SECONDS = 2

    def __init__(self, base_url: str, auth_id: str):
        self.base_url = base_url.rstrip("/")
        self.auth_id = auth_id

        self.stream_http = requests.Session()
        self.api_http = requests.Session()

        self.stream_http.trust_env = False
        self.api_http.trust_env = False

        self.closed = False
        self.replaced = False

        self._lock = threading.RLock()
        self._stream_resp_lock = threading.RLock()
        self._active_stream_response = None

        self._executor = OpenAIComputerActionExecutor()
        self._busy = False

        self._last_ping = time.monotonic()
        self._watchdog_thread = threading.Thread(
            target=self._ping_watchdog_loop,
            name="computer-client-ping-watchdog",
            daemon=True,
        )

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

    def _auth_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.auth_id}",
        }

    def _run_stream_once(self):
        url = f"{self.base_url}/computer/events/stream"

        print(f"[stream] conectando a {url}")

        with self.stream_http.get(
            url,
            stream=True,
            timeout=(
                self.STREAM_CONNECT_TIMEOUT_SECONDS,
                self.STREAM_READ_TIMEOUT_SECONDS,
            ),
            headers={
                **self._auth_headers(),
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache",
            },
        ) as resp:
            with self._stream_resp_lock:
                self._active_stream_response = resp

            print(f"[stream] status={resp.status_code}")
            resp.raise_for_status()
            self._last_ping = time.monotonic()

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

        if event_name == "command":
            self._last_ping = time.monotonic()
            self._handle_command(payload)
            return

        if event_name == "screenshot":
            self._last_ping = time.monotonic()
            self._handle_screenshot(payload)
            return

        print(f"[stream] evento ignorado: {event_name} -> {payload}")

    def _handle_ping(self, payload: str):
        _ = json.loads(payload) if payload else {}
        try:
            self._send_heartbeat()
        except requests.RequestException as e:
            print(f"[heartbeat] error de red: {e}")
        except Exception as e:
            print(f"[heartbeat] error: {e}")

    def _handle_command(self, payload: str):
        data = json.loads(payload)
        computer_call = data["computer_call"]

        with self._lock:
            if self._busy:
                self._submit_result({
                    "ok": False,
                    "error": "No se pueden ejecutar nuevas acciones porque ya hay una operación en ejecución",
                })
                return

            self._busy = True

        worker = threading.Thread(
            target=self._run_command_worker,
            args=(computer_call,),
            name="computer-command",
            daemon=True,
        )
        worker.start()

    def _handle_screenshot(self, payload: str):
        _ = json.loads(payload) if payload else {}

        with self._lock:
            if self._busy:
                self._submit_screenshot(
                    image_base64="",
                    ok=False,
                    error="No se puede capturar screenshot porque ya hay una operación en ejecución",
                )
                return

            self._busy = True

        worker = threading.Thread(
            target=self._run_screenshot_worker,
            name="computer-screenshot",
            daemon=True,
        )
        worker.start()

    def _run_command_worker(self, computer_call: dict):
        try:
            time.sleep(0.2)
            exec_result = self._executor.execute_computer_call(computer_call)
            time.sleep(0.2)
            image_base64 = self._capture_screenshot_base64()

            result_payload = {
                "ok": True,
                "call_id": exec_result.get("call_id"),
                "count": exec_result.get("count"),
                "results": exec_result.get("results", []),
                "image_base64": image_base64,
            }

        except Exception as e:
            result_payload = {
                "ok": False,
                "error": str(e),
                "image_base64": "",
            }
            print(f"[command] error ejecutando acción: {e}")
        finally:
            with self._lock:
                self._busy = False

        try:
            self._submit_result(result_payload)
        except Exception as e:
            print(f"[result] error enviando resultado: {e}")

    def _run_screenshot_worker(self):
        try:
            image_base64 = self._capture_screenshot_base64()
            self._submit_screenshot(
                image_base64=image_base64,
                ok=True,
                error=None,
            )
        except Exception as e:
            print(f"[screenshot] error capturando/enviando: {e}")
            try:
                self._submit_screenshot(
                    image_base64="",
                    ok=False,
                    error=str(e),
                )
            except Exception as inner_e:
                print(f"[screenshot] error adicional enviando fallo: {inner_e}")
        finally:
            with self._lock:
                self._busy = False

    def _send_heartbeat(self):
        url = f"{self.base_url}/computer/heartbeat"

        with self._lock:
            payload = {
                "busy": self._busy,
            }

        print(f"[heartbeat] -> {url}")
        with requests.Session() as s:
            s.trust_env = False
            resp = s.post(
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

    def _submit_result(self, result_payload: dict):
        url = f"{self.base_url}/computer/actions/result"
        payload = {
            "result": result_payload,
        }

        print(f"[result] -> {url}")
        with requests.Session() as s:
            s.trust_env = False
            resp = s.post(
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

    def _submit_screenshot(self, image_base64: str, ok: bool, error: str | None):
        url = f"{self.base_url}/computer/screenshots/result"
        payload = {
            "ok": ok,
            "error": error,
            "image_base64": image_base64,
        }

        print(f"[screenshot] -> {url}")
        with requests.Session() as s:
            s.trust_env = False
            resp = s.post(
                url,
                json=payload,
                timeout=60,
                headers={
                    **self._auth_headers(),
                    "Content-Type": "application/json",
                },
            )
            print(f"[screenshot] <- status={resp.status_code} body={resp.text}")
            resp.raise_for_status()

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

        self.stream_http = requests.Session()
        self.stream_http.trust_env = False

    def _ping_watchdog_loop(self):
        while not self.closed and not self.replaced:
            elapsed = time.monotonic() - self._last_ping

            if elapsed > self.PING_TIMEOUT_SECONDS:
                print("[watchdog] timeout de ping, forzando reconnect del stream")
                self._force_break_stream()
                self._last_ping = time.monotonic()

            time.sleep(1.0)

    def _capture_screenshot_base64(self) -> str:
        image = ImageGrab.grab(all_screens=True)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def close(self):
        if self.closed:
            return

        self.closed = True
        self._force_break_stream()

        try:
            self.api_http.close()
        except Exception:
            pass


if __name__ == "__main__":
    url = get_backend_url()
    login = input("Login: ")
    password = getpass.getpass("Contraseña: ")

    user_client = UserManager(url)

    print("Login...")
    session_auth_id = user_client.login(login, password)
    print("Autenticación correcta. Cliente de control gráfico conectado.")

    computer_client = ComputerStreamingClient(
        base_url=url,
        auth_id=session_auth_id,
    )
    computer_client.run()
