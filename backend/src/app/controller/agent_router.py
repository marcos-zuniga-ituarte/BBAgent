import asyncio
import mimetypes

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Path, Request, Security, UploadFile, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.data_access import AuthService
from app.services.command_approval_manager import approval_manager
from app.services.god_service.angel_status import sse_event
from app.services.god_service.god_service import god

router = APIRouter(prefix="/chat", tags=["agent"])

bearer_scheme = HTTPBearer(auto_error=False)


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

def _resolve_mime_type(filename: str) -> str:
    guessed_type, _ = mimetypes.guess_type(filename)
    if guessed_type:
        return guessed_type

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    fallback_map = {
        "md": "text/markdown",
        "txt": "text/plain",
        "json": "application/json",
        "csv": "text/csv",
        "html": "text/html",
        "xml": "application/xml",
        "yaml": "application/x-yaml",
        "yml": "application/x-yaml",
    }

    return fallback_map.get(ext, "text/plain")

@router.post(
    "/runs/{chat_id}",
    summary="Iniciar ejecución de chat",
    description=(
        "Inicia una ejecución para un chat. "
        "Requiere Authorization: Bearer <token>."
    ),
)
async def chat_stream(
    request: Request,
    chat_id: str = Path(..., description="ID del chat"),
    message: Annotated[str | None, Form()] = None,
    askForConfirmation: Annotated[int, Form()] = 0,
    audio: UploadFile | None = File(default=None),
    files: list[UploadFile] | None = File(default=None),
    bearer_token: str = Security(_require_bearer_token),
):
    if askForConfirmation not in (0, 1, 2):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="askForConfirmation must be 0, 1 or 2",
        )

    user = _get_user_from_token(bearer_token)

    chat = user.get_chat(chat_id)
    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    audio_bytes = None
    audio_filename = None

    if audio is not None:
        if not audio.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Audio filename is required",
            )
        audio_filename = audio.filename
        audio_bytes = await audio.read()

    uploaded_files = []

    if files:
        for file in files:
            if not file.filename:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Each file must have a filename",
                )

            file_bytes = await file.read()
            mime_type = _resolve_mime_type(file.filename)

            uploaded_files.append(
                {
                    "filename": file.filename,
                    "bytes": file_bytes,
                    "mime_type": mime_type,
                }
            )

    if not message and not audio and not uploaded_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must send message, audio, or files",
        )

    approval_manager.create_session(chat_id)

    started = god.start(
        user=user,
        chat=chat,
        ask_for_confirmation=askForConfirmation,
        texto_usuario=message,
        session_id=chat_id,
        audio_bytes=audio_bytes,
        audio_filename=audio_filename,
        files=uploaded_files,
    )

    if not started:
        approval_manager.remove_session(chat_id)
        return {
            "status": "already_running",
            "chat_id": chat.id,
        }

    return {
        "status": "started",
        "chat_id": chat.id,
    }


@router.get(
    "/subscribe/{chat_id}",
    summary="Suscribirse al stream SSE de un chat",
    description=(
        "Abre el stream SSE de un chat autenticado. "
        "Requiere Authorization: Bearer <token>."
    ),
)
async def subscribe_chat(
    request: Request,
    chat_id: str = Path(..., description="ID del chat"),
    bearer_token: str = Security(_require_bearer_token),
):
    user = _get_user_from_token(bearer_token)

    chat = user.get_chat(chat_id)
    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    async def event_generator():
        _status, subscriber = god.attach(chat)

        try:
            yield sse_event(
                {"type": "start", "chat_id": chat_id},
                event="start",
            )

            while True:
                if await request.is_disconnected():
                    break

                item = await asyncio.to_thread(subscriber.queue.get)

                if item is None:
                    break

                if not isinstance(item, dict):
                    yield sse_event(
                        {"type": "error", "message": "Invalid SSE payload"},
                        event="error",
                    )
                    break

                event = item.get("event", "message")
                data = item.get("data", {})

                yield sse_event(data, event=event)

        finally:
            god.detach(chat_id, subscriber.id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/runs/{chat_id}/stop",
    summary="Solicitar parada de una ejecución de chat",
)
async def stop_chat(
    request: Request,
    chat_id: str = Path(..., description="ID del chat"),
    bearer_token: str = Security(_require_bearer_token),
):
    user = _get_user_from_token(bearer_token)

    chat = user.get_chat(chat_id)
    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    ok = god.request_stop(chat_id, reason="Stopped by user")
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat status not found",
        )

    return {
        "status": "stop_requested",
        "chat_id": chat_id,
    }

@router.get(
    "/{chat_id}/messages",
    summary="Obtener mensajes de un chat",
)
async def get_messages(
    request: Request,
    chat_id: str = Path(..., description="ID de la sesión/chat"),
    bearer_token: str = Security(_require_bearer_token),
):
    user = _get_user_from_token(bearer_token)

    chat = user.get_chat(chat_id)
    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    return chat.get_messages_for_ui()


@router.get(
    "",
    summary="Listar chats del usuario",
)
async def get_chats(
    request: Request,
    bearer_token: str = Security(_require_bearer_token),
):
    user = _get_user_from_token(bearer_token)
    return user.get_chats()


@router.post(
    "",
    summary="Crear un nuevo chat",
)
async def create_chat(
    request: Request,
    bearer_token: str = Security(_require_bearer_token),
):
    user = _get_user_from_token(bearer_token)
    return user.create_chat().id