"""Orchestrator for the EmpresaGPT Quality Engine."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .checks import run_all_checks
from .report import QualityReport, render_human_summary, write_reports
from .rules import ROOT


@dataclass(frozen=True)
class QualityEngine:
    root: Path = ROOT

    def run(self, *, strict: bool = False, write_json: bool = False, write_report: bool = True) -> QualityReport:
        report = QualityReport(results=run_all_checks(self.root), strict=strict)
        if write_report:
            report = write_reports(report, self.root, write_json=write_json)
        return report


def run_quality_check(*, strict: bool = False, json_output: bool = False, root: Path | None = None) -> QualityReport:
    engine = QualityEngine(root=root or ROOT)
    return engine.run(strict=strict, write_json=json_output, write_report=True)


def print_quality_summary(report: QualityReport) -> None:
    print(render_human_summary(report))
    if report.generated_files:
        print()
        print("Relatorios:")
        for path in report.generated_files:
            print(f"- {path}")

