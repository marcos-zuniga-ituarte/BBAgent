import json
import os
import threading
from typing import Any

from pydantic import ValidationError

from app.data_access import Chat
from app.modules.llm.llm import llm
from app.modules.llm.prompt_manager import PromptManager
from app.services.brain_service.memory_structure import ConversationMemory
from app.services.brain_service.memory_patch_structure import MemoryPatchPlan
from app.services.brain_service.memory_patch_apply import apply_memory_patch

model_memory = os.getenv("OPENAI_MEMORY_MODEL")
prompt_memory = os.getenv("MEMORY_PROMPT")
prompt_memory_full_rebuild = os.getenv("MEMORY_PROMPT_FULL_REBUILD")

context_history_runs = int(os.environ.get("CONTEXT_HISTORY_RUNS"))


class BrainService:
    def __init__(self, chat: Chat) -> None:
        self.chat = chat
        self._memory_thread: threading.Thread | None = None
        self._memory_exception: Exception | None = None
        self._context = []

    def start(self):
        last_message = self.chat.get_last_message().id
        context, messages_to_summarize = self.chat.get_messages_partitioned_for_openai(
            last_message, context_history_runs
        )
        self._context = self.get_memory_for_response() + context
        self.start_memory_update(messages_to_summarize)

    def get_context(self):
        return self._context

    def add_message(self, message_response, show=False):
        msg = self.chat.add_message(message_response, show=show)
        self._context.append(message_response)
        return msg

    def add_messages(self, messages_responses):
        self.chat.add_messages(messages_responses)
        self._context += messages_responses

    def _build_empty_memory(self) -> ConversationMemory:
        return ConversationMemory(
            summary_for_reentry="Conversación iniciada recientemente.",
            task={
                "user_goal": "",
                "current_topic": "",
                "task_status": "not_started",
                "active_subtasks": [],
                "next_steps": [],
                "success_criteria": [],
                "blocked_by": [],
            },
            facts=[],
            entities=[],
            decisions=[],
            open_questions=[],
            constraints=[],
            preferences=[],
            risks=[],
            artifacts=[],
        )

    def _load_memory(self) -> ConversationMemory | None:
        raw_memory = self.chat.get_memory()
        if not raw_memory:
            return None

        try:
            return ConversationMemory.model_validate(raw_memory)
        except Exception:
            return None

    def _normalize_memory(self, memory: ConversationMemory) -> ConversationMemory:
        def dedupe_by_key(items, key_fn):
            seen = set()
            result = []

            for item in items:
                key = key_fn(item)
                if key in seen:
                    continue
                seen.add(key)
                result.append(item)

            return result

        memory.entities = dedupe_by_key(
            memory.entities,
            lambda x: (x.type.strip().lower(), x.name.strip().lower()),
        )

        memory.preferences = dedupe_by_key(
            memory.preferences,
            lambda x: x.key.strip().lower(),
        )

        memory.constraints = dedupe_by_key(
            memory.constraints,
            lambda x: x.text.strip().lower(),
        )

        memory.facts = dedupe_by_key(
            memory.facts,
            lambda x: x.text.strip().lower(),
        )

        memory.decisions = dedupe_by_key(
            memory.decisions,
            lambda x: x.decision.strip().lower(),
        )

        memory.open_questions = dedupe_by_key(
            memory.open_questions,
            lambda x: x.question.strip().lower(),
        )

        memory.artifacts = dedupe_by_key(
            memory.artifacts,
            lambda x: (
                x.type.strip().lower(),
                x.name.strip().lower(),
                (x.value or "").strip().lower(),
            ),
        )

        memory.risks = list(dict.fromkeys(r.strip() for r in memory.risks if r.strip()))

        memory.facts = memory.facts[:12]
        memory.entities = memory.entities[:12]
        memory.decisions = memory.decisions[:8]
        memory.open_questions = memory.open_questions[:8]
        memory.constraints = memory.constraints[:8]
        memory.preferences = memory.preferences[:8]
        memory.risks = memory.risks[:6]
        memory.artifacts = memory.artifacts[:10]

        return ConversationMemory.model_validate(memory.model_dump(mode="json"))

    def _dump_compact(self, data: dict) -> str:
        return json.dumps(
            data,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    def _build_memory_for_response(self, memory: ConversationMemory) -> dict[str, Any]:
        return {
            "summary": memory.summary_for_reentry,
            "task": {
                "user_goal": memory.task.user_goal,
                "current_topic": memory.task.current_topic,
                "task_status": memory.task.task_status,
                "active_subtasks": memory.task.active_subtasks[:4],
                "next_steps": memory.task.next_steps[:4],
                "blocked_by": memory.task.blocked_by[:3],
            },
            "entities": [
                {
                    "type": e.type,
                    "name": e.name,
                    "attributes": [{"key": a.key, "value": a.value} for a in e.attributes[:3]],
                }
                for e in memory.entities[:6]
            ],
            "constraints": [c.text for c in memory.constraints[:4]],
            "preferences": [{"key": p.key, "value": p.value} for p in memory.preferences[:4]],
            "decisions": [d.decision for d in memory.decisions[:4]],
            "open_questions": [q.question for q in memory.open_questions[:3]],
            "facts": [f.text for f in memory.facts[:4]],
            "risks": memory.risks[:4],
            "artifacts": [
                {"type": a.type, "name": a.name, "value": a.value}
                for a in memory.artifacts[:5]
            ],
        }

    def get_memory_for_response(self) -> list[dict[str, str]]:
        memory = self._load_memory()
        if memory is None:
            return []
        return [{
            "role": "system",
            "content": "Memoria útil previa:\n" + self._dump_compact(
                self._build_memory_for_response(memory)
            ),
        }]

    def get_memory_for_update(self) -> list[dict[str, str]]:
        memory = self._load_memory()
        if memory is None:
            return []
        return [{
            "role": "system",
            "content": "Memoria estructurada actual (JSON):\n" + self._dump_compact(
                memory.model_dump(mode="json", exclude_none=True)
            ),
        }]

    def update_memory(self, messages_to_update: list[dict[str, Any]]) -> None:
        if not messages_to_update:
            return

        current_memory = self._load_memory() or self._build_empty_memory()

        instructions = [
            {
                "role": "system",
                "content": PromptManager.load(prompt_memory),
            },
            *self.get_memory_for_update(),
        ]

        try:
            patch_plan = llm.structured(
                model=model_memory,
                instructions=instructions,
                messages=messages_to_update,
                schema=MemoryPatchPlan,
            )

            if not isinstance(patch_plan, MemoryPatchPlan):
                patch_plan = MemoryPatchPlan.model_validate(patch_plan)

            updated_memory = apply_memory_patch(current_memory, patch_plan)
            updated_memory = self._normalize_memory(updated_memory)

        except ValidationError:
            rebuild_instructions = [
                {
                    "role": "system",
                    "content": PromptManager.load(prompt_memory_full_rebuild),
                },
                *self.get_memory_for_update(),
            ]

            rebuilt_memory = llm.structured(
                model=model_memory,
                instructions=rebuild_instructions,
                messages=messages_to_update,
                schema=ConversationMemory,
            )

            if not isinstance(rebuilt_memory, ConversationMemory):
                rebuilt_memory = ConversationMemory.model_validate(rebuilt_memory)

            updated_memory = self._normalize_memory(rebuilt_memory)

        self.chat.set_memory(updated_memory.model_dump(mode="json"))

    def start_memory_update(self, messages_to_update: list[dict[str, Any]]) -> None:
        if not messages_to_update:
            self._memory_thread = None
            self._memory_exception = None
            return

        if self._memory_thread is not None and self._memory_thread.is_alive():
            raise RuntimeError("Memory update thread is already running.")

        self._memory_exception = None

        def _runner() -> None:
            try:
                self.update_memory(messages_to_update)
            except Exception as e:
                self._memory_exception = e

        self._memory_thread = threading.Thread(
            target=_runner,
            name="brain-memory-update",
            daemon=True,
        )
        self._memory_thread.start()

    def wait_for_memory_update(self) -> None:
        if self._memory_thread is None:
            return

        self._memory_thread.join()

        if self._memory_exception is not None:
            raise self._memory_exception
