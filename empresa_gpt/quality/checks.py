"""Individual checks for the EmpresaGPT Quality Engine."""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path

from . import rules
from .report import CheckResult, make_result


def run_all_checks(root: Path | None = None) -> tuple[CheckResult, ...]:
    root = root or rules.ROOT
    results: list[CheckResult] = []
    results.extend(check_architecture(root))
    results.extend(check_structure(root))
    results.extend(check_security(root))
    results.extend(check_documentation(root))
    results.extend(check_contracts(root))
    results.extend(check_promogg_preserved(root))
    results.extend(check_git(root))
    return tuple(results)


def check_architecture(root: Path) -> tuple[CheckResult, ...]:
    py_files = _python_files(root / "empresa_gpt")
    banned_imports = []
    core_banned_imports = []
    for path in py_files:
        imports = _imports_in_file(path)
        rel = _rel(root, path)
        for name in imports:
            root_name = name.split(".", 1)[0]
            if root_name in rules.BANNED_PROMOGG_IMPORT_ROOTS:
                banned_imports.append(f"{rel}: {name}")
            if rel.startswith("empresa_gpt/core/") and root_name in rules.BANNED_CORE_IMPORT_ROOTS:
                core_banned_imports.append(f"{rel}: {name}")

    promogg_imports = []
    for path in root.glob("*.py"):
        imports = _imports_in_file(path)
        if any(name == "empresa_gpt" or name.startswith("empresa_gpt.") for name in imports):
            promogg_imports.append(_rel(root, path))

    return (
        make_result(
            "Arquitetura",
            "EmpresaGPT sem imports exclusivos do Promogg",
            not banned_imports,
            "Nenhum import proibido encontrado." if not banned_imports else "; ".join(banned_imports[:8]),
            "Remover dependencia direta e criar adaptador futuro.",
            severity="critico",
            files=[item.split(":", 1)[0] for item in banned_imports[:8]],
        ),
        make_result(
            "Arquitetura",
            "Core sem dependencia do Promogg",
            not core_banned_imports,
            "Core independente." if not core_banned_imports else "; ".join(core_banned_imports[:8]),
            "Manter core livre de dominio Promogg, Mercado Livre, afiliados e painel.",
            severity="critico",
            files=[item.split(":", 1)[0] for item in core_banned_imports[:8]],
        ),
        make_result(
            "Arquitetura",
            "Promogg sem import estatico de EmpresaGPT",
            not promogg_imports,
            "Nenhum modulo raiz do Promogg importa EmpresaGPT estaticamente." if not promogg_imports else "; ".join(promogg_imports),
            "Usar apenas ponte CLI preguicosa ou adaptador futuro aprovado por ADR/RFC.",
            severity="alerta",
            files=promogg_imports,
        ),
    )


def check_structure(root: Path) -> tuple[CheckResult, ...]:
    required = (
        *rules.REQUIRED_ROOT_DOCUMENTS,
        *rules.REQUIRED_ADRS,
        *rules.REQUIRED_MANUAL_DOCUMENTS,
        *rules.REQUIRED_CONTRACTS,
    )
    missing = [path for path in required if not (root / path).exists()]
    return (
        make_result(
            "Estrutura",
            "Documentos, ADRs e contratos obrigatorios",
            not missing,
            f"{len(required) - len(missing)}/{len(required)} artefatos encontrados." if not missing else "Ausentes: " + ", ".join(missing),
            "Criar ou restaurar artefatos fundadores da EmpresaGPT.",
            severity="bloqueante",
            files=missing,
        ),
    )


