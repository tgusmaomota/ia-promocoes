"""Alert model surface for EGOC."""

from __future__ import annotations

from .models import Alert, AlertLevel

ALERT_LEVELS = (
    AlertLevel.INFO,
    AlertLevel.WARNING,
    AlertLevel.IMPORTANT,
    AlertLevel.CRITICAL,
)


def informational_alert(title: str, message: str = "") -> Alert:
    """Create a non-runtime informational alert."""

    return Alert(level=AlertLevel.INFO, title=title, message=message)

