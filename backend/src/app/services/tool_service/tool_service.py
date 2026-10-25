import json
import threading
from queue import Queue, Empty
from typing import Dict, List, Optional

from app.modules.llm.tool_manager import ToolManager
from app.services.god_service.angel_status import AngelStoppedException
from app.services.command_approval_manager import approval_manager
from app.services.tool_service.tool_handler import ToolHandler
from app.services.tool_service.tools.terminal import TerminalStepToolHandler

from app.services.tool_service.tools.computer import ComputerToolHandler
from app.services.tool_service.tools.terminal import TerminalStepToolHandler


class ToolService:
    def __init__(self, *, user, chat, sender, ask_for_confirmation: int):
        self.user = user
        self.chat = chat
        self.sender = sender
        self.ask_for_confirmation = ask_for_confirmation

        self._call_queue: Queue = Queue()
        self._messages: List[Dict] = []
        self._messages_lock = threading.Lock()

        self._worker_thread: Optional[threading.Thread] = None
        self._worker_started = False
        self._stop_event = threading.Event()
        self._worker_exception: Optional[Exception] = None

    def get_tools(self):
        return ToolManager.load("terminal") + ToolManager.load("computer")

    def _build_tool(self, call: dict) -> ToolHandler:
        tool_name = call.get("name")
        arguments = call.get("arguments", {})

        if tool_name == "terminal":
            return TerminalStepToolHandler(
                user=self.user,
                chat=self.chat,
                sender=self.sender,
                call_id=call["call_id"],
                command=arguments.get("command", ""),
            )

        if tool_name == "computer_batch":
            return ComputerToolHandler(
                user=self.user,
                sender=self.sender,
                call_id=call["call_id"],
                computer_call={
                    "type": "computer_call",
                    "call_id": call["call_id"],
                    "actions": arguments.get("actions", []),
                },
            )

        raise ValueError(f"Tool no soportada: {tool_name}")

    def _should_ask_for_confirmation(self) -> bool:
        return self.ask_for_confirmation == 2

    def _build_tool_approval_payload(self, tool: dict) -> dict:
        return {
            "tool_name": tool.get("name"),
            "arguments": tool.get("arguments", {}),
        }

    def _build_function_call_message(self, tool: dict) -> Dict:
        return {
            "type": "function_call",
            "call_id": tool["call_id"],
            "name": tool["name"],
            "arguments": json.dumps(
                tool.get("arguments", {}),
                ensure_ascii=False,
            ),
        }

    def _build_denied_tool_output(self, tool: dict) -> Dict:
        return {
            "type": "function_call_output",
            "call_id": tool["call_id"],
            "output": f"No se permitió ejecutar la tool: {tool.get('name', '')}",
        }

    def _build_error_tool_output(self, tool: dict, error: Exception) -> Dict:
        return {
            "type": "function_call_output",
            "call_id": tool["call_id"],
            "output": f"Error ejecutando la tool {tool.get('name', '')}: {str(error)}",
        }

    def _append_message(self, message: Dict) -> None:
        with self._messages_lock:
            self._messages.append(message)

    def _ensure_worker(self) -> None:
        if self._worker_started:
            return

        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name=f"tool-service-worker-{self.chat.id}",
        )
        self._worker_thread.start()
        self._worker_started = True

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                call = self._call_queue.get(timeout=0.2)
            except Empty:
                continue

            try:
                self._append_message(self._build_function_call_message(call))

                if self._should_ask_for_confirmation():
                    payload = self._build_tool_approval_payload(call)

                    self.sender.send_tool_request(
                        payload["tool_name"],
                        payload["arguments"],
                    )

                    decision = approval_manager.wait_for_decision(
                        self.chat.id,
                        timeout_seconds=300,
                    )

                    if decision is not True:
                        self._append_message(self._build_denied_tool_output(call))
                        continue

                handler = self._build_tool(call)
                output = handler.execute()

                if output is not None:
                    self._append_message(output)

            except AngelStoppedException as e:
                self._worker_exception = e
            except Exception as e:
                self._append_message(self._build_error_tool_output(call, e))
                self._worker_exception = e
            finally:
                self._call_queue.task_done()

    def submit_call(self, call: dict) -> None:
        """
        Encola una tool para que el worker la procese.
        No bloquea por confirmación ni por ejecución.
        """
        if self._worker_exception:
            raise self._worker_exception

        self._ensure_worker()
        self._call_queue.put(call)

    def collect(self) -> List[Dict]:
        """
        Espera a que termine todo lo encolado y devuelve todos los mensajes
        generados por las tools hasta este momento.
        """
        self._call_queue.join()

        if self._worker_exception:
            raise self._worker_exception

        with self._messages_lock:
            messages = list(self._messages)
            self._messages.clear()

        return messages

    def shutdown(self) -> None:
        self._stop_event.set()

        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1)