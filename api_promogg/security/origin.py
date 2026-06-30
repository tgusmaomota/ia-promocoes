"""Validadores passivos de Origin, Host e Referer."""

from __future__ import annotations

from urllib.parse import urlparse

from api_promogg.security import constants, settings


def _normalize_host(host: str) -> str:
    candidate = host.strip().lower()
    if candidate.startswith("["):
        return candidate
    if ":" in candidate:
        candidate = candidate.split(":", 1)[0]
    return candidate


def _host_from_url(value: str) -> str | None:
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return _normalize_host(parsed.netloc)


def allowed_domains_for_environment(environment: str | None = None) -> tuple[str, ...]:
    env = (environment or settings.PROMOGG_ENV).strip().lower()
    if env == constants.ENVIRONMENT_DEVELOPMENT:
        return ("localhost", "127.0.0.1")
    if env == constants.ENVIRONMENT_PRODUCTION:
        return tuple(settings.ALLOWED_HOSTS)
    return ()


def validate_origin(origin: str, *, environment: str | None = None, allowed_domains: tuple[str, ...] | None = None) -> bool:
    if not isinstance(origin, str):
        return False
    host = _host_from_url(origin)
    if not host:
        return False
    allowed = allowed_domains if allowed_domains is not None else allowed_domains_for_environment(environment)
    return host in {_normalize_host(item) for item in allowed}


def validate_host(host: str, *, environment: str | None = None, allowed_domains: tuple[str, ...] | None = None) -> bool:
    if not isinstance(host, str):
        return False
    candidate = _normalize_host(host)
    if not candidate:
        return False
    allowed = allowed_domains if allowed_domains is not None else allowed_domains_for_environment(environment)
    return candidate in {_normalize_host(item) for item in allowed}


def validate_referer(
    referer: str | None,
    *,
    required: bool = False,
    environment: str | None = None,
    allowed_domains: tuple[str, ...] | None = None,
) -> bool:
    if referer is None:
        return not required
    if not isinstance(referer, str):
        return False
    host = _host_from_url(referer)
    if not host:
        return False
    allowed = allowed_domains if allowed_domains is not None else allowed_domains_for_environment(environment)
    return host in {_normalize_host(item) for item in allowed}
