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
    results.extend(check_promogg_product_surface(root))
    results.extend(check_operations_center(root))
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
    modules = ",".join(f"'{module}'" for module in rules.REQUIRED_CONTRACT_PACKAGES)
    cmd = [
        sys.executable,
        "-c",
        "import json; "
        f"mods = [{modules}]; "
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


def check_promogg_product_surface(root: Path) -> tuple[CheckResult, ...]:
    index_path = _first_existing(root, ("site/index.html", "dist_site/index.html"))
    index_text = _read_text(index_path).lower() if index_path else ""
    style_path = _first_existing(root, ("site/style.css", "dist_site/style.css"))
    style_text = _read_text(style_path).lower() if style_path else ""
    script_path = _first_existing(root, ("site/app.js", "dist_site/app.js"))
    script_text = _read_text(script_path).lower() if script_path else ""
    catalog_path = _first_existing(root, ("site/ofertas.json", "dist_site/ofertas.json", "catalogo_publico/ofertas.json"))
    catalog = _load_json(catalog_path) if catalog_path else None

    missing_home = []
    for label, signals in rules.PROMOGG_HOME_REQUIRED_SIGNALS:
        if not any(signal in index_text for signal in signals):
            missing_home.append(label)

    seo_missing = []
    for label, signals in rules.PROMOGG_SEO_REQUIRED_SIGNALS:
        if not any(signal in index_text for signal in signals):
            seo_missing.append(label)
    for filename, label in (("sitemap.xml", "Sitemap"), ("robots.txt", "Robots")):
        if not (root / "site" / filename).exists() and not (root / "dist_site" / filename).exists():
            seo_missing.append(label)

    cards_missing = _cards_missing_fields(catalog)
    link_issues, image_issues = _catalog_asset_issues(catalog)
    category_dirs = [path for base in (root / "site" / "categoria", root / "dist_site" / "categoria") if base.exists() for path in base.iterdir() if path.is_dir()]
    missing_experience_docs = [path for path in rules.PROMOGG_EXPERIENCE_REQUIRED_DOCUMENTS if not (root / path).exists()]
    plan_issues = _experience_plan_issues(root)
    v2_sources = {
        "index": index_text,
        "style": style_text,
        "script": script_text,
    }
    v2_missing = {
        label: [signal for source, signal in signals if signal not in v2_sources.get(source, "")]
        for label, signals in rules.PROMOGG_V2_IMPLEMENTATION_SIGNALS.items()
    }
    v2_missing = {label: signals for label, signals in v2_missing.items() if signals}

    return (
        make_result(
            "Produto Promogg",
            "UX Audit e Design System documentados",
            not missing_experience_docs,
            "Documentos de Experience V2 encontrados." if not missing_experience_docs else "Ausentes: " + ", ".join(missing_experience_docs),
            "Criar PROMOGG_UX_AUDIT.md e empresa_gpt/docs/PROMOGG_DESIGN_SYSTEM.md antes da implementacao.",
            severity="bloqueante",
            files=missing_experience_docs,
        ),
        make_result(
            "Produto Promogg",
            "Planos V2 completos",
            not plan_issues,
            "Design System, Cards Premium, Home e Painel de Confianca planejados." if not plan_issues else "; ".join(plan_issues),
            "Completar planejamento textual antes de implementar a Promogg Experience V2.",
            severity="alerta",
            files=rules.PROMOGG_EXPERIENCE_REQUIRED_DOCUMENTS,
        ),
        make_result(
            "Produto Promogg",
            "Home completa planejada",
            not missing_home,
            "Home contem sinais de produto esperados." if not missing_home else "Ausentes ou nao detectados: " + ", ".join(missing_home),
            "Planejar implementacao futura das secoes de home pelo Product Intelligence Engine.",
            severity="alerta",
            files=tuple(filter(None, (_rel(root, index_path) if index_path else None,))),
        ),
        make_result(
            "Produto Promogg",
            "Cards completos",
            not cards_missing,
            "Cards possuem campos essenciais detectados." if not cards_missing else "; ".join(cards_missing[:8]),
            "Garantir titulo, preco, link e imagem nos cards em adaptador futuro.",
            severity="alerta",
            files=tuple(filter(None, (_rel(root, catalog_path) if catalog_path else None,))),
        ),
        make_result(
            "Produto Promogg",
            "Links validos",
            not link_issues,
            "Links de catalogo parecem validos." if not link_issues else "; ".join(link_issues[:8]),
            "Revisar links vazios, javascript, anchors soltos ou URLs nao publicas.",
            severity="alerta",
            files=tuple(filter(None, (_rel(root, catalog_path) if catalog_path else None,))),
        ),
        make_result(
            "Produto Promogg",
            "Imagens validas",
            not image_issues,
            "Imagens de catalogo parecem validas." if not image_issues else "; ".join(image_issues[:8]),
            "Revisar imagens vazias, placeholders ou URLs nao publicas.",
            severity="alerta",
            files=tuple(filter(None, (_rel(root, catalog_path) if catalog_path else None,))),
        ),
        make_result(
            "Produto Promogg",
            "SEO valido",
            not seo_missing,
            "SEO basico detectado." if not seo_missing else "Ausentes ou nao detectados: " + ", ".join(seo_missing),
            "Projetar Open Graph, Schema.org, sitemap, canonical, robots, meta description, title e Twitter Cards.",
            severity="alerta",
            files=tuple(filter(None, (_rel(root, index_path) if index_path else None,))),
        ),
        make_result(
            "Produto Promogg",
            "Promogg Experience V2 implementada",
            not v2_missing,
            "Hero, Cards Premium, estados vazios, responsividade e SEO basico detectados." if not v2_missing else "; ".join(f"{label}: {', '.join(signals)}" for label, signals in v2_missing.items()),
            "Implementar os sinais minimos da Promogg V2 em site/index.html, site/style.css e site/app.js.",
            severity="bloqueante",
            files=tuple(filter(None, (
                _rel(root, index_path) if index_path else None,
                _rel(root, style_path) if style_path else None,
                _rel(root, script_path) if script_path else None,
            ))),
        ),
        make_result(
            "Produto Promogg",
            "Estrutura de categorias",
            bool(category_dirs),
            f"{len(category_dirs)} categoria(s) detectada(s)." if category_dirs else "Nenhuma estrutura de categoria detectada em site/ ou dist_site/.",
            "Garantir paginas de categoria para descoberta, SEO e navegacao.",
            severity="alerta",
            files=[_rel(root, path) for path in category_dirs[:8]],
        ),
    )


def check_operations_center(root: Path) -> tuple[CheckResult, ...]:
    missing_files = [path for path in rules.EGOC_REQUIRED_FILES if not (root / path).exists()]
    contracts_text = _read_text(root / "empresa_gpt/operations/contracts.py")
    models_text = _read_text(root / "empresa_gpt/operations/models.py")
    dashboard_text = _read_text(root / "empresa_gpt/operations/dashboard.py")
    doc_text = _read_text(root / "EMPRESAGPT_OPERATIONS_CENTER.md").lower()

    missing_contracts = [name for name in rules.EGOC_REQUIRED_CONTRACTS if name not in contracts_text]
    missing_models = [name for name in rules.EGOC_REQUIRED_MODELS if f"class {name}" not in models_text]
    missing_dashboard = [term for term in rules.EGOC_DASHBOARD_TERMS if term not in dashboard_text]
    missing_docs = [term for term in ("objetivos", "arquitetura", "fluxos", "contratos", "responsabilidades", "escalabilidade", "integracao futura") if term not in doc_text]

    operations_imports = []
    for path in _python_files(root / "empresa_gpt" / "operations"):
        imports = _imports_in_file(path)
        rel = _rel(root, path)
        for name in imports:
            root_name = name.split(".", 1)[0]
            if root_name in rules.BANNED_PROMOGG_IMPORT_ROOTS:
                operations_imports.append(f"{rel}: {name}")

    proc = subprocess.run(
        [sys.executable, "-c", "import empresa_gpt.operations; print('ok')"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    import_ok = proc.returncode == 0

    return (
        make_result(
            "EGOC",
            "EGOC documentado e estruturado",
            not missing_files and not missing_docs,
            "EGOC possui arvore e documento fundador." if not missing_files and not missing_docs else "Ausentes: " + ", ".join((*missing_files, *missing_docs)),
            "Criar estrutura oficial e EMPRESAGPT_OPERATIONS_CENTER.md com objetivos, arquitetura, fluxos, contratos, responsabilidades, escalabilidade e integracao futura.",
            severity="bloqueante",
            files=missing_files,
        ),
        make_result(
            "EGOC",
            "Contratos existentes",
            not missing_contracts,
            "Contratos EGOC encontrados." if not missing_contracts else "Ausentes: " + ", ".join(missing_contracts),
            "Definir contratos do Operations Center sem runtime.",
            severity="bloqueante",
            files=("empresa_gpt/operations/contracts.py",),
        ),
        make_result(
            "EGOC",
            "Modelos existentes",
            not missing_models,
            "Modelos EGOC encontrados." if not missing_models else "Ausentes: " + ", ".join(missing_models),
            "Definir Product, Service, Metric, Health, Risk, Audit, Backup e Alert.",
            severity="bloqueante",
            files=("empresa_gpt/operations/models.py",),
        ),
        make_result(
            "EGOC",
            "Sem dependencia do Promogg",
            not operations_imports,
            "Operations Center nao importa runtime Promogg." if not operations_imports else "; ".join(operations_imports),
            "Remover qualquer dependencia de produto especifico do EGOC.",
            severity="critico",
            files=[item.split(":", 1)[0] for item in operations_imports[:8]],
        ),
        make_result(
            "EGOC",
            "Sem side effects",
            import_ok,
            "empresa_gpt.operations importavel sem erro." if import_ok else (proc.stderr or proc.stdout).strip()[:500],
            "Manter imports inertes e sem acesso a servicos reais.",
            severity="critico",
            files=("empresa_gpt/operations/__init__.py",),
        ),
        make_result(
            "EGOC",
            "Arquitetura valida",
            not missing_dashboard,
            "Dashboard cobre EmpresaGPT, produtos, saude, servicos, backups, alertas, auditorias, qualidade, riscos e uso de recursos." if not missing_dashboard else "Ausentes: " + ", ".join(missing_dashboard),
            "Completar a arvore declarativa do dashboard EGOC.",
            severity="bloqueante",
            files=("empresa_gpt/operations/dashboard.py",),
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


def _first_existing(root: Path, candidates: tuple[str, ...]) -> Path | None:
    for candidate in candidates:
        path = root / candidate
        if path.exists():
            return path
    return None


def _load_json(path: Path | None):
    if not path:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def _catalog_items(catalog) -> list[dict]:
    if isinstance(catalog, list):
        return [item for item in catalog if isinstance(item, dict)]
    if isinstance(catalog, dict):
        for key in ("ofertas", "items", "produtos", "data"):
            value = catalog.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _cards_missing_fields(catalog) -> list[str]:
    items = _catalog_items(catalog)
    if not items:
        return ["catalogo indisponivel ou vazio"]
    issues = []
    required_groups = {
        "titulo": ("titulo", "title", "nome"),
        "preco": ("preco", "preco_atual", "price"),
        "link": ("link", "url", "permalink"),
        "imagem": ("imagem", "imagem_url", "image", "thumbnail"),
    }
    for index, item in enumerate(items[:20], start=1):
        missing = [label for label, keys in required_groups.items() if not any(item.get(key) for key in keys)]
        if missing:
            issues.append(f"item {index}: {', '.join(missing)}")
    return issues


def _catalog_asset_issues(catalog) -> tuple[list[str], list[str]]:
    items = _catalog_items(catalog)
    if not items:
        return ["catalogo indisponivel ou vazio"], ["catalogo indisponivel ou vazio"]
    link_issues = []
    image_issues = []
    for index, item in enumerate(items[:50], start=1):
        link = str(item.get("link") or item.get("url") or item.get("permalink") or "").strip().lower()
        image = str(item.get("imagem") or item.get("imagem_url") or item.get("image") or item.get("thumbnail") or "").strip().lower()
        if not link or link.startswith(("#", "javascript:")):
            link_issues.append(f"item {index}: link vazio/invalido")
        if link and not (link.startswith("http://") or link.startswith("https://") or link.startswith("/")):
            link_issues.append(f"item {index}: link nao publico")
        if not image or "placeholder" in image:
            image_issues.append(f"item {index}: imagem vazia/placeholder")
        if image and not (image.startswith("http://") or image.startswith("https://") or image.startswith("/") or image.startswith("data:image/")):
            image_issues.append(f"item {index}: imagem nao publica")
    return link_issues, image_issues


def _experience_plan_issues(root: Path) -> list[str]:
    combined = []
    for path in rules.PROMOGG_EXPERIENCE_REQUIRED_DOCUMENTS:
        combined.append(_read_text(root / path).lower())
    text = "\n".join(combined)
    issues = []
    for label, terms in rules.PROMOGG_EXPERIENCE_PLAN_TERMS.items():
        missing = [term for term in terms if term not in text]
        if missing:
            issues.append(f"{label}: ausentes {', '.join(missing)}")
    return issues
