from fastapi import APIRouter, HTTPException, Path, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.data_access import AuthService
from app.services.command_approval_manager import approval_manager

router = APIRouter(prefix="/tool-approval", tags=["tool-approval"])

bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------
# Schemas
# ---------------------------

class ToolApprovalDecisionRequest(BaseModel):
    decision: bool = Field(
        ...,
        description="Decisión del usuario sobre la petición de aprobación",
        examples=[True],
    )


class ToolApprovalDecisionResponse(BaseModel):
    status: str = Field(..., description="Resultado de la operación")
    session_id: str = Field(..., description="ID de la sesión/chat")
    decision: bool = Field(..., description="Decisión registrada")


class ErrorResponse(BaseModel):
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

@router.post(
    "/sessions/{session_id}/response",
    response_model=ToolApprovalDecisionResponse,
    summary="Responder a una petición de aprobación de herramienta",
    description=(
        "Registra la decisión del usuario sobre una petición de aprobación pendiente. "
        "La decisión se envía en el body JSON de la petición. "
        "Requiere Authorization: Bearer <token>."
    ),
    responses={
        200: {"model": ToolApprovalDecisionResponse, "description": "Decisión registrada correctamente"},
        401: {"model": ErrorResponse, "description": "Falta token o token inválido"},
        404: {"model": ErrorResponse, "description": "Chat no encontrado o no hay aprobación pendiente"},
        422: {"model": ErrorResponse, "description": "Payload inválido"},
    },
)
async def command_response(
    payload: ToolApprovalDecisionRequest,
    session_id: str = Path(..., description="ID de la sesión/chat"),
    bearer_token: str = Security(_require_bearer_token),
):
    user = _get_user_from_token(bearer_token)

    chat = user.get_chat(session_id)
    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    ok = approval_manager.submit_decision(session_id, payload.decision)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pending approval session for this chat",
        )

    return ToolApprovalDecisionResponse(
        status="ok",
        session_id=session_id,
        decision=payload.decision,
    )