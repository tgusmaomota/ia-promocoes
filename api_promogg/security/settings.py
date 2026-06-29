"""Configuracao central de seguranca lida do ambiente."""

from __future__ import annotations

import os

from api_promogg.security import constants


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise RuntimeError(f"Valor booleano invalido para {name}: {raw_value!r}")


def _env_int(name: str, default: int, *, minimum: int = 0) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"Valor inteiro invalido para {name}: {raw_value!r}") from exc
    if value < minimum:
        raise RuntimeError(f"{name} deve ser maior ou igual a {minimum}.")
    return value


def _env_csv(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return tuple(item.strip() for item in raw_value.split(",") if item.strip())


AUTH_ENABLED = _env_bool(constants.ENV_AUTH_ENABLED, False)
AUTH_EXPERIMENTAL_ENABLED = _env_bool(constants.ENV_AUTH_EXPERIMENTAL_ENABLED, False)
PROMOGG_ENV = os.getenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_PRODUCTION).strip().lower()
MFA_ENABLED = _env_bool(constants.ENV_MFA_ENABLED, False)
JWT_ENABLED = _env_bool(constants.ENV_JWT_ENABLED, False)
RBAC_ENABLED = _env_bool(constants.ENV_RBAC_ENABLED, False)
AUDIT_ENABLED = _env_bool(constants.ENV_AUDIT_ENABLED, True)

MAX_LOGIN_ATTEMPTS = _env_int(constants.ENV_MAX_LOGIN_ATTEMPTS, 5, minimum=1)
LOCKOUT_MINUTES = _env_int(constants.ENV_LOCKOUT_MINUTES, 15, minimum=1)
ACCESS_TOKEN_TTL = _env_int(constants.ENV_ACCESS_TOKEN_TTL, 900, minimum=60)
REFRESH_TOKEN_TTL = _env_int(constants.ENV_REFRESH_TOKEN_TTL, 2_592_000, minimum=60)
PASSWORD_MIN_LENGTH = _env_int(constants.ENV_PASSWORD_MIN_LENGTH, 12, minimum=1)
PASSWORD_REQUIRE_COMPLEXITY = _env_bool(constants.ENV_PASSWORD_REQUIRE_COMPLEXITY, True)

CORS_ALLOWED_ORIGINS = _env_csv(
    constants.ENV_CORS_ALLOWED_ORIGINS,
    (
        "http://localhost:8501",
        "http://localhost:8503",
        "http://127.0.0.1:8501",
        "http://127.0.0.1:8503",
        "https://promogg.com.br",
    ),
)

ALLOWED_HOSTS = _env_csv(
    constants.ENV_ALLOWED_HOSTS,
    (
        "localhost",
        "127.0.0.1",
        "promogg.com.br",
    ),
)
