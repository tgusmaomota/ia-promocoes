"""Future CLI entrypoint for the EmpresaGPT Quality Engine."""

from __future__ import annotations

import argparse

from .engine import print_quality_summary, run_quality_check


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EmpresaGPT Quality Engine")
    parser.add_argument("--json", action="store_true", help="tambem gera relatorio JSON")
    parser.add_argument("--strict", action="store_true", help="alertas viram bloqueio")
    args = parser.parse_args(argv)
    report = run_quality_check(strict=args.strict, json_output=args.json)
    print_quality_summary(report)
    return 0 if report.ready_for_commit else 1


if __name__ == "__main__":
    raise SystemExit(main())

