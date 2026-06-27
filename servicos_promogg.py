"""Gerenciador seguro de serviços do Promogg.

O modo padrão é econômico: nenhum serviço externo/custoso é iniciado sem
comando manual explícito. Este módulo controla processos conhecidos e flags de
habilitação para recursos que não são daemons permanentes, como Telegram e
deploy automático.
"""

from __future__ import annotations

import json
import os
import shlex
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


SERVICOS_DIR = Path(".promogg_servicos")
LOGS_DIR = Path("logs")
STATE_PATH = SERVICOS_DIR / "estado.json"
DEFAULT_TIMEOUT = 20


def _python_cmd():
    return str(Path("venv/bin/python")) if Path("venv/bin/python").exists() else sys.executable


SERVICOS = {
    "playwright": {
        "nome": "Playwright",
        "tipo": "flag",
        "custo": True,
        "descricao": "Habilita uso manual de Playwright; não abre navegador automaticamente.",
    },
    "supervisor": {
        "nome": "Supervisor",
        "tipo": "processo",
        "pid_file": SERVICOS_DIR / "supervisor.pid",
        "log": LOGS_DIR / "supervisor_loop.log",
        "args": ["ia_promocoes.py", "supervisor-loop"],
        "custo": True,
        "descricao": "Supervisor em loop. Pode consultar APIs/estado externo.",
    },
    "monitor": {
        "nome": "Monitor",
        "tipo": "processo",
        "pid_file": SERVICOS_DIR / "monitor.pid",
        "log": LOGS_DIR / "monitor.log",
        "args": ["ia_promocoes.py", "_worker-monitor"],
        "stop_file": SERVICOS_DIR / "monitor.stop",
        "custo": True,
        "descricao": "Monitoramento periódico de preços/API.",
    },
    "scheduler": {
        "nome": "Scheduler",
        "tipo": "processo",
        "pid_file": Path(".ia_promocoes.pid"),
        "log": LOGS_DIR / "producao.log",
        "args": ["ia_promocoes.py", "_worker-producao"],
        "stop_file": Path(".ia_promocoes.stop"),
        "custo": True,
        "descricao": "Ciclo de produção/coleta/publicação controlada.",
    },
    "telegram": {
        "nome": "Telegram",
        "tipo": "flag",
        "custo": True,
        "descricao": "Habilita publicação real de ofertas no Telegram.",
    },
    "tunnel": {
        "nome": "Cloudflare Tunnel",
        "tipo": "processo_env",
        "pid_file": SERVICOS_DIR / "tunnel.pid",
        "log": LOGS_DIR / "cloudflare_tunnel.log",
        "env_cmd": "PROMOGG_TUNNEL_COMMAND",
        "custo": True,
        "descricao": "Túnel remoto. Só inicia se PROMOGG_TUNNEL_COMMAND estiver configurado.",
    },
    "deploy": {
        "nome": "Deploy",
        "tipo": "flag",
        "custo": True,
        "descricao": "Habilita deploy automático; não publica no ato de habilitar.",
    },
    "painel": {
        "nome": "Painel",
        "tipo": "processo",
        "pid_file": Path(".promogg_painel.pid"),
        "log": LOGS_DIR / "painel.log",
        "args": ["-m", "streamlit", "run", "painel.py", "--server.headless", "true"],
        "custo": False,
        "descricao": "Painel Streamlit local.",
    },
    "site-local": {
        "nome": "Site local",
        "tipo": "processo",
        "pid_file": SERVICOS_DIR / "site_local.pid",
        "log": LOGS_DIR / "site_local.log",
        "args": ["servidor_site.py", "--porta", os.getenv("PROMOGG_SITE_LOCAL_PORTA", "8080")],
        "custo": False,
        "descricao": "Servidor local do site estático.",
    },
}