def check_security(root: Path) -> tuple[CheckResult, ...]:
    risky_names = []
    risky_text = []
    public_risky_text = []
    for path in _security_review_files(root):
        rel = _rel(root, path)
        lower_name = path.name.lower()
        if lower_name in rules.SENSITIVE_FILENAMES or lower_name.endswith(rules.SENSITIVE_SUFFIXES):
            risky_names.append(rel)
        if path.is_file() and _is_text_file(path):
            text = _read_text(path).lower()
            hits = _sensitive_hits(text, public=rel.startswith(("site/", "dist_site/")))
            documentation_context = path.suffix.lower() in {".md", ".example"} or "/docs/" in rel
            if hits and not documentation_context and path.name not in rules.ALLOWED_SENSITIVE_TEXT_FILES:
                risky_text.append(f"{rel}: {', '.join(hits[:4])}")
            if rel.startswith(("site/", "dist_site/")) and hits:
                public_risky_text.append(f"{rel}: {', '.join(hits[:4])}")

    return (
        make_result(
            "Seguranca",
            "Arquivos sensiveis por nome",
            not risky_names,
            "Nenhum nome sensivel encontrado em area revisavel." if not risky_names else "; ".join(risky_names[:10]),
            "Remover do Git/area versionavel e manter ignorado.",
            severity="critico",
            files=risky_names[:10],
        ),
        make_result(
            "Seguranca",
            "Padroes sensiveis em texto",
            not risky_text,
            "Nenhum padrao sensivel inesperado encontrado." if not risky_text else "; ".join(risky_text[:10]),
            "Sanitizar conteudo ou mover para arquivo local ignorado.",
            severity="bloqueante",
            files=[item.split(":", 1)[0] for item in risky_text[:10]],
        ),
        make_result(
            "Seguranca",
            "Site e dist_site sem padroes sensiveis",
            not public_risky_text,
            "Artefatos publicos sem padroes sensiveis detectados." if not public_risky_text else "; ".join(public_risky_text[:10]),
            "Regenerar artefatos publicos apenas com dados sanitizados.",
            severity="critico",
            files=[item.split(":", 1)[0] for item in public_risky_text[:10]],
        ),
    )


def check_documentation(root: Path) -> tuple[CheckResult, ...]:
    missing_readmes = []
    incomplete_readmes = []
    for area in rules.QUALITY_AREAS:
        readme = root / "empresa_gpt" / area / "README.md"
        if not readme.exists():
            missing_readmes.append(_rel(root, readme))
            continue
        text = _read_text(readme).lower()
        missing_terms = [term for term in rules.README_REQUIRED_TERMS if term not in text]
        if missing_terms:
            incomplete_readmes.append(f"{_rel(root, readme)}: {', '.join(missing_terms)}")

    return (
        make_result(
            "Documentacao",
            "README por area",
            not missing_readmes,
            "Todas as areas possuem README." if not missing_readmes else "Ausentes: " + ", ".join(missing_readmes),
            "Criar README com responsabilidade, entradas, saidas, erros, seguranca e uso futuro.",
            severity="bloqueante",
            files=missing_readmes,
        ),
        make_result(
            "Documentacao",
            "README com secoes minimas",
            not incomplete_readmes,
            "READMEs contem termos minimos esperados." if not incomplete_readmes else "; ".join(incomplete_readmes[:10]),
            "Completar README da area com responsabilidades, entradas, saidas, erros, seguranca e uso futuro.",
            severity="alerta",
            files=[item.split(":", 1)[0] for item in incomplete_readmes[:10]],
        ),
    )


def check_contracts(root: Path) -> tuple[CheckResult, ...]:
    missing = [path for path in rules.REQUIRED_CONTRACTS if not (root / path).exists()]
    cmd = [
        sys.executable,
        "-c",
        "import json; "
        "mods = ['empresa_gpt.core.config','empresa_gpt.security','empresa_gpt.ai','empresa_gpt.storage','empresa_gpt.analytics','empresa_gpt.monitoring','empresa_gpt.services']; "
        "[__import__(m) for m in mods]; "
        "print(json.dumps({'ok': True, 'modules': mods}))",
    ]
    proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True, check=False)
    imports_ok = proc.returncode == 0
    evidence = "Contratos importados sem erro." if imports_ok else (proc.stderr or proc.stdout).strip()[:500]

    return (
        make_result(
            "Contratos",
            "Contratos obrigatorios existem",
            not missing,
            "Todos os contratos obrigatorios existem." if not missing else "Ausentes: " + ", ".join(missing),
            "Criar stubs contratuais inertes para a area ausente.",
            severity="bloqueante",
            files=missing,
        ),
        make_result(
            "Contratos",
            "Contratos importaveis sem side effects",
            imports_ok,
            evidence,
            "Corrigir imports dos contratos para nao depender de runtime do Promogg.",
            severity="critico",
            files=rules.REQUIRED_CONTRACTS,
        ),
    )


def check_promogg_preserved(root: Path) -> tuple[CheckResult, ...]:
    source = _read_text(root / "ia_promocoes.py")
    missing = [command for command in rules.PROMOGG_ESSENTIAL_COMMANDS if f'"{command}"' not in source and f"'{command}'" not in source]
    return (
        make_result(
            "Promogg preservado",
            "Comandos essenciais registrados no CLI",
            not missing,
            "Comandos essenciais encontrados sem execucao." if not missing else "Ausentes: " + ", ".join(missing),
            "Restaurar registro do comando no CLI sem executa-lo.",
            severity="bloqueante",
            files=("ia_promocoes.py",),
        ),
    )


