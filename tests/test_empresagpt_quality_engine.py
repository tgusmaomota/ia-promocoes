from pathlib import Path

from empresa_gpt.quality.engine import QualityEngine
from empresa_gpt.quality.report import CheckResult, QualityReport, render_human_summary


def test_quality_report_strict_turns_alerts_into_blockers():
    report = QualityReport(
        results=(
            CheckResult(
                area="Git",
                name="Alteracoes pendentes",
                status="FALHA",
                severity="alerta",
                evidence="1 alteracao",
                recommendation="Revisar.",
            ),
        ),
        strict=True,
    )

    assert report.warning_count == 1
    assert report.effective_blocking_count == 1
    assert report.ready_for_commit is False


def test_quality_summary_contains_required_flags():
    report = QualityReport(
        results=(
            CheckResult(
                area="Arquitetura",
                name="ok",
                status="OK",
                severity="info",
                evidence="ok",
                recommendation="Nenhuma.",
            ),
        )
    )

    summary = render_human_summary(report)

    assert "EmpresaGPT Quality Engine" in summary
    assert "PRONTO_PARA_COMMIT=true" in summary
    assert "PRONTO_PARA_FASE_4=true" in summary


def test_quality_engine_can_run_without_writing_reports():
    report = QualityEngine(root=Path.cwd()).run(write_report=False)

    assert report.results
    assert not report.generated_files

