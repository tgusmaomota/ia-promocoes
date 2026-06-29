"""Validadores reutilizaveis para entradas de seguranca."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from api_promogg.security import settings

EMAIL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,64}$")
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_email(email: str) -> bool:
    if not isinstance(email, str):
        return False
    normalized = normalize_email(email)
    if len(normalized) > 254:
        return False
    return bool(EMAIL_RE.fullmatch(normalized))


def validate_password(
    password: str,
    *,
    min_length: int | None = None,
    require_complexity: bool | None = None,
) -> bool:
    if not isinstance(password, str):
        return False
    effective_min_length = settings.PASSWORD_MIN_LENGTH if min_length is None else min_length
    effective_complexity = settings.PASSWORD_REQUIRE_COMPLEXITY if require_complexity is None else require_complexity
    if len(password) < effective_min_length:
        return False
    if not effective_complexity:
        return True
    checks = (
        any(char.islower() for char in password),
        any(char.isupper() for char in password),
        any(char.isdigit() for char in password),
        any(not char.isalnum() for char in password),
    )
    return all(checks)


def validate_username(username: str) -> bool:
    if not isinstance(username, str):
        return False
    return bool(USERNAME_RE.fullmatch(username.strip()))


def validate_cors_origin(origin: str, allowed_origins: tuple[str, ...] | list[str] | None = None) -> bool:
    if not isinstance(origin, str):
        return False
    parsed = urlparse(origin.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    allowed = settings.CORS_ALLOWED_ORIGINS if allowed_origins is None else tuple(allowed_origins)
    return origin.strip() in allowed


def validate_allowed_host(host: str, allowed_hosts: tuple[str, ...] | list[str] | None = None) -> bool:
    if not isinstance(host, str):
        return False
    candidate = host.strip().lower()
    if not candidate:
        return False
    if ":" in candidate and not candidate.startswith("["):
        candidate = candidate.split(":", 1)[0]
    allowed = settings.ALLOWED_HOSTS if allowed_hosts is None else tuple(allowed_hosts)
    return candidate in {item.lower() for item in allowed}


def validate_request_id(request_id: str) -> bool:
    if not isinstance(request_id, str):
        return False
    return bool(REQUEST_ID_RE.fullmatch(request_id.strip()))


def validate_max_input_size(value: str | bytes, max_length: int) -> bool:
    if max_length < 0:
        return False
    if isinstance(value, str):
        return len(value) <= max_length
    if isinstance(value, bytes):
        return len(value) <= max_length
    return False