def check_git(root: Path) -> tuple[CheckResult, ...]:
    proc = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, check=False)
    if proc.returncode:
        return (
            make_result(
                "Git",
                "Status do Git",
                False,
                "git status falhou.",
                "Verificar instalacao e repositorio Git.",
                severity="alerta",
            ),
        )
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    untracked = [line for line in lines if line.startswith("??")]
    sensitive = []
    reports = []
    large = []
    for line in lines:
        path = line[3:].strip() if len(line) > 3 else line.strip()
        name = Path(path).name
        if name.startswith("RELATORIO_") and name not in rules.GIT_ALLOWED_REPORTS:
            reports.append(path)
        if name.lower() in rules.SENSITIVE_FILENAMES or name.lower().endswith(rules.SENSITIVE_SUFFIXES):
            sensitive.append(path)
        full = root / path
        try:
            if full.is_file() and full.stat().st_size > rules.MAX_REVIEW_FILE_BYTES:
                large.append(f"{path} ({full.stat().st_size} bytes)")
        except OSError:
            pass

    return (
        make_result(
            "Git",
            "Alteracoes pendentes",
            not lines,
            "Arvore limpa." if not lines else f"{len(lines)} alteracao(oes), {len(untracked)} nao rastreada(s).",
            "Revisar diff antes de commit. Aviso esperado durante desenvolvimento.",
            severity="alerta",
            files=[line[3:].strip() for line in lines[:20]],
        ),
        make_result(
            "Git",
            "Arquivos sensiveis no status",
            not sensitive,
            "Nenhum arquivo sensivel no status." if not sensitive else "; ".join(sensitive),
            "Remover da area versionavel e revisar .gitignore.",
            severity="critico",
            files=sensitive,
        ),
        make_result(
            "Git",
            "Relatorios permitidos",
            not reports,
            "Somente relatorios permitidos aparecem no status." if not reports else "; ".join(reports),
            "Mover relatorio operacional para docs/historico ou manter ignorado.",
            severity="alerta",
            files=reports,
        ),
        make_result(
            "Git",
            "Arquivos grandes",
            not large,
            "Nenhum arquivo grande pendente detectado." if not large else "; ".join(large),
            "Evitar versionar artefatos grandes; usar storage apropriado.",
            severity="alerta",
            files=[item.split(" ", 1)[0] for item in large],
        ),
    )


def _python_files(base: Path) -> tuple[Path, ...]:
    if not base.exists():
        return ()
    return tuple(path for path in base.rglob("*.py") if "__pycache__" not in path.parts)


def _imports_in_file(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return set()
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def _security_review_files(root: Path) -> tuple[Path, ...]:
    files = set(_git_visible_files(root))
    for folder in ("site", "dist_site"):
        base = root / folder
        if base.exists():
            files.update(_reviewable_files(base))
    return tuple(sorted(files))


def _git_visible_files(root: Path) -> tuple[Path, ...]:
    proc = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=root, capture_output=True, text=True, check=False)
    if proc.returncode:
        return ()
    return tuple(root / line.strip() for line in proc.stdout.splitlines() if line.strip())


def _reviewable_files(root: Path) -> tuple[Path, ...]:
    ignored_parts = {".git", "venv", "__pycache__", ".pytest_cache", "logs", "backups", "perfil_mercadolivre", "perfil_mercadolivre_backup"}
    files = []
    for path in root.rglob("*"):
        if any(part in ignored_parts for part in path.parts):
            continue
        if path.is_file():
            files.append(path)
    return tuple(files)


def _sensitive_hits(text: str, *, public: bool = False) -> list[str]:
    hits = []
    regexes = {
        "secret_assignment": r"(client_secret|api_key|password|telegram_bot_token|refresh_token|access_token|secret_key)\s*[:=]\s*['\"](?=[^'\"]{24,})(?=[^'\"]*[0-9])[^'\"]+['\"]",
        "bearer_token": r"authorization\s*[:=]\s*['\"]?bearer\s+[a-z0-9._-]{20,}",
        "set_cookie": r"set-cookie\s*[:=]",
    }
    for name, pattern in regexes.items():
        if re.search(pattern, text, flags=re.IGNORECASE):
            hits.append(name)
    if public:
        for marker in ("refresh_token", "access_token", "telegram_bot_token", "client_secret"):
            if marker in text:
                hits.append(marker)
    return hits


def _is_text_file(path: Path) -> bool:
    if path.stat().st_size > rules.MAX_REVIEW_FILE_BYTES:
        return False
    return path.suffix.lower() in {"", ".py", ".md", ".txt", ".json", ".js", ".sql", ".toml", ".yml", ".yaml", ".html", ".css", ".example"}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()
