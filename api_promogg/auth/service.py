from dataclasses import dataclass

from api_promogg.auth.audit import AuditEvent
from api_promogg.auth.password import hash_password, verify_password
from api_promogg.auth.repository import AuthRepository
from api_promogg.auth.tokens import generate_opaque_token


GENERIC_LOGIN_ERROR = "Credenciais inválidas."


class AuthError(Exception):
    def __init__(self, code: str, message: str = GENERIC_LOGIN_ERROR):
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class UserDTO:
    id: str
    email: str
    status: str


@dataclass(frozen=True)
class SessionResult:
    session_id: str
    user: UserDTO
    refresh_token: str


@dataclass(frozen=True)
class AuthResult:
    authenticated: bool
    session: SessionResult | None = None


@dataclass(frozen=True)
class RefreshResult:
    status: str
    session_id: str | None = None
    refresh_token: str | None = None


class ExperimentalAuthService:
    def __init__(self, repository: AuthRepository):
        self.repository = repository

    def criar_usuario_experimental(self, email: str, password: str, status: str = "active") -> UserDTO:
        user = self.repository.criar_usuario(email, hash_password(password), status=status)
        self._audit("auth.user.created", "success", actor_user_id=user.id, metadata={"email": user.email, "password": password})
        return _user_dto(user)

    def autenticar_credenciais(self, email: str, password: str) -> AuthResult:
        user = self.repository.buscar_usuario_por_email(email)
        if not user or user.status != "active" or not verify_password(password, user.password_hash):
            self._audit("auth.login.failure", "failure", metadata={"email": email, "password": password})
            raise AuthError("INVALID_CREDENTIALS")

        session = self.repository.criar_sessao(user.id)
        refresh_token = generate_opaque_token()
        self.repository.registrar_refresh_token(session.id, refresh_token)
        self._audit("auth.login.success", "success", actor_user_id=user.id, actor_session_id=session.id)
        return AuthResult(
            authenticated=True,
            session=SessionResult(
                session_id=session.id,
                user=_user_dto(user),
                refresh_token=refresh_token,
            ),
        )

    def rotacionar_refresh_token(self, refresh_token: str) -> RefreshResult:
        record = self.repository.buscar_refresh_token_por_token(refresh_token)
        if not record:
            self._audit("auth.refresh.invalid", "failure", metadata={"refresh_token": refresh_token})
            raise AuthError("INVALID_REFRESH_TOKEN", "Refresh token inválido.")

        session = self.repository.buscar_sessao(record.session_id)
        if (
            record.used_at is not None
            or record.revoked_at is not None
            or session is None
            or session.status != "active"
        ):
            self.repository.marcar_reuso_refresh_token(record.id)
            if session:
                self.repository.revogar_sessao(session.id, reason="refresh_reuse")
            self._audit(
                "auth.refresh.reused",
                "blocked",
                actor_session_id=record.session_id,
                metadata={"refresh_token": refresh_token},
            )
            return RefreshResult(status="reused", session_id=record.session_id)

        self.repository.marcar_refresh_token_usado(record.id)
        novo_refresh = generate_opaque_token()
        self.repository.registrar_refresh_token(
            record.session_id,
            novo_refresh,
            family_id=record.family_id,
            previous_token_id=record.id,
        )
        self._audit("auth.refresh.used", "success", actor_session_id=record.session_id)
        return RefreshResult(status="rotated", session_id=record.session_id, refresh_token=novo_refresh)

    def logout(self, session_id: str) -> bool:
        session = self.repository.revogar_sessao(session_id, reason="logout")
        self._audit("auth.logout", "success", actor_session_id=session_id)
        return bool(session and session.status == "revoked")

    def _audit(self, action, result, actor_user_id=None, actor_session_id=None, metadata=None):
        self.repository.registrar_evento_auditoria(
            AuditEvent(
                action=action,
                result=result,
                actor_user_id=actor_user_id,
                actor_session_id=actor_session_id,
                metadata=metadata or {},
            )
        )


def _user_dto(user) -> UserDTO:
    return UserDTO(id=user.id, email=user.email, status=user.status)
