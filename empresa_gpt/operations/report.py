"""Reporting contracts for EGOC."""

from __future__ import annotations

from dataclasses import dataclass

from .models import Product


@dataclass(frozen=True)
class OperationsReport:
    """A product-neutral operational report."""

    title: str
    products: tuple[Product, ...] = ()
    generated_at: str | None = None
    summary: str = ""


def empty_report(title: str = "EmpresaGPT Operations Center") -> OperationsReport:
    """Return an empty report without reading runtime state."""

    return OperationsReport(title=title)

