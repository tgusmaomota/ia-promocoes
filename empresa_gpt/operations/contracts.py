"""Contracts for EmpresaGPT Operations Center.

Contracts are inert and product-neutral. Future products register explicit
snapshots through adapters that implement these protocols.
"""

from __future__ import annotations

from typing import Protocol

from .models import Alert, Audit, Backup, Health, Metric, Product, Risk, Service


class OperationsContractError(Exception):
    """Base error for EGOC contract violations."""


class ProductHealthContract(Protocol):
    """Reports product health without starting product runtime."""

    def health(self, product_name: str) -> Health:
        """Return a health snapshot for a product."""


class ProductStatusContract(Protocol):
    """Reports the complete status of a product."""

    def product_status(self, product_name: str) -> Product:
        """Return the product status snapshot."""


class ServiceContract(Protocol):
    """Reports services owned by a product."""

    def services(self, product_name: str) -> tuple[Service, ...]:
        """Return service snapshots."""


class RiskContract(Protocol):
    """Reports risk state calculated outside EGOC."""

    def risk(self, product_name: str) -> Risk:
        """Return a risk snapshot."""


class BackupContract(Protocol):
    """Reports backup state."""

    def backups(self, product_name: str) -> tuple[Backup, ...]:
        """Return backup snapshots."""


class AuditContract(Protocol):
    """Reports audit results."""

    def audits(self, product_name: str) -> tuple[Audit, ...]:
        """Return audit snapshots."""


class AlertContract(Protocol):
    """Reports operational alerts."""

    def alerts(self, product_name: str) -> tuple[Alert, ...]:
        """Return alert snapshots."""


class MetricsContract(Protocol):
    """Reports operational metrics."""

    def metrics(self, product_name: str) -> tuple[Metric, ...]:
        """Return metric snapshots."""


class ProductOperationsContract(
    ProductHealthContract,
    ProductStatusContract,
    ServiceContract,
    RiskContract,
    BackupContract,
    AuditContract,
    AlertContract,
    MetricsContract,
    Protocol,
):
    """Complete product adapter contract for future EGOC integration."""

