from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.services.brain_service.memory_structure import (
    DecisionStatus,
    FactSource,
    MemoryArtifact,
    MemoryAttribute,
    MemoryConstraint,
    MemoryEntity,
    MemoryFact,
    MemoryStatus,
    MemoryTaskState,
    PreferenceStability,
    Priority,
)


class PatchOp(str, Enum):
    add = "add"
    update = "update"
    remove = "remove"


class SummaryPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    replace: str | None = Field(
        None,
        description="Nuevo summary_for_reentry. Null si no cambia.",
    )


class TaskPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_goal: str | None = None
    current_topic: str | None = None
    task_status: MemoryStatus | None = None
    active_subtasks: list[str] | None = None
    next_steps: list[str] | None = None
    success_criteria: list[str] | None = None
    blocked_by: list[str] | None = None


class FactAdd(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    source: FactSource
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    expires_after_turns: int | None = Field(None, ge=1)


class FactUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., ge=1)
    text: str | None = None
    source: FactSource | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    expires_after_turns: int | None = Field(None, ge=1)


class FactPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: PatchOp
    add: FactAdd | None = None
    update: FactUpdate | None = None
    remove_id: int | None = Field(None, ge=1)


class EntityAdd(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    name: str
    attributes: list[MemoryAttribute] = Field(default_factory=list)
    source: FactSource


class EntityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., ge=1)
    type: str | None = None
    name: str | None = None
    attributes: list[MemoryAttribute] | None = None
    source: FactSource | None = None


class EntityPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: PatchOp
    add: EntityAdd | None = None
    update: EntityUpdate | None = None
    remove_id: int | None = Field(None, ge=1)


class DecisionAdd(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str
    rationale: str | None = None
    status: DecisionStatus = DecisionStatus.active
    source: FactSource


class DecisionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., ge=1)
    decision: str | None = None
    rationale: str | None = None
    status: DecisionStatus | None = None
    source: FactSource | None = None


class DecisionPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: PatchOp
    add: DecisionAdd | None = None
    update: DecisionUpdate | None = None
    remove_id: int | None = Field(None, ge=1)


class QuestionAdd(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str
    priority: Priority = Priority.medium
    blocking: bool = False
    owner: str = "assistant"


class QuestionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., ge=1)
    question: str | None = None
    priority: Priority | None = None
    blocking: bool | None = None
    owner: str | None = None


class QuestionPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: PatchOp
    add: QuestionAdd | None = None
    update: QuestionUpdate | None = None
    remove_id: int | None = Field(None, ge=1)


class ConstraintAdd(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    priority: Priority = Priority.high
    source: FactSource


class ConstraintUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., ge=1)
    text: str | None = None
    priority: Priority | None = None
    source: FactSource | None = None


class ConstraintPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: PatchOp
    add: ConstraintAdd | None = None
    update: ConstraintUpdate | None = None
    remove_id: int | None = Field(None, ge=1)


class PreferenceAdd(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    value: str
    stability: PreferenceStability
    source: FactSource


class PreferenceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., ge=1)
    key: str | None = None
    value: str | None = None
    stability: PreferenceStability | None = None
    source: FactSource | None = None


class PreferencePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: PatchOp
    add: PreferenceAdd | None = None
    update: PreferenceUpdate | None = None
    remove_id: int | None = Field(None, ge=1)


class ArtifactAdd(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    name: str
    value: str | None = None


class ArtifactUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., ge=1)
    type: str | None = None
    name: str | None = None
    value: str | None = None


class ArtifactPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: PatchOp
    add: ArtifactAdd | None = None
    update: ArtifactUpdate | None = None
    remove_id: int | None = Field(None, ge=1)


class RisksPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    replace: list[str] | None = None


class MemoryPatchPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field("2.1", description="Versión del schema de patch.")
    summary: SummaryPatch | None = None
    task: TaskPatch | None = None

    facts: list[FactPatch] = Field(default_factory=list)
    entities: list[EntityPatch] = Field(default_factory=list)
    decisions: list[DecisionPatch] = Field(default_factory=list)
    open_questions: list[QuestionPatch] = Field(default_factory=list)
    constraints: list[ConstraintPatch] = Field(default_factory=list)
    preferences: list[PreferencePatch] = Field(default_factory=list)
    artifacts: list[ArtifactPatch] = Field(default_factory=list)

    risks: RisksPatch | None = None