"""Contratos de credenciais de autenticacao.

A aplicacao deve depender destes contratos, nao de um formato concreto como JWT.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class AccessCredential:
    value: str
    credential_type: str
    subject: str
    issued_at: datetime
    expires_at: datetime
    not_before: datetime
    token_id: str
    claims: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RefreshCredential:
    value: str
    credential_type: str
    subject: str
    issued_at: datetime
    expires_at: datetime
    token_id: str
    cookie_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class CredentialProvider(Protocol):
    def is_enabled(self) -> bool:
        """Retorna se o provider pode emitir credenciais no ambiente atual."""

    def issue_access_credential(self, *, subject: str, session_id: str, **kwargs) -> AccessCredential:
        """Emite uma credencial de acesso por chamada explicita."""

    def issue_refresh_credential(self, *, subject: str, session_id: str, **kwargs) -> RefreshCredential:
        """Emite uma credencial de refresh por chamada explicita."""
