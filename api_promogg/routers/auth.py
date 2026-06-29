from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from api_promogg.auth.service import AuthError, criar_experimental_auth_service
from api_promogg.security import constants, feature_flags, settings, validators


router = APIRouter(prefix="/auth", tags=["auth-experimental"])


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    session_id: str


def _ensure_experimental_auth_available():
    if not feature_flags.auth_experimental_enabled():
        raise HTTPException(status_code=404)
    if settings.PROMOGG_ENV != constants.ENVIRONMENT_DEVELOPMENT:
        raise HTTPException(status_code=404)


def _experimental_auth_available_at_startup() -> bool:
    return feature_flags.auth_experimental_enabled() and settings.PROMOGG_ENV == constants.ENVIRONMENT_DEVELOPMENT


def _service():
    return criar_experimental_auth_service()


def _request_id_from(request: Request) -> str:
    return getattr(request.state, "request_id", "req_unknown")


def login(payload: LoginRequest, request: Request):
    if not validators.validate_email(payload.email):
        raise HTTPException(status_code=400)
    if not validators.validate_max_input_size(payload.password, 1024):
        raise HTTPException(status_code=400)

    try:
        result = _service().autenticar_credenciais(payload.email, payload.password)
    except AuthError:
        raise HTTPException(status_code=401) from None

    return {
        "data": {
            "authenticated": result.authenticated,
            "session_id": result.session.session_id,
            "user": {
                "id": result.session.user.id,
                "email": result.session.user.email,
                "status": result.session.user.status,
            },
            "refresh_token": result.session.refresh_token,
            "access_token": None,
            "jwt_issued": False,
        },
        "request_id": _request_id_from(request),
    }


def logout(payload: LogoutRequest, request: Request):
    if not validators.validate_request_id(payload.session_id):
        raise HTTPException(status_code=400)
    logged_out = _service().logout(payload.session_id)
    return {
        "data": {
            "logged_out": logged_out,
        },
        "request_id": _request_id_from(request),
    }


def refresh(payload: RefreshRequest, request: Request):
    if not validators.validate_max_input_size(payload.refresh_token, 4096):
        raise HTTPException(status_code=400)
    try:
        result = _service().rotacionar_refresh_token(payload.refresh_token)
    except AuthError:
        raise HTTPException(status_code=401) from None

    return {
        "data": {
            "status": result.status,
            "session_id": result.session_id,
            "refresh_token": result.refresh_token,
            "access_token": None,
            "jwt_issued": False,
        },
        "request_id": _request_id_from(request),
    }


def me(session_id: str, request: Request):
    if not validators.validate_request_id(session_id):
        raise HTTPException(status_code=400)
    user = _service().obter_usuario_da_sessao(session_id)
    if not user:
        raise HTTPException(status_code=401)
    return {
        "data": {
            "user": {
                "id": user.id,
                "email": user.email,
                "status": user.status,
            },
            "jwt_issued": False,
        },
        "request_id": _request_id_from(request),
    }


if _experimental_auth_available_at_startup():
    guarded = [Depends(_ensure_experimental_auth_available)]
    router.add_api_route("/login", login, methods=["POST"], dependencies=guarded)
    router.add_api_route("/logout", logout, methods=["POST"], dependencies=guarded)
    router.add_api_route("/refresh", refresh, methods=["POST"], dependencies=guarded)
    router.add_api_route("/me", me, methods=["GET"], dependencies=guarded)
