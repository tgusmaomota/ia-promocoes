"""Auditoria de segurança para publicação estática do Promogg.

O objetivo é bloquear publicação automática quando Git, site ou artefatos
públicos contenham dados sensíveis, caminhos locais ou campos internos.
"""

import fnmatch
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path


RELATORIO = Path("RELATORIO_AUDITORIA_SEGURANCA_PUBLICACAO.md")

REQUIRED_GITIGNORE = [
    ".env",
    ".env.*",
    "!.env.example",
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    "banco.db",
    "venv/",
    "__pycache__/",
    "*.pyc",
    "perfil_mercadolivre/",
    "perfil_mercadolivre_backup/",
    "backups/",
    "logs/",
    "*.log",
    ".coleta_confiavel_checkpoint.json",
    ".afiliados_checkpoint.json",
    "*.session",
    "*.cookies",
    "storage_state.json",
    "playwright/.auth/",
    "relatorios_privados/",
]

SENSITIVE_TRACKED_PATTERNS = [
    ".env",
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    "banco.db",
    "promocoes.db",
    "venv/*",
    "perfil_mercadolivre/*",
    "perfil_mercadolivre_backup/*",
    "backups/*",
    "logs/*",
    "*.log",
    ".coleta_confiavel_checkpoint.json",
    ".afiliados_checkpoint.json",
    "*.session",
    "*.cookies",
    "storage_state.json",
    "playwright/.auth/*",
]

PUBLIC_FORBIDDEN_FILE_PATTERNS = [
    ".env",
    "*.env",
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    "*.log",
    "*.session",
    "*.cookies",
    "storage_state.json",
    ".coleta_confiavel_checkpoint.json",
    ".afiliados_checkpoint.json",
]

