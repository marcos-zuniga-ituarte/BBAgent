from __future__ import annotations

from copy import deepcopy

from app.services.brain_service.memory_patch_structure import MemoryPatchPlan, PatchOp
from app.services.brain_service.memory_structure import (
    ConversationMemory,
    MemoryArtifact,
    MemoryConstraint,
    MemoryDecision,
    MemoryEntity,
    MemoryFact,
    MemoryPreference,
    MemoryQuestion,
)


def _next_id(memory: ConversationMemory) -> int:
    new_id = memory.next_id
    memory.next_id += 1
    return new_id


def _apply_fact_patches(memory: ConversationMemory, patches):
    by_id = {item.id: item for item in memory.facts}

    for patch in patches:
        if patch.op == PatchOp.remove and patch.remove_id is not None:
            by_id.pop(patch.remove_id, None)

        elif patch.op == PatchOp.update and patch.update is not None:
            item = by_id.get(patch.update.id)
            if item is None:
                continue
            data = item.model_dump(mode="json")
            update = patch.update.model_dump(exclude_none=True, mode="json")
            update.pop("id", None)
            data.update(update)
            by_id[item.id] = MemoryFact.model_validate(data)

        elif patch.op == PatchOp.add and patch.add is not None:
            data = patch.add.model_dump(mode="json")
            data["id"] = _next_id(memory)
            item = MemoryFact.model_validate(data)
            by_id[item.id] = item

    memory.facts = list(by_id.values())


def _apply_entity_patches(memory: ConversationMemory, patches):
    by_id = {item.id: item for item in memory.entities}

    for patch in patches:
        if patch.op == PatchOp.remove and patch.remove_id is not None:
            by_id.pop(patch.remove_id, None)

        elif patch.op == PatchOp.update and patch.update is not None:
            item = by_id.get(patch.update.id)
            if item is None:
                continue
            data = item.model_dump(mode="json")
            update = patch.update.model_dump(exclude_none=True, mode="json")
            update.pop("id", None)
            data.update(update)
            by_id[item.id] = MemoryEntity.model_validate(data)

        elif patch.op == PatchOp.add and patch.add is not None:
            data = patch.add.model_dump(mode="json")
            data["id"] = _next_id(memory)
            item = MemoryEntity.model_validate(data)
            by_id[item.id] = item

    memory.entities = list(by_id.values())


def _apply_decision_patches(memory: ConversationMemory, patches):
    by_id = {item.id: item for item in memory.decisions}

    for patch in patches:
        if patch.op == PatchOp.remove and patch.remove_id is not None:
            by_id.pop(patch.remove_id, None)

        elif patch.op == PatchOp.update and patch.update is not None:
            item = by_id.get(patch.update.id)
            if item is None:
                continue
            data = item.model_dump(mode="json")
            update = patch.update.model_dump(exclude_none=True, mode="json")
            update.pop("id", None)
            data.update(update)
            by_id[item.id] = MemoryDecision.model_validate(data)

        elif patch.op == PatchOp.add and patch.add is not None:
            data = patch.add.model_dump(mode="json")
            data["id"] = _next_id(memory)
            item = MemoryDecision.model_validate(data)
            by_id[item.id] = item

    memory.decisions = list(by_id.values())


def _apply_question_patches(memory: ConversationMemory, patches):
    by_id = {item.id: item for item in memory.open_questions}

    for patch in patches:
        if patch.op == PatchOp.remove and patch.remove_id is not None:
            by_id.pop(patch.remove_id, None)

        elif patch.op == PatchOp.update and patch.update is not None:
            item = by_id.get(patch.update.id)
            if item is None:
                continue
            data = item.model_dump(mode="json")
            update = patch.update.model_dump(exclude_none=True, mode="json")
            update.pop("id", None)
            data.update(update)
            by_id[item.id] = MemoryQuestion.model_validate(data)

        elif patch.op == PatchOp.add and patch.add is not None:
            data = patch.add.model_dump(mode="json")
            data["id"] = _next_id(memory)
            item = MemoryQuestion.model_validate(data)
            by_id[item.id] = item

    memory.open_questions = list(by_id.values())


