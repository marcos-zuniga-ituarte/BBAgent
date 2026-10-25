import asyncio
import json
import threading
import uuid
from typing import Any
import queue
import uuid


def sse_event(data: dict, event: str | None = None) -> str:
    parts = []
    if event:
        parts.append(f"event: {event}")
    parts.append(f"data: {json.dumps(data, ensure_ascii=False)}")
    return "\n".join(parts) + "\n\n"


class StreamingSubscriber:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.queue = queue.Queue()
        self.active = True

    def push(self, item: dict) -> None:
        if not self.active:
            return
        self.queue.put(item)

    def close(self) -> None:
        self.active = False
        try:
            self.queue.put_nowait(None)
        except Exception:
            pass


class AngelStoppedException(Exception):
    pass


class AngelStatus:
    """
    Estado vivo asociado a un chat/angel.

    Guarda:
    - subscribers
    - fase actual
    - tool pendiente de aprobación
    - historial corto de tools/resultados
    - respuesta parcial en streaming
    - estado de ejecución
    """

    def __init__(self, chat):
        self.chat = chat
        self.chat_id = chat.id

        self._lock = threading.RLock()
        self._subscribers: dict[str, StreamingSubscriber] = {}

        self.is_running = False
        self.is_done = False
        self.error_message: str | None = None

        self.current_status: dict[str, Any] | None = None
        self.pending_tool_request: dict[str, Any] | None = None
        self.tool_history: list[dict[str, Any]] = []
        self.partial_response = ""

        self.stop_requested = False
        self.stop_reason: str | None = None

    def reset_for_new_run(self) -> None:
        with self._lock:
            self.is_running = True
            self.is_done = False
            self.error_message = None
            self.current_status = None
            self.pending_tool_request = None
            self.tool_history = []
            self.partial_response = ""
            self.stop_requested = False
            self.stop_reason = None

    def request_stop(self, reason: str = "Stopped by user") -> None:
        with self._lock:
            self.stop_requested = True
            self.stop_reason = reason

        self._broadcast(
            "stopping",
            {
                "type": "stopping",
                "chat_id": self.chat_id,
                "message": reason,
            },
        )

    def should_stop(self) -> bool:
        with self._lock:
            return self.stop_requested

    def raise_if_stopped(self) -> None:
        with self._lock:
            if self.stop_requested:
                raise AngelStoppedException(self.stop_reason or "Stopped by user")

    def send_stopped(self) -> None:
        with self._lock:
            self.is_running = False
            self.is_done = True
            self.current_status = None
            self.pending_tool_request = None

        self._broadcast(
            "stopped",
            {
                "type": "stopped",
                "chat_id": self.chat_id,
                "message": self.stop_reason or "Stopped by user",
            },
        )

    def finish_run(self) -> None:
        with self._lock:
            self.is_running = False
            self.is_done = True

    def fail_run(self, message: str) -> None:
        with self._lock:
            self.is_running = False
            self.is_done = True
            self.error_message = message

    def attach(self) -> StreamingSubscriber:
        subscriber = StreamingSubscriber()

        with self._lock:
            self._subscribers[subscriber.id] = subscriber

            snapshot = {
                "event": "snapshot",
                "data": {
                    "type": "snapshot",
                    "chat_id": self.chat_id,
                    "messages": self.chat.get_messages_for_ui(),
                    "live": {
                        "is_running": self.is_running,
                        "is_done": self.is_done,
                        "error_message": self.error_message,
                        "current_status": self.current_status,
                        "pending_tool_request": self.pending_tool_request,
                        "tool_history": self.tool_history,
                        "partial_response": self.partial_response,
                    },
                },
            }

        subscriber.push(snapshot)
        return subscriber

    def detach(self, subscriber_id: str) -> None:
        with self._lock:
            subscriber = self._subscribers.pop(subscriber_id, None)

        if subscriber is not None:
            subscriber.close()

    def _raise_if_stopped(self) -> None:
        with self._lock:
            if self.stop_requested:
                raise AngelStoppedException(self.stop_reason or "Stopped by user")

    def _broadcast(self, event: str, data: dict) -> None:
        payload = {
            "chat_id": self.chat_id,
            **data,
        }
        item = {"event": event, "data": payload}

        with self._lock:
            subscribers = list(self._subscribers.values())

        dead_ids = []
        for subscriber in subscribers:
            if not subscriber.active:
                dead_ids.append(subscriber.id)
                continue
            try:
                subscriber.push(item)
            except Exception:
                dead_ids.append(subscriber.id)

        if dead_ids:
            with self._lock:
                for dead_id in dead_ids:
                    sub = self._subscribers.pop(dead_id, None)
                    if sub is not None:
                        sub.close()

    def send_token(self, delta: str) -> None:
        self._raise_if_stopped()

        with self._lock:
            self.partial_response += delta

        self._broadcast(
            "token",
            {
                "type": "token",
                "delta": delta,
            },
        )

    def send_status(self, phase: str, message: str = None) -> None:
        self._raise_if_stopped()

        status_data = {
            "type": "status",
            "phase": phase,
            "message": message,
        }

        with self._lock:
            self.current_status = status_data

        self._broadcast("status", status_data)

    def send_tool_request(self, tool_name: str, arguments: dict) -> None:
        self._raise_if_stopped()

        data = {
            "type": "tool_request",
            "tool_name": tool_name,
            "arguments": arguments,
            "message": f"Tool proposed: {tool_name}",
        }

        with self._lock:
            self.pending_tool_request = data

        self._broadcast("tool_request", data)

    def send_tool_execute(self, tool_name: str, arguments: dict) -> None:
        self._raise_if_stopped()

        data = {
            "type": "executing_tool",
            "tool_name": tool_name,
            "arguments": arguments,
            "message": f"executing tool: {tool_name}",
        }

        with self._lock:
            self.pending_tool_request = None
            self.current_status = data

        self._broadcast("notification", data)

    def send_tool_result(self, tool_name: str, arguments: dict, output: str) -> None:
        self._raise_if_stopped()

        data = {
            "type": "tool_result",
            "tool_name": tool_name,
            "arguments": arguments,
            "output": output,
        }

        with self._lock:
            self.pending_tool_request = None
            self.tool_history.append(data)
            self.tool_history = self.tool_history[-20:]

        self._broadcast("tool_result", data)

    def send_error(self, message: str) -> None:
        self.fail_run(message)
        self._broadcast(
            "error",
            {
                "type": "error",
                "message": message,
            },
        )

    def send_message(self, message: dict) -> None:
        self._broadcast(
            "message",
            {
                "type": "message",
                "message": message,
            },
        )

    def send_message_close(self) -> None:
        self._raise_if_stopped()

        with self._lock:
            self.partial_response = ""

        self._broadcast(
            "message_close",
            {
                "type": "message_close",
            },
        )

    def send_done(self) -> None:
        self._raise_if_stopped()

        with self._lock:
            self.is_running = False
            self.is_done = True
            self.current_status = None
            self.pending_tool_request = None
            self.tool_history = []
            self.partial_response = ""

        self._broadcast(
            "done",
            {
                "type": "done",
            },
        )