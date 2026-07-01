"""Audit storage contracts for EGOC."""

from __future__ import annotations

from .models import Audit, AuditArea

AUDIT_AREAS = (
    AuditArea.SECURITY,
    AuditArea.QUALITY,
    AuditArea.PUBLICATION,
    AuditArea.SEO,
    AuditArea.CATALOG,
    AuditArea.PERFORMANCE,
    AuditArea.CONTRACTS,
)


def unknown_audit(area: AuditArea) -> Audit:
    """Return an inert audit result."""

    return Audit(area=area, status="unknown")