def _apply_constraint_patches(memory: ConversationMemory, patches):
    by_id = {item.id: item for item in memory.constraints}

    for patch in patches:
        if patch.op == PatchOp.remove and patch.remove_id is not None:
            by_id.pop(patch.remove_id, None)

        elif patch.op == PatchOp.update and patch.update is not None:
            item = by_id.get(patch.update.id)
            if item is None:
                continue
            data = item.model_dump(mode="json")
            update = patch.update.model_dump(exclude_none=True, mode="json")
            update.pop("id", None)
            data.update(update)
            by_id[item.id] = MemoryConstraint.model_validate(data)

        elif patch.op == PatchOp.add and patch.add is not None:
            data = patch.add.model_dump(mode="json")
            data["id"] = _next_id(memory)
            item = MemoryConstraint.model_validate(data)
            by_id[item.id] = item

    memory.constraints = list(by_id.values())


def _apply_preference_patches(memory: ConversationMemory, patches):
    by_id = {item.id: item for item in memory.preferences}

    for patch in patches:
        if patch.op == PatchOp.remove and patch.remove_id is not None:
            by_id.pop(patch.remove_id, None)

        elif patch.op == PatchOp.update and patch.update is not None:
            item = by_id.get(patch.update.id)
            if item is None:
                continue
            data = item.model_dump(mode="json")
            update = patch.update.model_dump(exclude_none=True, mode="json")
            update.pop("id", None)
            data.update(update)
            by_id[item.id] = MemoryPreference.model_validate(data)

        elif patch.op == PatchOp.add and patch.add is not None:
            data = patch.add.model_dump(mode="json")
            data["id"] = _next_id(memory)
            item = MemoryPreference.model_validate(data)
            by_id[item.id] = item

    memory.preferences = list(by_id.values())


def _apply_artifact_patches(memory: ConversationMemory, patches):
    by_id = {item.id: item for item in memory.artifacts}

    for patch in patches:
        if patch.op == PatchOp.remove and patch.remove_id is not None:
            by_id.pop(patch.remove_id, None)

        elif patch.op == PatchOp.update and patch.update is not None:
            item = by_id.get(patch.update.id)
            if item is None:
                continue
            data = item.model_dump(mode="json")
            update = patch.update.model_dump(exclude_none=True, mode="json")
            update.pop("id", None)
            data.update(update)
            by_id[item.id] = MemoryArtifact.model_validate(data)

        elif patch.op == PatchOp.add and patch.add is not None:
            data = patch.add.model_dump(mode="json")
            data["id"] = _next_id(memory)
            item = MemoryArtifact.model_validate(data)
            by_id[item.id] = item

    memory.artifacts = list(by_id.values())


def apply_memory_patch(memory: ConversationMemory, plan: MemoryPatchPlan) -> ConversationMemory:
    memory = ConversationMemory.model_validate(memory.model_dump(mode="json"))

    if plan.summary and plan.summary.replace is not None:
        memory.summary_for_reentry = plan.summary.replace

    if plan.task:
        task_patch = plan.task.model_dump(exclude_none=True, mode="json")
        task_data = memory.task.model_dump(mode="json")
        task_data.update(task_patch)
        memory.task = memory.task.__class__.model_validate(task_data)

    _apply_fact_patches(memory, plan.facts)
    _apply_entity_patches(memory, plan.entities)
    _apply_decision_patches(memory, plan.decisions)
    _apply_question_patches(memory, plan.open_questions)
    _apply_constraint_patches(memory, plan.constraints)
    _apply_preference_patches(memory, plan.preferences)
    _apply_artifact_patches(memory, plan.artifacts)

    if plan.risks and plan.risks.replace is not None:
        memory.risks = plan.risks.replace

    return ConversationMemory.model_validate(memory.model_dump(mode="json"))