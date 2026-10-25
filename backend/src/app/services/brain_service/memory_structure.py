from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class MemoryStatus(str, Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    blocked = "blocked"
    waiting_user = "waiting_user"
    completed = "completed"


class FactSource(str, Enum):
    user_explicit = "user_explicit"
    assistant_inferred = "assistant_inferred"
    tool_observed = "tool_observed"
    system_defined = "system_defined"


class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class DecisionStatus(str, Enum):
    proposed = "proposed"
    active = "active"
    superseded = "superseded"
    rejected = "rejected"


class PreferenceStability(str, Enum):
    session = "session"
    persistent = "persistent"


class MemoryFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., ge=1, description="Identificador estable del hecho.")
    text: str = Field(
        ...,
        description="Hecho relevante, atómico y reutilizable de la conversación.",
    )
    source: FactSource = Field(..., description="Origen del hecho.")
    confidence: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description="Confianza en el hecho.",
    )
    expires_after_turns: int | None = Field(
        None,
        ge=1,
        description="Turnos tras los que podría dejar de ser relevante.",
    )


class MemoryAttribute(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(..., description="Nombre del atributo.")
    value: str = Field(..., description="Valor del atributo.")


class MemoryEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., ge=1, description="Identificador estable de la entidad.")
    type: str = Field(..., description="Tipo de entidad.")
    name: str = Field(..., description="Nombre canónico y estable.")
    attributes: list[MemoryAttribute] = Field(
        default_factory=list,
        description="Atributos estructurados de la entidad.",
    )
    source: FactSource = Field(..., description="Origen de la entidad.")


class MemoryDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., ge=1, description="Identificador estable de la decisión.")
    decision: str = Field(..., description="Decisión tomada.")
    rationale: str | None = Field(None, description="Motivo breve.")
    status: DecisionStatus = Field(
        DecisionStatus.active,
        description="Estado actual de la decisión.",
    )
    source: FactSource = Field(..., description="Origen de la decisión.")


class MemoryQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., ge=1, description="Identificador estable de la pregunta.")
    question: str = Field(..., description="Pregunta abierta o dependencia pendiente.")
    priority: Priority = Field(Priority.medium, description="Prioridad.")
    blocking: bool = Field(False, description="Si bloquea el avance.")
    owner: str = Field("assistant", description="Quién debería resolverla.")


class MemoryPreference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., ge=1, description="Identificador estable de la preferencia.")
    key: str = Field(..., description="Clave corta de la preferencia.")
    value: str = Field(..., description="Valor de la preferencia.")
    stability: PreferenceStability = Field(..., description="Persistencia.")
    source: FactSource = Field(..., description="Origen de la preferencia.")


class MemoryConstraint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., ge=1, description="Identificador estable de la restricción.")
    text: str = Field(..., description="Restricción o requisito.")
    priority: Priority = Field(Priority.high, description="Importancia.")
    source: FactSource = Field(..., description="Origen de la restricción.")


class MemoryArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., ge=1, description="Identificador estable del artefacto.")
    type: str = Field(..., description="Tipo de artefacto.")
    name: str = Field(..., description="Nombre corto y estable.")
    value: str | None = Field(None, description="Ruta, id o referencia textual.")


class MemoryTaskState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_goal: str = Field(..., description="Objetivo actual del usuario.")
    current_topic: str = Field(..., description="Tema principal actual.")
    task_status: MemoryStatus = Field(..., description="Estado operativo.")
    active_subtasks: list[str] = Field(default_factory=list, description="Subtareas activas.")
    next_steps: list[str] = Field(default_factory=list, description="Siguientes pasos.")
    success_criteria: list[str] = Field(default_factory=list, description="Criterios de éxito.")
    blocked_by: list[str] = Field(default_factory=list, description="Bloqueos actuales.")


class ConversationMemory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field("2.1", description="Versión del schema.")
    next_id: int = Field(
        1,
        ge=1,
        description="Siguiente ID interno disponible para items nuevos.",
    )
    summary_for_reentry: str = Field(
        ...,
        description="Resumen corto para reenganchar al modelo.",
    )
    task: MemoryTaskState = Field(..., description="Estado operativo actual.")
    facts: list[MemoryFact] = Field(default_factory=list, description="Hechos.")
    entities: list[MemoryEntity] = Field(default_factory=list, description="Entidades.")
    decisions: list[MemoryDecision] = Field(default_factory=list, description="Decisiones.")
    open_questions: list[MemoryQuestion] = Field(default_factory=list, description="Preguntas abiertas.")
    constraints: list[MemoryConstraint] = Field(default_factory=list, description="Restricciones.")
    preferences: list[MemoryPreference] = Field(default_factory=list, description="Preferencias.")
    risks: list[str] = Field(default_factory=list, description="Riesgos y ambigüedades.")
    artifacts: list[MemoryArtifact] = Field(default_factory=list, description="Artefactos útiles.")