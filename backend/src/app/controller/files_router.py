from fastapi import APIRouter, HTTPException, Path, Security, status
from urllib.parse import quote
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.data_access import AuthService
from app.data_access.repositories.stored_file_repository import StoredFileRepository

router = APIRouter(prefix="/files", tags=["files"])

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


@router.get(
    "/{file_id}",
    summary="Descargar un archivo",
    description=(
        "Descarga un archivo del usuario autenticado. "
        "Requiere Authorization: Bearer <token>."
    ),
)
async def download_file(
    file_id: str = Path(..., description="ID del archivo"),
    bearer_token: str = Security(_require_bearer_token),
):
    user = _get_user_from_token(bearer_token)

    stored_file = StoredFileRepository.get_by_id(file_id)
    if stored_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    if stored_file.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    return Response(
        content=stored_file.data,
        media_type=stored_file.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": "attachment; filename*=UTF-8''" + quote(stored_file.filename, safe=""),
            "Content-Length": str(stored_file.size_bytes),
        },
    )
