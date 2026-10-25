from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.data_access import AuthService
from app.modules.terminal.terminal_service import (
    NoTerminalClient,
    PendingCommandError,
    SessionNotFoundError,
    terminal_session_service,
)

router = APIRouter(prefix="/terminal", tags=["terminal"])

bearer_scheme = HTTPBearer(auto_error=False)


class SessionRef(BaseModel):
    chat_id: str = Field(..., min_length=1)
    created_at: str = Field(..., min_length=1)


class ResultRequest(SessionRef):
    output: str = Field(...)


class ClientSessionInfo(BaseModel):
    chat_id: str = Field(..., min_length=1)
    created_at: str = Field(..., min_length=1)


class HeartbeatRequest(BaseModel):
    sessions: list[ClientSessionInfo] = Field(default_factory=list)


class OkResponse(BaseModel):
    result: str


class ErrorResponse(BaseModel):
    detail: str


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
):
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    user = AuthService.get_user_by_token(credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )
    return user


@router.get(
    "/events/stream",
    summary="Abrir stream SSE del cliente terminal",
    description="Abre el stream SSE para la sesión terminal del usuario autenticado.",
    responses={
        200: {"description": "Stream SSE abierto correctamente"},
        401: {"model": ErrorResponse, "description": "Token inválido o ausente"},
    },
)
async def open_terminal_stream(user=Depends(get_current_user)):
    return StreamingResponse(
        terminal_session_service.stream_generator(user.id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/heartbeat",
    response_model=OkResponse,
    summary="Registrar heartbeat del cliente terminal",
    description="Actualiza el estado del cliente y las sesiones terminal locales activas.",
    responses={
        200: {"model": OkResponse, "description": "Heartbeat registrado"},
        401: {"model": ErrorResponse, "description": "Token inválido o ausente"},
    },
)
async def register_heartbeat(payload: HeartbeatRequest, user=Depends(get_current_user)):
    terminal_session_service.register_pong(
        user_id=user.id,
        client_sessions=[
            {
                "chat_id": item.chat_id,
                "created_at": item.created_at,
            }
            for item in payload.sessions
        ],
    )
    return OkResponse(result="ok")


@router.post(
    "/sessions/result",
    response_model=OkResponse,
    summary="Enviar resultado de comando terminal",
    description=(
        "Recibe el resultado de un comando pendiente. "
        "Se mantiene intacto el contrato interno con terminal_session_service."
    ),
    responses={
        200: {"model": OkResponse, "description": "Resultado aceptado"},
        401: {"model": ErrorResponse, "description": "Token inválido o ausente"},
        409: {"model": ErrorResponse, "description": "No hay comando pendiente para esta sesión"},
    },
)
async def submit_terminal_result(payload: ResultRequest, user=Depends(get_current_user)):
    ok = terminal_session_service.submit_result(
        user_id=user.id,
        chat_id=payload.chat_id,
        created_at=payload.created_at,
        result=payload.output,
    )

    if not ok:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No hay comando pendiente para esta sesión",
        )

    return OkResponse(result="ok")