"""Service monitoring model surface for EGOC."""

from __future__ import annotations

from .models import ProductAvailability, Service

STANDARD_SERVICE_NAMES = (
    "Painel",
    "Site",
    "Banco",
    "Ollama",
    "Cloudflare",
    "Telegram",
    "Playwright",
    "Scheduler",
    "Supervisor",
    "Deploy",
)


def unknown_service(name: str) -> Service:
    """Return an inert service snapshot."""

    return Service(name=name, status=ProductAvailability.UNKNOWN)

