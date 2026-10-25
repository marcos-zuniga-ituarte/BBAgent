import threading
from typing import Optional


class ApprovalSession:
    def __init__(self) -> None:
        self.event = threading.Event()
        self.decision: Optional[bool] = None


class ApprovalManager:
    def __init__(self) -> None:
        self._sessions: dict[str, ApprovalSession] = {}
        self._lock = threading.Lock()

    def create_session(self, session_id: str) -> None:
        with self._lock:
            self._sessions[session_id] = ApprovalSession()

    def submit_decision(self, session_id: str, decision: bool) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False

            session.decision = decision
            session.event.set()
            return True

    def wait_for_decision(
        self,
        session_id: str,
        timeout_seconds: Optional[float] = None,
    ) -> Optional[bool]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            event = session.event

        finished = event.wait(timeout=timeout_seconds)
        if not finished:
            return None

        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            decision = session.decision
            session.decision = None
            session.event.clear()
            return decision

    def remove_session(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)


approval_manager = ApprovalManager()