"""Helpers passivos de CSRF.

Este modulo nao se integra a routers e nao escreve cookies. Ele apenas gera e
valida contratos de token para uma futura protecao CSRF.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from api_promogg.security import settings


@dataclass(frozen=True)
class CsrfToken:
    value: str
    issued_at: datetime
    expires_at: datetime


def generate_csrf_token(*, ttl_seconds: int | None = None, nbytes: int = 32) -> CsrfToken:
    if nbytes < 32:
        raise ValueError("Token CSRF deve ter pelo menos 32 bytes de entropia.")
    effective_ttl = ttl_seconds if ttl_seconds is not None else settings.CSRF_TOKEN_TTL
    if effective_ttl <= 0:
        raise ValueError("TTL de CSRF deve ser positivo.")
    issued_at = datetime.now(UTC)
    return CsrfToken(
        value=secrets.token_urlsafe(nbytes),
        issued_at=issued_at,
        expires_at=issued_at + timedelta(seconds=effective_ttl),
    )


def constant_time_compare(left: str, right: str) -> bool:
    if not left or not right:
        return False
    return secrets.compare_digest(left, right)


def is_csrf_token_expired(token: CsrfToken, *, now: datetime | None = None) -> bool:
    effective_now = now or datetime.now(UTC)
    return effective_now >= token.expires_at


def validate_csrf_token(expected: CsrfToken, provided: str, *, now: datetime | None = None) -> bool:
    if is_csrf_token_expired(expected, now=now):
        return False
    return constant_time_compare(expected.value, provided)
