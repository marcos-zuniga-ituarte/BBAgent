import json

from app.modules.computer.computer_service import computer_session_service
from app.services.god_service.angel_status import AngelStoppedException


class ComputerToolHandler:
    name = "computer_batch"

    def __init__(
        self,
        *,
        user,
        sender,
        call_id: str,
        computer_call: dict,
    ):
        self.user = user
        self.sender = sender
        self.call_id = call_id
        self.computer_call = computer_call

    def execute(self) -> dict:
        try:
            if not self.computer_call:
                raise Exception("No computer_call")

            arguments = {
                "computer_call": self.computer_call,
            }

            self.sender.send_tool_execute(self.name, arguments)

            output = computer_session_service.send_computer_call(
                user=self.user,
                computer_call=self.computer_call,
                timeout_seconds=60,
            )

            self.sender.send_tool_result(self.name, arguments, output)

        except AngelStoppedException:
            raise
        except Exception as e:
            output = {
                "ok": False,
                "error": str(e),
            }

        content = [
            {
                "type": "input_text",
                "text": json.dumps(
                    {
                        "ok": output.get("ok", False),
                        "error": output.get("error"),
                        "count": output.get("count"),
                        "results": output.get("results"),
                    },
                    ensure_ascii=False,
                ),
            }
        ]

        image_base64 = output.get("image_base64")
        if image_base64:
            content.append(
                {
                    "type": "input_image",
                    "image_url": f"data:image/png;base64,{image_base64}",
                    "detail": "original",
                }
            )

        return {
            "type": "function_call_output",
            "call_id": self.call_id,
            "output": content,
        }