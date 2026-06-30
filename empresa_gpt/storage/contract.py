"""Inert storage contract stubs for EmpresaGPT Phase 2."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol


class StorageError(Exception):
    """Base error for storage contract violations."""


@dataclass(frozen=True)
class StorageQuery:
    """Explicit storage query contract."""

    collection: str
    filters: Mapping[str, Any] = field(default_factory=dict)
    limit: int = 100


@dataclass(frozen=True)
class StorageResult:
    """Storage result contract."""

    items: tuple[Mapping[str, Any], ...] = ()
    total: int = 0


class RepositoryContract(Protocol):
    """Contract for repositories with explicit operations."""

    def list(self, query: StorageQuery) -> StorageResult:
        """Return data without implicit migrations or side effects."""

