import os

from app.modules.llm.prompt_manager import PromptManager
from app.modules.terminal.terminal_service import terminal_session_service
from app.services.god_service.angel_status import AngelStoppedException

idle_timeout = float(os.getenv("TERMINAL_IDLE_TIMEOUT_SECONDS"))
CREATED_AT = "CONSTANTE"


class TerminalStepToolHandler:
    name = "terminal"

    def __init__(
        self,
        *,
        user,
        chat,
        sender,
        call_id: str,
        command: str,
    ):
        self.user = user
        self.chat = chat
        self.sender = sender
        self.call_id = call_id
        self.command = command

    def execute(self) -> dict:
        try:
            if not self.command:
                raise Exception("No command")

            arguments = {
                "command": self.command,
            }

            self.sender.send_tool_execute(self.name, arguments)

            output = terminal_session_service.send_command(
                user=self.user,
                chat_id=self.chat.id,
                created_at=CREATED_AT,
                command_data={
                    "command": self.command,
                    "idle_timeout": idle_timeout,
                },
                timeout_seconds=60,
            )

            self.sender.send_tool_result(self.name, arguments, output)

        except AngelStoppedException:
            raise
        except Exception:
            output = PromptManager.load("no_command")

        return {
            "type": "function_call_output",
            "call_id": self.call_id,
            "output": output,
        }