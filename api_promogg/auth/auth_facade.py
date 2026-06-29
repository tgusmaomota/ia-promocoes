"""Fachada experimental para emissao de credenciais.

Este modulo e o ponto autorizado para emissao de credenciais experimentais.
Rotas HTTP nao devem usa-lo nesta fase.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from api_promogg.auth.credentials import AccessCredential, CredentialProvider, RefreshCredential
from api_promogg.security import constants, settings


class AuthFacadeError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class CredentialBundle:
    access: AccessCredential
    refresh: RefreshCredential


class AuthCredentialFacade:
    def __init__(self, provider: CredentialProvider):
        self.provider = provider
        self._revoked_token_ids: set[str] = set()

    def issue_credentials(self, *, subject: str, session_id: str, **kwargs) -> CredentialBundle:
        self._ensure_can_issue()
        access = self.provider.issue_access_credential(subject=subject, session_id=session_id, **kwargs)
        refresh = self.provider.issue_refresh_credential(subject=subject, session_id=session_id, **kwargs)
        return CredentialBundle(access=access, refresh=refresh)

    def renew_credentials(self, *, refresh_credential: RefreshCredential, session_id: str, **kwargs) -> CredentialBundle:
        self._ensure_can_issue()
        if not self.validate_refresh_credential(refresh_credential):
            raise AuthFacadeError("INVALID_REFRESH_CREDENTIAL", "Credencial de refresh invalida.")
        self.revoke(refresh_credential.token_id)
        return self.issue_credentials(subject=refresh_credential.subject, session_id=session_id, **kwargs)

    def revoke(self, token_id: str) -> bool:
        if not token_id:
            return False
        self._revoked_token_ids.add(token_id)
        return True

    def validate_access_credential(self, credential: AccessCredential) -> bool:
        if credential.token_id in self._revoked_token_ids:
            return False
        now = datetime.now(UTC)
        return credential.not_before <= now < credential.expires_at

    def validate_refresh_credential(self, credential: RefreshCredential) -> bool:
        if credential.token_id in self._revoked_token_ids:
            return False
        now = datetime.now(UTC)
        return now < credential.expires_at

    def _ensure_can_issue(self):
        if not settings.AUTH_ENABLED:
            raise AuthFacadeError("AUTH_DISABLED", "Autenticacao desabilitada.")
        if not settings.AUTH_EXPERIMENTAL_ENABLED:
            raise AuthFacadeError("AUTH_EXPERIMENTAL_DISABLED", "Autenticacao experimental desabilitada.")
        if not settings.JWT_ENABLED:
            raise AuthFacadeError("JWT_DISABLED", "JWT experimental desabilitado.")
        if settings.PROMOGG_ENV != constants.ENVIRONMENT_DEVELOPMENT:
            raise AuthFacadeError("AUTH_ENV_NOT_ALLOWED", "Credenciais experimentais permitidas apenas em development.")
        if not self.provider.is_enabled():
            raise AuthFacadeError("CREDENTIAL_PROVIDER_DISABLED", "Provider de credenciais desabilitado.")