MODO_ESTAVEL_LOCAL = "MODO_ESTAVEL_LOCAL"
SERVICOS_ESTAVEIS_LOCAIS = {"painel", "site-local"}
SERVICOS_ECONOMICOS = {"painel", "site-local"}
FLAGS_DESLIGADAS_PADRAO = {"playwright", "telegram", "deploy"}
SERVICOS_PRODUCAO = {"painel", "site-local", "scheduler", "supervisor", "monitor", "playwright", "telegram", "deploy"}
SERVICOS_OPERACAO = {"painel", "site-local"}


def _agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _carregar_estado():
    if not STATE_PATH.exists():
        return {"modo": MODO_ESTAVEL_LOCAL, "atualizado_em": _agora(), "servicos": {}}
    try:
        estado = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        estado.setdefault("modo", MODO_ESTAVEL_LOCAL)
        estado.setdefault("servicos", {})
        return estado
    except (OSError, json.JSONDecodeError):
        return {"modo": MODO_ESTAVEL_LOCAL, "atualizado_em": _agora(), "servicos": {}}


def _salvar_estado(estado):
    SERVICOS_DIR.mkdir(exist_ok=True)
    estado["atualizado_em"] = _agora()
    STATE_PATH.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")


def _pid_ativo(pid):
    try:
        os.kill(int(pid), 0)
        estado = subprocess.run(["ps", "-p", str(pid), "-o", "stat="], capture_output=True, text=True, check=False).stdout.strip()
        return bool(estado) and "Z" not in estado
    except (OSError, ValueError, TypeError):
        return False


