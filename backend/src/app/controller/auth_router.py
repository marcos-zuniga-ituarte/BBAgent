from fastapi import APIRouter, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.data_access import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------
# Schemas
# ---------------------------

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=1)


class LoginRequest(BaseModel):
    login: str = Field(..., min_length=1, description="Login del usuario")
    password: str = Field(..., min_length=1, description="Contraseña del usuario")


class IdResponse(BaseModel):
    id: str


class TokenResponse(BaseModel):
    access_token: str


class OkResponse(BaseModel):
    result: str


class ErrorResponse(BaseModel):
    detail: str


# ---------------------------
# Helpers
# ---------------------------

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
    "/users/password",
    response_model=OkResponse,
    summary="Cambiar contraseña",
    description="Requiere Authorization: Bearer <token>",
    responses={
        200: {"model": OkResponse, "description": "Password actualizado"},
        401: {"model": ErrorResponse, "description": "Token inválido o contraseña actual incorrecta"},
        400: {"model": ErrorResponse, "description": "Datos inválidos"},
    },
)
def change_password(
    payload: ChangePasswordRequest,
    bearer_token: str = Security(_require_bearer_token),
):
    try:
        user = AuthService.get_user_by_token(bearer_token)

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        if payload.current_password == payload.new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from current password",
            )

        try:
            AuthService.authenticate(
                login=user.login,  # cambia esto por user.username o user.email si aplica
                password=payload.current_password,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect",
            ) from exc

        AuthService.change_password_by_user(
            user=user,
            new_password=payload.new_password,
        )

        return OkResponse(result="ok")

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión",
    description=(
        "Autentica al usuario y devuelve un access token."
    ),
    responses={
        200: {"model": TokenResponse, "description": "Login correcto"},
        401: {"model": ErrorResponse, "description": "Credenciales inválidas"},
    },
)
def login(payload: LoginRequest):
    try:
        session = AuthService.authenticate(
            login=payload.login,
            password=payload.password,
        )
        return TokenResponse(access_token=session.token)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


@router.post(
    "/logout",
    response_model=OkResponse,
    summary="Cerrar sesión",
    description=(
        "Revoca la sesión actual. "
        "Requiere Authorization: Bearer <token>."
    ),
    responses={
        200: {"model": OkResponse, "description": "Logout correcto"},
        401: {"model": ErrorResponse, "description": "Falta token o token inválido"},
    },
)
def logout(
    bearer_token: str = Security(_require_bearer_token),
):
    AuthService.revoke_session(bearer_token)
    return OkResponse(result="ok")