SECRET_VALUE_PATTERNS = [
    ("telegram_bot_token", re.compile(r"\b\d{6,}:[A-Za-z0-9_-]{20,}\b")),
    ("bearer_token", re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{20,}")),
    ("authorization_header", re.compile(r"(?i)\bAuthorization\s*:\s*(?:Bearer|Basic)\s+[^\\s\"']{12,}")),
    ("local_user_path", re.compile(r"/Users/[^\\s\"'<>]+")),
    ("aws_like_secret", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
]

ASSIGNMENT_SECRET_RE = re.compile(
    r"(?i)\b(?:access_token|refresh_token|client_secret|telegram_bot_token|bot_token|api_key|apikey|password|senha)\b"
    r"[ \t]*[:=][ \t]*[\"']?([^\"'\s,}]+)"
)

PUBLIC_JSON_FORBIDDEN_KEYS = {
    "status",
    "motivo_rejeicao",
    "motivo",
    "score",
    "score_interno",
    "observacao",
    "observacao_interna",
    "logs",
    "log",
    "fonte_privada",
    "token",
    "access_token",
    "refresh_token",
    "client_secret",
    "chat_id",
    "erro_api",
    "payload",
    "payload_bruto",
    "caminho_local",
    "banco",
    "sqlite",
}

ENV_EXAMPLE_SECRET_KEYS = {
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "TELEGRAM_ALERT_CHAT_ID",
    "MELI_CLIENT_SECRET",
    "MELI_ACCESS_TOKEN",
    "MELI_REFRESH_TOKEN",
}

TEXT_EXTENSIONS = {
    ".html",
    ".js",
    ".css",
    ".json",
    ".xml",
    ".txt",
    ".md",
    ".csv",
    ".toml",
    ".svg",
}


def agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _git(args):
    proc = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    return proc.stdout.splitlines() if proc.returncode == 0 else []


def _match_any(path, patterns):
    valor = str(path).replace("\\", "/")
    return any(fnmatch.fnmatch(valor, pat) or valor == pat.rstrip("/") for pat in patterns)


def _add(resultado, nivel, escopo, arquivo, mensagem):
    resultado[nivel].append({
        "escopo": escopo,
        "arquivo": str(arquivo),
        "mensagem": mensagem,
    })


def _read_text(path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _scan_secret_values(texto):
    achados = []
    for nome, regex in SECRET_VALUE_PATTERNS:
        if regex.search(texto):
            achados.append(nome)
    for match in ASSIGNMENT_SECRET_RE.finditer(texto):
        valor = (match.group(1) or "").strip()
        if valor and valor not in {"", "''", '""', "SEU_TOKEN", "TOKEN_AQUI", "exemplo", "changeme"}:
            if len(valor) >= 8:
                achados.append("secret_assignment")
    return sorted(set(achados))


def _iter_files(base):
    base = Path(base)
    if not base.exists():
        return []
    return [p for p in base.rglob("*") if p.is_file()]


def _walk_json_keys(obj, prefix=""):
    keys = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            caminho = f"{prefix}.{key}" if prefix else str(key)
            keys.append((str(key), caminho))
            keys.extend(_walk_json_keys(value, caminho))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj[:5]):
            keys.extend(_walk_json_keys(value, f"{prefix}[{idx}]"))
    return keys


def auditar_git(resultado):
    tracked = _git(["ls-files"])
    resultado["metricas"]["git_versionados"] = len(tracked)
    for arquivo in tracked:
        if arquivo == ".env.example":
            continue
        if _match_any(arquivo, SENSITIVE_TRACKED_PATTERNS):
            _add(resultado, "critico", "git", arquivo, "arquivo sensível está versionado")

    suspeitos = [
        arquivo for arquivo in tracked
        if re.search(r"(?i)(env|token|secret|cookie|session|perfil|sqlite|banco|backup|log|checkpoint|oauth|refresh|access)", arquivo)
    ]
    resultado["metricas"]["git_nomes_suspeitos"] = len(suspeitos)
    for arquivo in suspeitos:
        if arquivo == ".env.example":
            continue
        if arquivo.endswith((".py", ".md", ".txt", ".csv", ".html", ".svg", ".png")):
            continue
        _add(resultado, "alerta", "git", arquivo, "nome sugere dado sensível; revisar se é público")


def auditar_gitignore(resultado):
    texto = _read_text(Path(".gitignore"))
    presentes = {linha.strip() for linha in texto.splitlines() if linha.strip() and not linha.strip().startswith("#")}
    faltantes = [padrao for padrao in REQUIRED_GITIGNORE if padrao not in presentes]
    resultado["metricas"]["gitignore_faltantes"] = len(faltantes)
    for padrao in faltantes:
        _add(resultado, "bloqueante", ".gitignore", ".gitignore", f"padrão obrigatório ausente: {padrao}")


def auditar_env_example(resultado):
    path = Path(".env.example")
    if not path.exists():
        _add(resultado, "bloqueante", "env", path, ".env.example ausente")
        return
    for linha in _read_text(path).splitlines():
        if not linha.strip() or linha.lstrip().startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        chave = chave.strip()
        valor = valor.strip()
        if chave in ENV_EXAMPLE_SECRET_KEYS and valor:
            _add(resultado, "critico", "env", path, f"{chave} tem valor no .env.example")
        if chave == "PROMOGG_SUPERVISOR_PUBLICAR" and valor.lower() != "false":
            _add(resultado, "bloqueante", "env", path, "PROMOGG_SUPERVISOR_PUBLICAR deve permanecer false no exemplo")


def auditar_publico(resultado, pasta):
    arquivos = _iter_files(pasta)
    resultado["metricas"][f"{pasta}_arquivos"] = len(arquivos)
    for path in arquivos:
        rel = path.as_posix()
        if _match_any(path.name, PUBLIC_FORBIDDEN_FILE_PATTERNS):
            _add(resultado, "critico", pasta, rel, "arquivo proibido em pasta pública")
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        texto = _read_text(path)
        for achado in _scan_secret_values(texto):
            # Nomes vazios de variáveis em documentação pública não entram aqui.
            _add(resultado, "critico" if achado != "local_user_path" else "bloqueante", pasta, rel, f"padrão sensível encontrado: {achado}")
        if path.suffix.lower() == ".json":
            try:
                dados = json.loads(texto)
            except json.JSONDecodeError:
                _add(resultado, "bloqueante", pasta, rel, "JSON público inválido")
                continue
            proibidas = sorted({caminho for key, caminho in _walk_json_keys(dados) if key in PUBLIC_JSON_FORBIDDEN_KEYS})
            for caminho in proibidas[:20]:
                _add(resultado, "bloqueante", pasta, rel, f"campo interno/proibido no JSON público: {caminho}")


def auditar_relatorios(resultado):
    arquivos = []
    for padrao in ("RELATORIO_*.md", "README_*.md", "COMANDOS_*.md", "MANUTENCAO_*.md", "PRODUCAO_*.md", "*.txt"):
        arquivos.extend(Path(".").glob(padrao))
    vistos = set()
    unicos = []
    for path in arquivos:
        if path.as_posix() not in vistos and path.is_file():
            vistos.add(path.as_posix())
            unicos.append(path)
    resultado["metricas"]["relatorios_auditados"] = len(unicos)
    for path in unicos:
        texto = _read_text(path)
        achados = _scan_secret_values(texto)
        for achado in achados:
            severidade = "bloqueante" if achado == "local_user_path" else "critico"
            _add(resultado, severidade, "relatorios", path, f"padrão sensível encontrado: {achado}")


def auditar_python(resultado):
    arquivos = [p for p in Path(".").glob("*.py") if p.is_file()]
    resultado["metricas"]["python_auditados"] = len(arquivos)
    for path in arquivos:
        texto = _read_text(path)
        for achado in _scan_secret_values(texto):
            # Código pode conter regex/nomes de variáveis; só chaves reais devem bloquear.
            if achado in {"telegram_bot_token", "private_key", "aws_like_secret"}:
                _add(resultado, "critico", "python", path, f"valor sensível literal encontrado: {achado}")


def status_final(resultado):
    if resultado["critico"]:
        return "critico"
    if resultado["bloqueante"]:
        return "bloqueante"
    if resultado["alerta"]:
        return "alerta"
    return "ok"


def _escrever_relatorio(resultado):
    linhas = [
        "# Relatório de Auditoria de Segurança de Publicação",
        "",
        f"- Gerado em: {agora()}",
        f"- Status final: **{resultado['status_final']}**",
        f"- Críticos: {len(resultado['critico'])}",
        f"- Bloqueantes: {len(resultado['bloqueante'])}",
        f"- Alertas: {len(resultado['alerta'])}",
        "",
        "## Métricas",
    ]
    for chave, valor in sorted(resultado["metricas"].items()):
        linhas.append(f"- {chave}: {valor}")
    for nivel, titulo in (("critico", "Achados críticos"), ("bloqueante", "Achados bloqueantes"), ("alerta", "Alertas")):
        linhas += ["", f"## {titulo}"]
        itens = resultado[nivel]
        if not itens:
            linhas.append("- nenhum")
        else:
            for item in itens[:80]:
                linhas.append(f"- `{item['arquivo']}` ({item['escopo']}): {item['mensagem']}")
            if len(itens) > 80:
                linhas.append(f"- ... {len(itens) - 80} achados adicionais omitidos no relatório resumido")
    linhas += [
        "",
        "## Correções/garantias aplicadas",
        "- `.gitignore` reforçado para banco, SQLite, sessões, cookies, checkpoints, storage state, perfil Playwright, backups, logs e relatórios privados.",
        "- Auditoria automática criada no comando `python3 ia_promocoes.py auditar-seguranca-publicacao`.",
        "- Gate integrado ao supervisor e ao ciclo automático antes de liberar publicação.",
        "- Nenhum token, cookie ou segredo foi impresso neste relatório.",
        "",
        "## Decisão",
        "- Publicação automática é segura apenas quando não houver achados críticos nem bloqueantes.",
        f"- Seguro para publicar automaticamente agora: {'sim' if resultado['publicacao_segura'] else 'não'}",
    ]
    RELATORIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def auditar_seguranca_publicacao(escrever_relatorio=True):
    resultado = {
        "gerado_em": agora(),
        "critico": [],
        "bloqueante": [],
        "alerta": [],
        "metricas": {},
    }
    auditar_git(resultado)
    auditar_gitignore(resultado)
    auditar_env_example(resultado)
    auditar_publico(resultado, "site")
    auditar_publico(resultado, "dist_site")
    auditar_relatorios(resultado)
    auditar_python(resultado)
    resultado["status_final"] = status_final(resultado)
    resultado["publicacao_segura"] = resultado["status_final"] in {"ok", "alerta"}
    if escrever_relatorio:
        _escrever_relatorio(resultado)
    return resultado
