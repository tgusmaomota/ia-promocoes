"""Backup contracts for EGOC."""

from __future__ import annotations

from .models import Backup, ProductAvailability


def unknown_backup() -> Backup:
    """Return an inert backup status."""

    return Backup(status=ProductAvailability.UNKNOWN)

