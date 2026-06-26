"""Alertas operacionais Telegram para o supervisor Promogg.

Não envia ofertas. Sanitiza mensagens e aplica cooldown por tipo de alerta.
"""

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

from banco import registrar_evento_sistema, registrar_log


ESTADO_ALERTAS = Path(".promogg_alertas_estado.json")
RELATORIO_ALERTAS = Path("RELATORIO_SUPERVISOR_AUTOMATICO.md")
TIPOS_ALERTA = {
    "login_mercado_livre_necessario",
    "oauth_expirado",
    "api_401_403",
    "playwright_logout",
    "catalogo_degradado",
    "validacao_falhou",
    "deploy_bloqueado",
    "telegram_ofertas_bloqueado",
    "ciclo_concluido",
    "producao_liberada",
    "intervencao_humana_necessaria",
}


def _agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def alertas_habilitados():
    load_dotenv(override=True)
    return os.getenv("PROMOGG_SUPERVISOR_TELEGRAM_ALERTAS", "true").strip().lower() in {"1", "true", "sim", "yes", "on"}


def cooldown_minutos():
    try:
        return max(0, int(os.getenv("PROMOGG_SUPERVISOR_ALERTA_COOLDOWN_MINUTOS", "60")))
    except ValueError:
        return 60


def _carregar_estado():
    try:
        return json.loads(ESTADO_ALERTAS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"alertas": []}


def _salvar_estado(estado):
    ESTADO_ALERTAS.write_text(json.dumps(estado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sanitizar(texto, limite=900):
    texto = " ".join(str(texto or "").replace("\n", " ").split())
    texto = re.sub(r"https?://\S+", "[url removida]", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\b(?:token|secret|password|senha|cookie|authorization|api[_-]?key)\s*[:=]\s*\S+", "[segredo removido]", texto, flags=re.IGNORECASE)
    texto = re.sub(r"(MELI_ACCESS_TOKEN|MELI_REFRESH_TOKEN|TELEGRAM_BOT_TOKEN|TELEGRAM_CHAT_ID)=\S+", r"\1=[removido]", texto)
    return texto[:limite]


def _pode_enviar(tipo, estado=None):
    estado = estado or _carregar_estado()
    limite = datetime.now() - timedelta(minutes=cooldown_minutos())
    for alerta in reversed(estado.get("alertas", [])):
        if alerta.get("tipo") != tipo or not alerta.get("enviado"):
            continue
        try:
            enviado_em = datetime.fromisoformat(alerta["quando"])
        except (TypeError, ValueError):
            continue
        if enviado_em >= limite:
            return False
        return True
    return True


def _destino_telegram():
    load_dotenv(override=True)
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_ALERT_CHAT_ID", "").strip() or os.getenv("TELEGRAM_CHAT_ID", "").strip()
    return token, chat_id


def enviar_alerta_operacional(tipo, mensagem, dry_run=True, forcar=False):
    tipo = str(tipo or "intervencao_humana_necessaria").strip()
    if tipo not in TIPOS_ALERTA:
        tipo = "intervencao_humana_necessaria"
    mensagem = f"[ALERTA PROMOGG] {sanitizar(mensagem)}"
    estado = _carregar_estado()
    registro = {"quando": datetime.now().isoformat(timespec="seconds"), "tipo": tipo, "mensagem": mensagem, "dry_run": dry_run, "enviado": False, "motivo": ""}

    if not alertas_habilitados():
        registro["motivo"] = "alertas desabilitados"
    elif not forcar and not _pode_enviar(tipo, estado):
        registro["motivo"] = "cooldown ativo"
    elif dry_run:
        registro["motivo"] = "simulado"
    else:
        token, chat_id = _destino_telegram()
        if not token or not chat_id:
            registro["motivo"] = "Telegram operacional não configurado"
        else:
            try:
                resposta = requests.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    data={"chat_id": chat_id, "text": mensagem},
                    timeout=20,
                )
                registro["enviado"] = resposta.status_code == 200
                registro["motivo"] = "enviado" if registro["enviado"] else f"HTTP {resposta.status_code}"
            except requests.RequestException as erro:
                registro["motivo"] = sanitizar(f"falha de rede: {erro}", 160)

    estado.setdefault("alertas", []).append(registro)
    estado["alertas"] = estado["alertas"][-80:]
    if not dry_run:
        _salvar_estado(estado)
        registrar_log("alertas_telegram", f"Alerta operacional {tipo}: {registro['motivo']}", dados=mensagem[:500])
        registrar_evento_sistema("alerta_operacional", "supervisor", "sucesso" if registro["enviado"] else "aviso", f"Alerta {tipo}", registro["motivo"])
    return registro


def enviar_resumo_ciclo(resumo, dry_run=True):
    texto = "\n".join([
        "✅ Promogg ciclo concluído",
        f"Ofertas públicas: {resumo.get('ofertas_publicas', 0)}",
        f"Pendentes: {resumo.get('pendentes', 0)}",
        f"Aprovadas auto: {resumo.get('aprovadas_auto', 0)}",
        f"Rejeitadas: {resumo.get('rejeitadas', 0)}",
        f"Publicáveis: {resumo.get('publicaveis', 0)}",
        f"Deploy: {resumo.get('deploy', 'bloqueado')}",
        f"Telegram ofertas: {resumo.get('telegram_ofertas', 'bloqueado')}",
        f"Saúde: {resumo.get('saude', 'desconhecida')}",
    ])
    return enviar_alerta_operacional("ciclo_concluido", texto, dry_run=dry_run)


def testar_alerta_telegram(dry_run=True):
    return enviar_alerta_operacional(
        "intervencao_humana_necessaria",
        f"Teste operacional Promogg em {_agora()}. Nenhuma oferta foi enviada.",
        dry_run=dry_run,
        forcar=True,
    )


def ultimo_alerta():
    estado = _carregar_estado()
    alertas = estado.get("alertas", [])
    return alertas[-1] if alertas else {}
