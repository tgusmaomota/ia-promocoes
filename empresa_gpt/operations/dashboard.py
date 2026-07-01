"""Dashboard architecture for EmpresaGPT Operations Center.

The dashboard module is intentionally declarative. It defines the visual and
operational hierarchy without importing UI frameworks or product runtimes.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DashboardSection:
    """A dashboard section definition."""

    name: str
    children: tuple["DashboardSection", ...] = ()


EGOC_DASHBOARD_TREE = DashboardSection(
    "EmpresaGPT",
    (
        DashboardSection(
            "Produtos",
            (
                DashboardSection("Saude"),
                DashboardSection("Servicos"),
                DashboardSection("Backups"),
                DashboardSection("Alertas"),
                DashboardSection("Auditorias"),
                DashboardSection("Qualidade"),
                DashboardSection("Riscos"),
                DashboardSection("Uso de recursos"),
            ),
        ),
    ),
)

