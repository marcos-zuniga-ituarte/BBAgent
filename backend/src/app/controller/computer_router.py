from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.data_access import AuthService
from app.modules.computer.computer_service import (
    NoComputerClient,
    PendingScreenshotError,
    PendingComputerCallError,
    computer_session_service,
)

router = APIRouter(prefix="/computer", tags=["computer"])

bearer_scheme = HTTPBearer(auto_error=False)


class ScreenshotResultBody(BaseModel):
    ok: bool = Field(..., description="Indica si la captura fue correcta")
    error: str | None = Field(default=None, description="Mensaje de error si falló")
    image_base64: str = Field(default="", description="Imagen codificada en base64")


class HeartbeatRequest(BaseModel):
    busy: bool = Field(default=False, description="Indica si el cliente está ocupado")


class ComputerResultRequest(BaseModel):
    result: dict = Field(..., description="Resultado libre de la ejecución remota")


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
    summary="Abrir stream SSE del cliente computer",
    description="Abre el stream SSE para la sesión remota autenticada.",
    responses={
        200: {"description": "Stream SSE abierto correctamente"},
        401: {"model": ErrorResponse, "description": "Token inválido o ausente"},
    },
)
async def open_computer_stream(user=Depends(get_current_user)):
    return StreamingResponse(
        computer_session_service.stream_generator(str(user.id)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/heartbeat",
    response_model=OkResponse,
    summary="Registrar heartbeat del cliente computer",
    description="Actualiza el estado de vida del cliente remoto.",
    responses={
        200: {"model": OkResponse, "description": "Heartbeat registrado"},
        401: {"model": ErrorResponse, "description": "Token inválido o ausente"},
    },
)
async def register_heartbeat(payload: HeartbeatRequest, user=Depends(get_current_user)):
    computer_session_service.register_pong(
        user_id=str(user.id),
        busy=payload.busy,
    )
    return OkResponse(result="ok")


@router.post(
    "/actions/result",
    response_model=OkResponse,
    summary="Enviar resultado de acción remota",
    description=(
        "Recibe el resultado de una acción remota. "
        "El campo result se mantiene libre para no romper contratos internos."
    ),
    responses={
        200: {"model": OkResponse, "description": "Resultado aceptado"},
        401: {"model": ErrorResponse, "description": "Token inválido o ausente"},
        409: {"model": ErrorResponse, "description": "No hay ejecución pendiente"},
    },
)
async def submit_computer_result(payload: ComputerResultRequest, user=Depends(get_current_user)):
    ok = computer_session_service.submit_result(
        user_id=str(user.id),
        result=payload.result,
    )

    if not ok:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No hay ejecución pendiente para este usuario",
        )

    return OkResponse(result="ok")


@router.post(
    "/screenshots/result",
    response_model=OkResponse,
    summary="Enviar resultado de screenshot",
    description=(
        "Recibe el resultado de un screenshot pendiente. "
        "Se mantiene exactamente el contrato interno: ok, error e image_base64."
    ),
    responses={
        200: {"model": OkResponse, "description": "Screenshot aceptado"},
        401: {"model": ErrorResponse, "description": "Token inválido o ausente"},
        409: {"model": ErrorResponse, "description": "No hay screenshot pendiente"},
    },
)
async def submit_screenshot_result(payload: ScreenshotResultBody, user=Depends(get_current_user)):
    ok = computer_session_service.submit_screenshot(
        user_id=str(user.id),
        screenshot_data={
            "ok": payload.ok,
            "error": payload.error,
            "image_base64": payload.image_base64,
        },
    )

    if not ok:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No hay screenshot pendiente para este usuario",
        )

    return OkResponse(result="ok")