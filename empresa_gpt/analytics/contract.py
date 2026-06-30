"""Inert analytics contract stubs for EmpresaGPT Phase 2."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol


class AnalyticsError(Exception):
    """Base error for analytics contract violations."""


@dataclass(frozen=True)
class AnalyticsEvent:
    """Sanitized analytics event contract."""

    name: str
    resource: str
    properties: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AnalyticsReport:
    """Analytics report contract."""

    name: str
    metrics: Mapping[str, Any] = field(default_factory=dict)


class AnalyticsContract(Protocol):
    """Contract for sanitized analytics collection and reporting."""

    def track(self, event: AnalyticsEvent) -> None:
        """Track an event only when explicitly enabled by caller."""

    def report(self, name: str) -> AnalyticsReport:
        """Return an analytics report."""

