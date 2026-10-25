from fastapi import APIRouter, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from app.data_access import AuthService

router = APIRouter(prefix="/user", tags=["user"])

bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------
# Schemas
# ---------------------------

class UpdateSystemPromptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Nuevo system prompt del usuario",
        examples=["Eres un asistente técnico muy conciso y preciso."],
    )


class SystemPromptResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(..., description="System prompt actual del usuario")


class OkResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(..., description="Resultado de la operación")


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: str


# ---------------------------
# Helpers
# ---------------------------

def _get_user_from_token(access_token: str):
    user = AuthService.get_user_by_token(access_token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )
    return user


def _require_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> str:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    return credentials.credentials


# ---------------------------
# Endpoints
# ---------------------------

@router.put(
    "/system-prompt",
    response_model=OkResponse,
    summary="Actualizar system prompt del usuario",
    description=(
        "Actualiza el system prompt del usuario autenticado. "
        "El nuevo prompt se envía en el body JSON de la petición. "
        "Requiere Authorization: Bearer <token>."
    ),
    responses={
        200: {"model": OkResponse, "description": "System prompt actualizado correctamente"},
        401: {"model": ErrorResponse, "description": "Falta token o token inválido"},
        422: {"model": ErrorResponse, "description": "Payload inválido"},
    },
)
async def change_system_prompt(
    payload: UpdateSystemPromptRequest,
    bearer_token: str = Security(_require_bearer_token),
):
    user = _get_user_from_token(bearer_token)
    user.set_system_prompt(payload.prompt)
    return OkResponse(status="ok")


@router.get(
    "/system-prompt",
    response_model=SystemPromptResponse,
    summary="Obtener system prompt del usuario",
    description=(
        "Obtiene el system prompt actual del usuario autenticado. "
        "Requiere Authorization: Bearer <token>."
    ),
    responses={
        200: {"model": SystemPromptResponse, "description": "System prompt obtenido correctamente"},
        401: {"model": ErrorResponse, "description": "Falta token o token inválido"},
    },
)
async def get_system_prompt(
    bearer_token: str = Security(_require_bearer_token),
):
    user = _get_user_from_token(bearer_token)

    prompt_value = user.system_prompt
    if prompt_value is None:
        prompt_value = ""
    elif not isinstance(prompt_value, str):
        prompt_value = str(prompt_value)

    return SystemPromptResponse(prompt=prompt_value)