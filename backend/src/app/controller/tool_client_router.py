from pathlib import Path
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED

from fastapi import APIRouter, HTTPException, Security, status
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.data_access import AuthService

router = APIRouter(prefix="/tool-client", tags=["tool-client"])

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


def _get_clients_dir() -> Path:
    """
    Estructura esperada:
    BBAgentPython/
      clients/
      src/app/controller/tool_client_router.py

    Desde este archivo subimos:
    controller -> app -> src -> BBAgentPython
    """
    project_root = Path(__file__).resolve().parents[3]
    clients_dir = project_root / "clients"

    if not clients_dir.exists() or not clients_dir.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clients directory not found",
        )

    return clients_dir


@router.get(
    "/download",
    summary="Descargar la carpeta clients comprimida en zip",
    description=(
        "Comprime la carpeta clients del servidor y la devuelve como archivo zip. "
        "Requiere Authorization: Bearer <token>."
    ),
)
async def download_clients_zip(
    bearer_token: str = Security(_require_bearer_token),
):
    # Valida el token; si no es válido lanza 401
    _get_user_from_token(bearer_token)

    clients_dir = _get_clients_dir()

    # Export source and explicitly approved setup files, never local configuration.
    setup_files = {"README.md", "requirements.txt", "requirements-terminal.txt"}
    archive = BytesIO()
    root = clients_dir.resolve()
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as zip_file:
        for source in sorted(clients_dir.rglob("*")):
            relative = source.relative_to(clients_dir)
            if source.suffix != ".py" and relative.as_posix() not in setup_files:
                continue
            if (not source.is_file() or source.is_symlink()
                    or not source.resolve().is_relative_to(root)
                    or any(part.startswith(".") or part in {"__pycache__", "venv", "env"} for part in relative.parts)):
                continue
            zip_file.write(source, arcname=(Path("clients") / relative).as_posix())

    return Response(
        content=archive.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="clients.zip"'},
    )
