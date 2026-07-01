"""Data models for EmpresaGPT Operations Center.

The EGOC models are product-neutral. They describe operational state that any
EmpresaGPT product can report without giving this package knowledge of the
product runtime, database, APIs, or deployment process.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class ProductAvailability(str, Enum):
    """Canonical availability states for products and services."""

    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    DEGRADED = "DEGRADED"
    MAINTENANCE = "MAINTENANCE"
    UNKNOWN = "UNKNOWN"


class DeploymentStatus(str, Enum):
    """Deployment lifecycle state reported by a product."""

    NOT_CONFIGURED = "NOT_CONFIGURED"
    READY = "READY"
    BLOCKED = "BLOCKED"
    DEPLOYED = "DEPLOYED"
    ROLLBACK_REQUIRED = "ROLLBACK_REQUIRED"
    UNKNOWN = "UNKNOWN"


class RiskLevel(str, Enum):
    """Risk levels used by the future Risk Engine."""

    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class AlertLevel(str, Enum):
    """Alert severity used by EGOC."""

    INFO = "INFO"
    WARNING = "WARNING"
    IMPORTANT = "IMPORTANT"
    CRITICAL = "CRITICAL"


class AuditArea(str, Enum):
    """Audit domains stored by EGOC."""

    SECURITY = "SECURITY"
    QUALITY = "QUALITY"
    PUBLICATION = "PUBLICATION"
    SEO = "SEO"
    CATALOG = "CATALOG"
    PERFORMANCE = "PERFORMANCE"
    CONTRACTS = "CONTRACTS"


@dataclass(frozen=True)
class Health:
    """Product health score and availability snapshot."""

    status: ProductAvailability = ProductAvailability.UNKNOWN
    score: float = 0.0
    checked_at: str | None = None
    summary: str = ""
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Risk:
    """Risk snapshot produced by explicit product inputs."""

    level: RiskLevel = RiskLevel.UNKNOWN
    score: float = 0.0
    factors: tuple[str, ...] = ()
    checked_at: str | None = None
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Service:
    """A monitored service reported by a product adapter."""

    name: str
    status: ProductAvailability = ProductAvailability.UNKNOWN
    uptime_seconds: int | None = None
    cpu_percent: float | None = None
    ram_mb: float | None = None
    version: str | None = None
    last_checked_at: str | None = None
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Metric:
    """A product-neutral operational metric."""

    name: str
    value: float
    unit: str = ""
    captured_at: str | None = None
    dimensions: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Audit:
    """A stored audit result for one product and area."""

    area: AuditArea
    status: str = "unknown"
    score: float | None = None
    executed_at: str | None = None
    findings: tuple[str, ...] = ()
    report_path: str | None = None
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Backup:
    """Backup state reported by a product."""

    status: ProductAvailability = ProductAvailability.UNKNOWN
    last_backup_at: str | None = None
    validation_status: str = "unknown"
    integrity_status: str = "unknown"
    retention_policy: str = ""
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Alert:
    """Operational alert surfaced in EGOC."""

    level: AlertLevel
    title: str
    message: str = ""
    created_at: str | None = None
    source: str = "unknown"
    resolved: bool = False
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Product:
    """Complete product status as seen by EGOC."""

    name: str
    version: str
    status: ProductAvailability = ProductAvailability.UNKNOWN
    availability: ProductAvailability = ProductAvailability.UNKNOWN
    last_updated_at: str | None = None
    last_backup_at: str | None = None
    last_audit_at: str | None = None
    last_validation_at: str | None = None
    health_score: float = 0.0
    risk_score: float = 0.0
    quality_score: float = 0.0
    deployment_status: DeploymentStatus = DeploymentStatus.UNKNOWN
    services: tuple[Service, ...] = ()
    metrics: tuple[Metric, ...] = ()
    audits: tuple[Audit, ...] = ()
    backups: tuple[Backup, ...] = ()
    alerts: tuple[Alert, ...] = ()
    details: Mapping[str, Any] = field(default_factory=dict)

