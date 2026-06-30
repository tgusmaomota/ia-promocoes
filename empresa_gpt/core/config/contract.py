"""Inert configuration contract stubs for EmpresaGPT Phase 2."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol


class ConfigError(Exception):
    """Base error for platform configuration contract violations."""


@dataclass(frozen=True)
class ConfigSource:
    """A named, explicit configuration source."""

    name: str
    values: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class PlatformConfig:
    """Resolved platform configuration with services disabled by default."""

    environment: str = "development"
    service_enabled: bool = False
    client_id: str | None = None
    values: Mapping[str, str] = field(default_factory=dict)


class ConfigContract(Protocol):
    """Contract for explicit, side-effect-free configuration loading."""

    def load(self, source: ConfigSource) -> PlatformConfig:
        """Return resolved platform config without starting services."""

