"""Inert service contract stubs for EmpresaGPT Phase 2."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol


class ServiceError(Exception):
    """Base error for service contract violations."""


@dataclass(frozen=True)
class ServiceCommand:
    """Explicit command for a platform service."""

    name: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    dry_run: bool = True


@dataclass(frozen=True)
class ServiceResult:
    """Result for a service command."""

    accepted: bool = False
    status: str = "disabled_by_default"
    details: Mapping[str, Any] = field(default_factory=dict)


class ServiceContract(Protocol):
    """Contract for explicit service execution."""

    def execute(self, command: ServiceCommand) -> ServiceResult:
        """Execute only when explicitly implemented and enabled."""

