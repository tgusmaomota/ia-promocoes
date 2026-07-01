"""Report helpers for the EmpresaGPT Quality Engine."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class CheckResult:
    area: str
    name: str
    status: str
    severity: str
    evidence: str
    recommendation: str
    files: tuple[str, ...] = ()

    @property
    def is_ok(self) -> bool:
        return self.status == "OK"

    @property
    def is_warning(self) -> bool:
        return self.severity == "alerta"

    @property
    def is_blocking(self) -> bool:
        return self.severity in {"critico", "bloqueante"}


@dataclass(frozen=True)
class QualityReport:
    results: tuple[CheckResult, ...]
    strict: bool = False
    generated_files: tuple[str, ...] = field(default_factory=tuple)

    @property
    def critical_count(self) -> int:
        return sum(1 for result in self.results if result.severity == "critico")

    @property
    def blocking_count(self) -> int:
        return sum(1 for result in self.results if result.severity == "bloqueante")

    @property
    def warning_count(self) -> int:
        return sum(1 for result in self.results if result.severity == "alerta")

    @property
    def effective_blocking_count(self) -> int:
        base = self.critical_count + self.blocking_count
        return base + self.warning_count if self.strict else base

    @property
    def ready_for_commit(self) -> bool:
        return self.effective_blocking_count == 0

    @property
    def ready_for_phase_4(self) -> bool:
        return self.ready_for_commit and self.warning_count == 0

    def area_statuses(self) -> dict[str, str]:
        statuses = {}
        for area in ("Arquitetura", "Estrutura", "Seguranca", "Documentacao", "Contratos", "Promogg preservado", "Produto Promogg", "Git"):
            area_results = [result for result in self.results if result.area == area]
            if not area_results:
                statuses[area] = "N/D"
            elif any(result.severity == "critico" for result in area_results):
                statuses[area] = "CRITICO"
            elif any(result.severity == "bloqueante" for result in area_results):
                statuses[area] = "BLOQUEIO"
            elif any(result.severity == "alerta" for result in area_results):
                statuses[area] = "AVISO"
            else:
                statuses[area] = "OK"
        return statuses

    def to_dict(self) -> dict:
        return {
            "strict": self.strict,
            "criticos": self.critical_count,
            "bloqueantes": self.blocking_count,
            "alertas": self.warning_count,
            "bloqueios_efetivos": self.effective_blocking_count,
            "PRONTO_PARA_COMMIT": self.ready_for_commit,
            "PRONTO_PARA_FASE_4": self.ready_for_phase_4,
            "generated_files": list(self.generated_files),
            "checks": [asdict(result) for result in self.results],
        }


def render_human_summary(report: QualityReport) -> str:
    lines = ["EmpresaGPT Quality Engine", ""]
    for area, status in report.area_statuses().items():
        lines.append(f"{area + '.':.<25} {status}")
    lines.extend(
        [
            "",
            f"Criticos: {report.critical_count}",
            f"Bloqueantes: {report.blocking_count}",
            f"Alertas: {report.warning_count}",
            "",
            f"PRONTO_PARA_COMMIT={'true' if report.ready_for_commit else 'false'}",
            f"PRONTO_PARA_FASE_4={'true' if report.ready_for_phase_4 else 'false'}",
        ]
    )
    return "\n".join(lines)


def render_markdown(report: QualityReport) -> str:
    lines = [
        "# Relatorio EmpresaGPT Quality Engine",
        "",
        f"Strict: {'sim' if report.strict else 'nao'}",
        "",
        render_human_summary(report),
        "",
        "## Checks Executados",
        "",
        "| Area | Check | Status | Severidade | Evidencia | Recomendacao | Arquivos |",
        "|---|---|---|---|---|---|---|",
    ]
    for result in report.results:
        files = "<br>".join(result.files)
        lines.append(
            "| {area} | {name} | {status} | {severity} | {evidence} | {recommendation} | {files} |".format(
                area=_md(result.area),
                name=_md(result.name),
                status=_md(result.status),
                severity=_md(result.severity),
                evidence=_md(result.evidence),
                recommendation=_md(result.recommendation),
                files=_md(files),
            )
        )
    return "\n".join(lines) + "\n"


def write_reports(report: QualityReport, root: Path, write_json: bool = False) -> QualityReport:
    generated = ["RELATORIO_EMPRESAGPT_QUALITY_ENGINE.md"]
    (root / generated[0]).write_text(render_markdown(report), encoding="utf-8")
    if write_json:
        generated.append("RELATORIO_EMPRESAGPT_QUALITY_ENGINE.json")
        (root / generated[-1]).write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return QualityReport(results=report.results, strict=report.strict, generated_files=tuple(generated))


def make_result(
    area: str,
    name: str,
    ok: bool,
    evidence: str,
    recommendation: str,
    *,
    severity: str = "bloqueante",
    files: Iterable[str] = (),
) -> CheckResult:
    return CheckResult(
        area=area,
        name=name,
        status="OK" if ok else "FALHA",
        severity="info" if ok else severity,
        evidence=evidence,
        recommendation="Nenhuma." if ok else recommendation,
        files=tuple(files),
    )


def _md(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")
