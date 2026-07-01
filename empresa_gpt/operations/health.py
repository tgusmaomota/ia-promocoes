"""Health Engine contracts and helpers for EGOC."""

from __future__ import annotations

from .models import Health, ProductAvailability

HEALTH_STATES = (
    ProductAvailability.ONLINE,
    ProductAvailability.OFFLINE,
    ProductAvailability.DEGRADED,
    ProductAvailability.MAINTENANCE,
    ProductAvailability.UNKNOWN,
)


def unknown_health(summary: str = "Health not reported.") -> Health:
    """Return an inert unknown health snapshot."""

    return Health(status=ProductAvailability.UNKNOWN, score=0.0, summary=summary)

