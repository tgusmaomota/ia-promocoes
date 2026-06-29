"""Feature flags de seguranca para consumo por rotas futuras."""

from api_promogg.security import settings


def auth_enabled() -> bool:
    return settings.AUTH_ENABLED


def auth_experimental_enabled() -> bool:
    return settings.AUTH_EXPERIMENTAL_ENABLED


def rbac_enabled() -> bool:
    return settings.RBAC_ENABLED


def mfa_enabled() -> bool:
    return settings.MFA_ENABLED


def jwt_enabled() -> bool:
    return settings.JWT_ENABLED
