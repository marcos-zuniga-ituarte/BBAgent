import threading

from app.services.god_service.angel_service import Angel
from app.services.god_service.angel_status import AngelStatus
from app.services.command_approval_manager import approval_manager


class God:
    def __init__(self):
        self._lock = threading.RLock()
        self._executing: set[str] = set()
        self._statuses: dict[str, AngelStatus] = {}

    def get_or_create_status(self, chat) -> AngelStatus:
        with self._lock:
            status = self._statuses.get(chat.id)
            if status is None:
                status = AngelStatus(chat)
                self._statuses[chat.id] = status
            return status

    def attach(self, chat):
        status = self.get_or_create_status(chat)
        subscriber = status.attach()
        return status, subscriber

    def detach(self, chat_id: str, subscriber_id: str) -> None:
        with self._lock:
            status = self._statuses.get(chat_id)

        if status is not None:
            status.detach(subscriber_id)

    def _mark_executing(self, angel_id: str) -> bool:
        with self._lock:
            if angel_id in self._executing:
                return False
            self._executing.add(angel_id)
            return True

    def _unmark_executing(self, angel_id: str) -> None:
        with self._lock:
            self._executing.discard(angel_id)

    def _run_angel(self, angel: Angel, session_id: str | None = None) -> None:
        angel_id = angel.get_id()

        try:
            angel.execute()
        except Exception as e:
            angel.sender.send_error(str(e))
        finally:
            if session_id is not None:
                approval_manager.remove_session(session_id)
            self._unmark_executing(angel_id)

    def start(
            self,
            user,
            chat,
            ask_for_confirmation: int,
            texto_usuario: str | None,
            session_id: str | None = None,
            system_prompt_list=None,
            audio_bytes: bytes | None = None,
            audio_filename: str | None = None,
            files: list[dict] | None = None,
    ) -> bool:
        status_obj = self.get_or_create_status(chat)

        angel = Angel(
            user=user,
            chat=chat,
            sender=status_obj,
            ask_for_confirmation=ask_for_confirmation,
            texto_usuario=texto_usuario,
            system_prompt_list=system_prompt_list,
            audio_bytes=audio_bytes,
            audio_filename=audio_filename,
            files=files,
        )

        angel_id = angel.get_id()
        if not self._mark_executing(angel_id):
            return False

        thread = threading.Thread(
            target=self._run_angel,
            args=(angel, session_id),
            daemon=True,
        )
        thread.start()

        return True

    def request_stop(self, chat_id: str, reason: str = "Stopped by user") -> bool:
        with self._lock:
            status = self._statuses.get(chat_id)

        if status is None:
            return False

        status.request_stop(reason)
        return True

    def is_stop_requested(self, chat_id: str) -> bool:
        with self._lock:
            status = self._statuses.get(chat_id)

        if status is None:
            return False

        return status.should_stop()


god = God()