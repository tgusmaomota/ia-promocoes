"""Risk Engine contracts for EGOC.

This module intentionally does not implement a scoring algorithm. It defines
the levels and output shape that future product adapters will report.
"""

from __future__ import annotations

from .models import Risk, RiskLevel

RISK_LEVELS = (
    RiskLevel.LOW,
    RiskLevel.MODERATE,
    RiskLevel.HIGH,
    RiskLevel.CRITICAL,
    RiskLevel.UNKNOWN,
)


def unknown_risk() -> Risk:
    """Return an inert unknown risk snapshot."""

    return Risk(level=RiskLevel.UNKNOWN, score=0.0)

