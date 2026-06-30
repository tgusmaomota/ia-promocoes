from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from api_promogg.auth.auth_facade import AuthCredentialFacade, AuthFacadeError
from api_promogg.auth.cookies import build_clear_refresh_cookie_spec, build_csrf_cookie_spec, build_refresh_cookie_spec
from api_promogg.auth.jwt_provider import ExperimentalJWTProvider
from api_promogg.auth.rbac import PersistentRBACAuthorizer
from api_promogg.auth.service import AuthError, criar_experimental_auth_service
from api_promogg.security import constants, csrf, feature_flags, settings, validators


router = APIRouter(prefix="/auth", tags=["auth-experimental"])


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


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


def _authorizer_for(service):
    return PersistentRBACAuthorizer(service.repository)


def _ensure_session_allowed(service, session_id: str):
    user = service.obter_usuario_da_sessao(session_id)
    if not user:
        raise HTTPException(status_code=401)
    authorizer = _authorizer_for(service)
    if authorizer.is_enabled() and not authorizer.can_authorize_user(user.id):
        raise HTTPException(status_code=403)
    return user


def _request_id_from(request: Request) -> str:
    return getattr(request.state, "request_id", "req_unknown")


def _cookie_secure_for(request: Request) -> bool:
    return request.url.scheme == "https"


def _set_refresh_cookie(response: Response, request: Request, refresh_token: str):
    spec = build_refresh_cookie_spec(refresh_token, secure=_cookie_secure_for(request), samesite="lax")
    response.set_cookie(**spec.as_response_kwargs())


def _clear_refresh_cookie(response: Response, request: Request):
    spec = build_clear_refresh_cookie_spec(secure=_cookie_secure_for(request), samesite="lax")
    response.set_cookie(**spec.as_response_kwargs())


def _set_csrf_cookie_if_enabled(response: Response, request: Request):
    if not settings.CSRF_ENABLED:
        return None
    token = csrf.generate_csrf_token()
    spec = build_csrf_cookie_spec(token.value, secure=_cookie_secure_for(request), samesite="lax")
    response.set_cookie(**spec.as_response_kwargs())
    return token.value


def _validate_csrf_if_enabled(request: Request):
    if not settings.CSRF_ENABLED:
        return
    cookie_token = request.cookies.get(settings.CSRF_COOKIE_NAME)
    header_token = request.headers.get(settings.CSRF_HEADER_NAME)
    if not csrf.constant_time_compare(cookie_token or "", header_token or ""):
        raise HTTPException(status_code=403)


def _issue_access_credential_if_enabled(session):
    if not feature_flags.jwt_enabled():
        return None
    if not settings.JWT_SIGNING_KEY:
        raise HTTPException(status_code=500)
    try:
        bundle = _service().emitir_credenciais_experimentais(
            session,
            AuthCredentialFacade(ExperimentalJWTProvider()),
            signing_key=settings.JWT_SIGNING_KEY,
        )
    except AuthFacadeError:
        raise HTTPException(status_code=500) from None
    return {
        "type": bundle.access.credential_type,
        "value": bundle.access.value,
        "expires_at": bundle.access.expires_at.isoformat(),
    }


def _session_payload(session, *, access_credential=None):
    return {
        "authenticated": True,
        "session_id": session.session_id,
        "user": {
            "id": session.user.id,
            "email": session.user.email,
            "status": session.user.status,
        },
        "access_credential": access_credential,
        "jwt_issued": access_credential is not None,
    }


def login(payload: LoginRequest, request: Request, response: Response):
    if not validators.validate_email(payload.email):
        raise HTTPException(status_code=400)
    if not validators.validate_max_input_size(payload.password, 1024):
        raise HTTPException(status_code=400)

    service = _service()
    try:
        result = service.autenticar_credenciais(payload.email, payload.password)
    except AuthError:
        raise HTTPException(status_code=401) from None

    _set_refresh_cookie(response, request, result.session.refresh_token)
    _set_csrf_cookie_if_enabled(response, request)
    access_credential = _issue_access_credential_if_enabled(result.session)
    return {
        "data": _session_payload(result.session, access_credential=access_credential),
        "request_id": _request_id_from(request),
    }


def logout(payload: LogoutRequest, request: Request, response: Response):
    _validate_csrf_if_enabled(request)
    if not validators.validate_request_id(payload.session_id):
        raise HTTPException(status_code=400)
    service = _service()
    _ensure_session_allowed(service, payload.session_id)
    logged_out = service.logout(payload.session_id)
    _clear_refresh_cookie(response, request)
    return {
        "data": {
            "logged_out": logged_out,
        },
        "request_id": _request_id_from(request),
    }


def refresh(request: Request, response: Response, payload: RefreshRequest | None = None):
    _validate_csrf_if_enabled(request)
    if "refresh_token" in request.query_params:
        raise HTTPException(status_code=400)
    refresh_token = (payload.refresh_token if payload else None) or request.cookies.get(constants.COOKIE_REFRESH_TOKEN)
    if not refresh_token or not validators.validate_max_input_size(refresh_token, 4096):
        raise HTTPException(status_code=400)
    service = _service()
    try:
        result = service.rotacionar_refresh_token(refresh_token)
    except AuthError:
        raise HTTPException(status_code=401) from None

    if result.status == "reused":
        _clear_refresh_cookie(response, request)
        raise HTTPException(status_code=401)

    _ensure_session_allowed(service, result.session_id)
    _set_refresh_cookie(response, request, result.refresh_token)
    session = service.obter_sessao_ativa(result.session_id)
    access_credential = _issue_access_credential_if_enabled(session) if session else None
    return {
        "data": {
            "status": result.status,
            "session_id": result.session_id,
            "access_credential": access_credential,
            "jwt_issued": access_credential is not None,
        },
        "request_id": _request_id_from(request),
    }


def me(session_id: str, request: Request):
    if not validators.validate_request_id(session_id):
        raise HTTPException(status_code=400)
    service = _service()
    user = _ensure_session_allowed(service, session_id)
    return {
        "data": {
            "session": {
                "id": session_id,
            },
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