def _pid_do_arquivo(pid_file):
    try:
        pid = int(Path(pid_file).read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None
    return pid if _pid_ativo(pid) else None


def _metricas_pid(pid):
    if not pid:
        return {"cpu": None, "memoria": None, "tempo_ligado": None}
    saida = subprocess.run(
        ["ps", "-p", str(pid), "-o", "%cpu=,%mem=,etime="],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    if not saida:
        return {"cpu": None, "memoria": None, "tempo_ligado": None}
    partes = saida.split(None, 2)
    return {
        "cpu": partes[0] if len(partes) > 0 else None,
        "memoria": partes[1] if len(partes) > 1 else None,
        "tempo_ligado": partes[2] if len(partes) > 2 else None,
    }


def _flag_ativa(nome):
    estado = _carregar_estado()
    if nome in FLAGS_DESLIGADAS_PADRAO:
        return bool(estado["servicos"].get(nome, {}).get("habilitado", False))
    return bool(estado["servicos"].get(nome, {}).get("habilitado", False))


def _registrar(nome, **dados):
    estado = _carregar_estado()
    atual = estado["servicos"].setdefault(nome, {})
    atual.update(dados)
    atual["atualizado_em"] = _agora()
    _salvar_estado(estado)
    LOGS_DIR.mkdir(exist_ok=True)
    evento = dados.get("ultimo_evento") or dados.get("status") or "atualizado"
    with (LOGS_DIR / "servicos.log").open("a", encoding="utf-8") as log:
        log.write(f"{_agora()} {nome} {evento} pid={dados.get('pid') or '-'}\n")


def _args_servico(nome, cfg):
    if cfg["tipo"] == "processo_env":
        comando = os.getenv(cfg["env_cmd"], "").strip()
        return shlex.split(comando) if comando else []
    return [_python_cmd(), *cfg["args"]]


def iniciar_servico(nome):
    if nome not in SERVICOS:
        return {"ok": False, "mensagem": f"Serviço desconhecido: {nome}"}
    cfg = SERVICOS[nome]
    SERVICOS_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)

    if cfg["tipo"] == "flag":
        _registrar(nome, habilitado=True, status="ON", pid=None, ultimo_evento="habilitado manualmente")
        return {"ok": True, "mensagem": f"{cfg['nome']} habilitado. Nenhum processo foi iniciado."}

    pid_file = cfg["pid_file"]
    pid = _pid_do_arquivo(pid_file)
    if pid:
        _registrar(nome, habilitado=True, status="ON", pid=pid, ultimo_evento="já estava ativo")
        return {"ok": True, "mensagem": f"{cfg['nome']} já está ON. PID {pid}", "pid": pid}

    args = _args_servico(nome, cfg)
    if not args:
        _registrar(nome, habilitado=False, status="OFF", pid=None, ultimo_evento="comando não configurado")
        return {"ok": False, "mensagem": f"{cfg['nome']} não foi iniciado: comando não configurado."}

    with cfg["log"].open("a", encoding="utf-8") as log:
        processo = subprocess.Popen(
            args,
            cwd=Path.cwd(),
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    time.sleep(6)
    if processo.poll() is not None:
        pid_file.unlink(missing_ok=True)
        _registrar(nome, habilitado=False, status="OFF", pid=None, ultimo_evento=f"falhou ao iniciar codigo={processo.returncode}")
        return {
            "ok": False,
            "mensagem": f"{cfg['nome']} não ficou ativo. Veja {cfg['log']}.",
            "pid": None,
        }
    pid_file.write_text(str(processo.pid), encoding="utf-8")
    _registrar(nome, habilitado=True, status="ON", pid=processo.pid, iniciado_em=_agora(), ultimo_evento="iniciado manualmente")
    return {"ok": True, "mensagem": f"{cfg['nome']} iniciado. PID {processo.pid}", "pid": processo.pid}


def parar_servico(nome, timeout=DEFAULT_TIMEOUT):
    if nome not in SERVICOS:
        return {"ok": False, "mensagem": f"Serviço desconhecido: {nome}"}
    cfg = SERVICOS[nome]

    if cfg["tipo"] == "flag":
        _registrar(nome, habilitado=False, status="OFF", pid=None, ultimo_evento="desabilitado manualmente")
        return {"ok": True, "mensagem": f"{cfg['nome']} desabilitado."}

    pid_file = cfg["pid_file"]
    if cfg.get("stop_file"):
        cfg["stop_file"].write_text("parar\n", encoding="utf-8")
    pid = _pid_do_arquivo(pid_file)
    if not pid:
        pid_file.unlink(missing_ok=True)
        _registrar(nome, habilitado=False, status="OFF", pid=None, ultimo_evento="já estava parado")
        return {"ok": True, "mensagem": f"{cfg['nome']} já estava OFF."}

    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass

    fim = time.time() + max(1, int(timeout))
    while time.time() < fim:
        if not _pid_ativo(pid):
            break
        time.sleep(0.5)

    if _pid_ativo(pid):
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass

    pid_file.unlink(missing_ok=True)
    _registrar(nome, habilitado=False, status="OFF", pid=None, encerrado_em=_agora(), ultimo_evento="parado manualmente")
    return {"ok": True, "mensagem": f"{cfg['nome']} parado."}


def reiniciar_servico(nome):
    parada = parar_servico(nome)
    if not parada["ok"]:
        return parada
    return iniciar_servico(nome)


def status_servicos():
    estado = _carregar_estado()
    resultado = []
    for nome, cfg in SERVICOS.items():
        pid = _pid_do_arquivo(cfg["pid_file"]) if cfg["tipo"] != "flag" else None
        flag = _flag_ativa(nome)
        ativo = bool(pid) if cfg["tipo"] != "flag" else flag
        registro = estado["servicos"].get(nome, {})
        metricas = _metricas_pid(pid)
        resultado.append({
            "id": nome,
            "nome": cfg["nome"],
            "status": "ON" if ativo else "OFF",
            "pid": pid,
            "log": str(cfg.get("log", "")) if cfg["tipo"] != "flag" else "",
            "cpu": metricas["cpu"],
            "memoria": metricas["memoria"],
            "tempo_ligado": metricas["tempo_ligado"],
            "requisicoes": int(registro.get("requisicoes", 0) or 0),
            "custo_estimado": float(registro.get("custo_estimado", 0) or 0),
            "watchdog": "gerenciado" if cfg["tipo"] != "flag" else "flag",
            "descricao": cfg["descricao"],
            "custo": cfg["custo"],
            "ultimo_evento": registro.get("ultimo_evento", ""),
        })
    resultado.extend(_status_locais())
    return resultado


def _status_locais():
    banco_ok = False
    try:
        from banco import conectar
        with conectar() as conn:
            conn.execute("SELECT 1").fetchone()
        banco_ok = True
    except Exception:
        banco_ok = False

    ollama_ok = bool(subprocess.run(["pgrep", "-f", "ollama"], capture_output=True, text=True, check=False).stdout.strip())
    return [
        {
            "id": "ollama",
            "nome": "Ollama",
            "status": "ON" if ollama_ok else "OFF",
            "pid": None,
            "log": "",
            "cpu": None,
            "memoria": None,
            "tempo_ligado": None,
            "requisicoes": 0,
            "custo_estimado": 0.0,
            "watchdog": "local",
            "descricao": "IA local; sem custo de API externa.",
            "custo": False,
            "ultimo_evento": "",
        },
        {
            "id": "banco",
            "nome": "Banco",
            "status": "ON" if banco_ok else "OFF",
            "pid": None,
            "log": "",
            "cpu": None,
            "memoria": None,
            "tempo_ligado": None,
            "requisicoes": 0,
            "custo_estimado": 0.0,
            "watchdog": "local",
            "descricao": "SQLite local.",
            "custo": False,
            "ultimo_evento": "",
        },
    ]


def modo_economico():
    mensagens = []
    for nome, cfg in SERVICOS.items():
        if cfg.get("custo"):
            mensagens.append(parar_servico(nome)["mensagem"])
    estado = _carregar_estado()
    estado["modo"] = "economico"
    _salvar_estado(estado)
    return mensagens


def modo_estavel():
    mensagens = []
    for nome, cfg in SERVICOS.items():
        if cfg.get("custo"):
            mensagens.append(parar_servico(nome)["mensagem"])
    for nome in sorted(SERVICOS_ESTAVEIS_LOCAIS):
        mensagens.append(iniciar_servico(nome)["mensagem"])
    estado = _carregar_estado()
    estado["modo"] = MODO_ESTAVEL_LOCAL
    estado["publicacao_automatica"] = False
    estado["telegram_real"] = False
    estado["deploy_automatico"] = False
    estado["coleta_agressiva"] = False
    _salvar_estado(estado)
    return mensagens


def modo_operacao():
    mensagens = []
    for nome, cfg in SERVICOS.items():
        if cfg.get("custo"):
            mensagens.append(parar_servico(nome)["mensagem"])
    for nome in sorted(SERVICOS_OPERACAO):
        mensagens.append(iniciar_servico(nome)["mensagem"])
    estado = _carregar_estado()
    estado["modo"] = "operacao_controlada"
    estado["publicacao_automatica"] = False
    estado["telegram_real"] = False
    estado["deploy_automatico"] = False
    estado["coleta_agressiva"] = False
    _salvar_estado(estado)
    return mensagens


def modo_divulgacao():
    from seguranca_publicacao import auditar_seguranca_publicacao

    auditoria = auditar_seguranca_publicacao()
    mensagens = []
    if not auditoria.get("publicacao_segura"):
        estado = _carregar_estado()
        estado["modo"] = "divulgacao_bloqueada"
        estado["publicacao_automatica"] = False
        estado["telegram_real"] = False
        estado["deploy_automatico"] = False
        _salvar_estado(estado)
        return {
            "ok": False,
            "mensagens": ["Divulgação bloqueada: auditoria de segurança tem críticos ou bloqueantes."],
            "auditoria": auditoria,
        }
    for nome in sorted(SERVICOS_ESTAVEIS_LOCAIS):
        mensagens.append(iniciar_servico(nome)["mensagem"])
    estado = _carregar_estado()
    estado["modo"] = "divulgacao_liberada"
    estado["publicacao_automatica"] = False
    estado["telegram_real"] = False
    estado["deploy_automatico"] = False
    _salvar_estado(estado)
    return {"ok": True, "mensagens": mensagens, "auditoria": auditoria}


def modo_producao():
    mensagens = []
    for nome in SERVICOS_PRODUCAO:
        mensagens.append(iniciar_servico(nome)["mensagem"])
    estado = _carregar_estado()
    estado["modo"] = "producao"
    _salvar_estado(estado)
    return mensagens
