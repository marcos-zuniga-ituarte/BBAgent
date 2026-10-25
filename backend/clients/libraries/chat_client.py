import requests
import json
from typing import Callable, Optional


class AgentClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = f"{base_url}/chat"

    # -----------------------------
    # Helpers
    # -----------------------------

    def _handle_response(self, response: requests.Response):
        try:
            data = response.json()
        except Exception:
            raise Exception(f"Respuesta inválida: {response.text}")

        if not response.ok:
            raise Exception(f"Error {response.status_code}: {data}")

        return data

    # -----------------------------
    # Chats
    # -----------------------------

    def create_chat(self, access_token: str) -> str:
        response = requests.post(
            self.base_url,
            params={"access_token": access_token},
        )
        return self._handle_response(response)

    def get_chats(self, access_token: str):
        response = requests.get(
            self.base_url,
            params={"access_token": access_token},
        )
        return self._handle_response(response)

    def get_messages(self, chat_id: str, access_token: str):
        response = requests.get(
            f"{self.base_url}/{chat_id}/messages",
            params={"access_token": access_token},
        )
        return self._handle_response(response)

    # -----------------------------
    # Confirmación de comandos 🔥
    # -----------------------------

    def send_command_decision(
        self,
        chat_id: str,
        access_token: str,
        decision: str,
    ):
        response = requests.post(
            f"{self.base_url}/session/{chat_id}/command-response",
            params={
                "access_token": access_token,
                "decision": decision,
            },
        )
        return self._handle_response(response)

    # -----------------------------
    # Streaming chat
    # -----------------------------

    def stream_chat(
        self,
        chat_id: str,
        access_token: str,
        message: str,
        ask_for_confirmation: int = 0,
        on_command_request: Optional[Callable[[str], bool]] = None,
    ):
        """
        on_command_request:
            callback que recibe (command: str) y devuelve "y" o "n"
        """

        response = requests.post(
            f"{self.base_url}/stream/{chat_id}",
            json={
                "message": message,
                "sessionAutId": access_token,
                "askForConfirmation": ask_for_confirmation,
            },
            stream=True,
        )

        if response.status_code != 200:
            raise Exception(f"Error: {response.text}")

        current_event = None

        for raw_line in response.iter_lines(decode_unicode=True):
            if not raw_line:
                continue

            line = raw_line.strip()

            # Leer tipo de evento
            if line.startswith("event:"):
                current_event = line.replace("event:", "").strip()
                continue

            # Leer data
            if line.startswith("data:"):
                data = json.loads(line.replace("data:", "").strip())

                yield {
                    "event": current_event,
                    "data": data,
                }

                # -----------------------------
                # Manejo automático de confirmaciones
                # -----------------------------
                if current_event == "command_request":
                    command = data.get("command")

                    decision = False

                    if on_command_request:
                        decision = on_command_request(command)
                    else:
                        decision = False

                    self.send_command_decision(
                        chat_id,
                        access_token,
                        decision,
                    )

                if current_event in {"done", "error"}:
                    break