"""Inert monitoring contract stubs for EmpresaGPT Phase 2."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol


class MonitoringError(Exception):
    """Base error for monitoring contract violations."""


@dataclass(frozen=True)
class HealthCheck:
    """A single health check request."""

    name: str
    target: str


@dataclass(frozen=True)
class HealthStatus:
    """Health check result."""

    name: str
    status: str = "unknown"
    details: Mapping[str, str] = field(default_factory=dict)


class MonitoringContract(Protocol):
    """Contract for explicit health checks and alerts."""

    def check(self, health_check: HealthCheck) -> HealthStatus:
        """Return health status without starting loops or alerts."""

