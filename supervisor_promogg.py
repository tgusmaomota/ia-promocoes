"""Supervisor automático seguro do Promogg."""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from alertas_telegram import enviar_alerta_operacional, enviar_resumo_ciclo, ultimo_alerta
from banco import conectar, inicializar_banco, registrar_evento_sistema
from catalogo_integridade import resumo_catalogo
from estado_sistema import MANUTENCAO_PARCIAL, definir_estado_sistema, obter_estado_sistema
from homologacao_publicacao import _git_status_classificado
from playwright_perfil import diagnosticar_perfil
from qualidade_catalogo import auditar_qualidade_catalogo
from saude_sistema import obter_relatorio_saude


RELATORIO = Path("RELATORIO_SUPERVISOR_AUTOMATICO.md")


def agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def config_supervisor():
    load_dotenv(override=True)
    def bool_env(nome, padrao=False):
        return os.getenv(nome, str(padrao).lower()).strip().lower() in {"1", "true", "sim", "yes", "on"}
    def int_env(nome, padrao):
        try:
            return int(os.getenv(nome, str(padrao)))
        except ValueError:
            return padrao
    return {
        "publicar": bool_env("PROMOGG_SUPERVISOR_PUBLICAR", False),
        "telegram_alertas": bool_env("PROMOGG_SUPERVISOR_TELEGRAM_ALERTAS", True),
        "intervalo_minutos": max(1, int_env("PROMOGG_SUPERVISOR_INTERVALO_MINUTOS", 60)),
        "max_erros_seguidos": max(1, int_env("PROMOGG_SUPERVISOR_MAX_ERROS_SEGUIDOS", 3)),
        "alerta_cooldown_minutos": max(0, int_env("PROMOGG_SUPERVISOR_ALERTA_COOLDOWN_MINUTOS", 60)),
    }


def _executar(args):
    proc = subprocess.run([sys.executable, "ia_promocoes.py", *args], capture_output=True, text=True)
    return {
        "comando": " ".join(["python3", "ia_promocoes.py", *args]),
        "codigo": proc.returncode,
        "stdout": (proc.stdout or "").strip()[-4000:],
        "stderr": (proc.stderr or "").strip()[-2000:],
    }


def _contagens():
    inicializar_banco()
    with conectar() as conn:
        status = {row["status"]: row["total"] for row in conn.execute("SELECT status, COUNT(*) total FROM postagens GROUP BY status")}
    return {
        "pendentes": status.get("pendente_revisao", 0),
        "aprovadas_auto": status.get("aprovado_auto", 0),
        "rejeitadas": status.get("rejeitado", 0),
        "publicadas": status.get("publicado", 0),
    }


def detectar_erros_ml():
    inicializar_banco()
    problemas = []
    with conectar() as conn:
        recentes = [dict(row) for row in conn.execute(
            """
            SELECT criado_em, etapa, nivel, mensagem, dados
            FROM logs
            WHERE criado_em >= datetime('now', '-2 days')
              AND (
                mensagem LIKE '%HTTP 401%' OR dados LIKE '%HTTP 401%'
                OR mensagem LIKE '%HTTP 403%' OR dados LIKE '%HTTP 403%'
                OR mensagem LIKE '%Falha ao gerar meli.la%'
                OR mensagem LIKE '%login%'
              )
            ORDER BY id DESC LIMIT 20
            """
        ).fetchall()]
        eventos_login = [dict(row) for row in conn.execute(
            """
            SELECT data_evento, origem, status, mensagem, detalhes
            FROM sistema_eventos
            WHERE data_evento >= datetime('now', '-2 days')
              AND (status='login_necessario' OR mensagem LIKE '%Login Mercado Livre necessário%' OR detalhes LIKE '%login%')
            ORDER BY id DESC LIMIT 10
            """
        ).fetchall()]
    for item in recentes:
        texto = f"{item.get('mensagem','')} {item.get('dados','')}".lower()
        if "http 401" in texto:
            problemas.append({"tipo": "oauth_expirado", "mensagem": "API Mercado Livre respondeu HTTP 401."})
        elif "http 403" in texto:
            problemas.append({"tipo": "api_401_403", "mensagem": "API Mercado Livre respondeu HTTP 403; fallback/degradação pode ser necessária."})
        elif "falha ao gerar meli.la" in texto and "login" in texto:
            problemas.append({"tipo": "login_mercado_livre_necessario", "mensagem": "Portal afiliado falhou com indício de sessão expirada."})
    if eventos_login:
        problemas.append({"tipo": "playwright_logout", "mensagem": "Playwright/Mercado Livre registrou login necessário."})
    vistos = set()
    unicos = []
    for p in problemas:
        chave = (p["tipo"], p["mensagem"])
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(p)
    return unicos


def status_playwright_supervisor(dry_run=True):
    diagnostico = diagnosticar_perfil()
    if not diagnostico["existe"]:
        return {"ok": False, "modo": "login_necessario", "motivo": "perfil_mercadolivre ausente", "diagnostico": diagnostico}
    if diagnostico["processos"] or diagnostico["locks"]:
        return {"ok": False, "modo": "degradado", "motivo": "perfil em uso ou com locks; supervisor não abrirá Playwright agora", "diagnostico": diagnostico}
    if dry_run:
        return {"ok": True, "modo": "nao_verificado_em_dry_run", "motivo": "perfil existe e não está bloqueado", "diagnostico": diagnostico}
    try:
        from playwright_perfil import verificar_login_mercadolivre
        sessao = verificar_login_mercadolivre(visual=False)
        return {"ok": bool(sessao.get("logado")), "modo": "normal" if sessao.get("logado") else "login_necessario", "motivo": sessao.get("motivo", ""), "diagnostico": diagnostico}
    except Exception as erro:
        return {"ok": False, "modo": "degradado", "motivo": f"falha ao verificar sessão Playwright: {erro}", "diagnostico": diagnostico}


def _resumo_ciclo_do_stdout(stdout):
    resumo = {}
    for linha in str(stdout or "").splitlines():
        if ":" not in linha:
            continue
        chave, valor = linha.split(":", 1)
        resumo[chave.strip().lower()] = valor.strip()
    return resumo


def _escrever_relatorio(resultado):
    linhas = [
        "# Relatório do Supervisor Automático",
        "",
        f"- Gerado em: {agora()}",
        f"- Modo: {'dry-run' if resultado['dry_run'] else 'execução real'}",
        "",
        "## Configuração",
        f"- PROMOGG_SUPERVISOR_PUBLICAR: {resultado['config']['publicar']}",
        f"- PROMOGG_SUPERVISOR_TELEGRAM_ALERTAS: {resultado['config']['telegram_alertas']}",
        f"- PROMOGG_SUPERVISOR_INTERVALO_MINUTOS: {resultado['config']['intervalo_minutos']}",
        f"- PROMOGG_SUPERVISOR_MAX_ERROS_SEGUIDOS: {resultado['config']['max_erros_seguidos']}",
        f"- PROMOGG_SUPERVISOR_ALERTA_COOLDOWN_MINUTOS: {resultado['config']['alerta_cooldown_minutos']}",
        "",
        "## Último ciclo",
        f"- Status final: {resultado['status_final']}",
        f"- Modo atual: {resultado['modo_atual']}",
        f"- Ofertas públicas: {resultado['catalogo']['ofertas']}",
        f"- Páginas: {resultado['catalogo']['paginas']}",
        f"- Pendentes: {resultado['contagens']['pendentes']}",
        f"- Aprovadas auto: {resultado['contagens']['aprovadas_auto']}",
        f"- Rejeitadas: {resultado['contagens']['rejeitadas']}",
        "",
        "## Alertas enviados/simulados",
    ]
    linhas += [f"- {a['tipo']}: {a['motivo']} | dry_run={a['dry_run']}" for a in resultado["alertas"]] or ["- nenhum"]
    linhas += [
        "",
        "## Bloqueios",
    ]
    linhas += [f"- {b}" for b in resultado["bloqueios"]] or ["- nenhum"]
    linhas += [
        "",
        "## Status Mercado Livre",
        f"- Problemas detectados: {len(resultado['problemas_ml'])}",
        *[f"- {p['tipo']}: {p['mensagem']}" for p in resultado["problemas_ml"]],
        "",
        "## Status Playwright",
        f"- OK: {resultado['playwright']['ok']}",
        f"- Modo: {resultado['playwright']['modo']}",
        f"- Motivo: {resultado['playwright']['motivo']}",
        "",
        "## Status catálogo",
        f"- Qualidade: {resultado['qualidade']['indicador']}",
        f"- Ressalvas bloqueantes: {len(resultado['qualidade'].get('ressalvas_bloqueantes', {}))}",
        f"- Ressalvas informativas: {len(resultado['qualidade'].get('ressalvas_informativas', {}))}",
        "",
        "## Recomendação",
        resultado["recomendacao"],
    ]
    RELATORIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def executar_supervisor(dry_run=True):
    cfg = config_supervisor()
    alertas = []
    bloqueios = []
    comandos = []
    estado = obter_estado_sistema()
    catalogo = resumo_catalogo("site")
    qualidade = auditar_qualidade_catalogo()
    saude = obter_relatorio_saude()
    playwright = status_playwright_supervisor(dry_run=dry_run)
    problemas_ml = detectar_erros_ml()
    git = _git_status_classificado()

    comandos.append(_executar(["status"]))
    comandos.append(_executar(["validar", "--somente-leitura"]))
    comandos.append(_executar(["auditar-qualidade-catalogo"]))
    comandos.append(_executar(["ciclo-automatico", "--dry-run"]))

    if comandos[-1]["codigo"] != 0:
        bloqueios.append("ciclo-automatico --dry-run falhou")
    if comandos[-2]["codigo"] != 0:
        bloqueios.append("auditoria de qualidade falhou")
    if comandos[-3]["codigo"] != 0:
        bloqueios.append("validar --somente-leitura falhou")
    if qualidade.get("ressalvas_bloqueantes"):
        bloqueios.append("catálogo possui ressalvas bloqueantes")
    dist = resumo_catalogo("dist_site")
    if dist["ofertas"] != catalogo["ofertas"] or dist["paginas"] != catalogo["paginas"]:
        bloqueios.append("dist_site diverge de site")
        alertas.append(enviar_alerta_operacional("catalogo_degradado", "dist_site diverge do site validado; publicação segue bloqueada.", dry_run=dry_run))
    if saude.get("criticos"):
        bloqueios.append("saúde possui críticos")
    if git.get("bloqueantes"):
        bloqueios.append("Git possui alterações bloqueantes para publicação")
    if problemas_ml:
        bloqueios.append("Mercado Livre/API/Playwright em modo degradado")
    if not playwright["ok"] and playwright["modo"] == "login_necessario":
        bloqueios.append("login Mercado Livre necessário")

    if problemas_ml or playwright["modo"] in {"login_necessario", "degradado"}:
        if not dry_run:
            definir_estado_sistema(MANUTENCAO_PARCIAL, "Supervisor detectou dependência Mercado Livre degradada")
        mensagem = (
            "⚠️ Promogg precisa de login no Mercado Livre. A automação foi pausada com segurança. "
            "Rode: python3 ia_promocoes.py login-mercadolivre Depois: "
            "python3 ia_promocoes.py testar-playwright-sessao python3 ia_promocoes.py supervisor"
        )
        alertas.append(enviar_alerta_operacional("login_mercado_livre_necessario", mensagem, dry_run=dry_run))

    pode_rodar_ciclo_real = not dry_run and not problemas_ml and playwright["ok"] and comandos[-1]["codigo"] == 0
    ciclo_real = None
    if pode_rodar_ciclo_real:
        args = ["ciclo-automatico"]
        if cfg["publicar"]:
            args.append("--publicar")
        ciclo_real = _executar(args)
        comandos.append(ciclo_real)
        if ciclo_real["codigo"] != 0:
            bloqueios.append("ciclo automático real falhou ou ficou bloqueado")

    if cfg["publicar"]:
        ciclo_publicar_sim = _executar(["ciclo-automatico", "--dry-run", "--publicar"])
        comandos.append(ciclo_publicar_sim)
        if "Seguro rodar ciclo-automatico --publicar: sim" in ciclo_publicar_sim["stdout"]:
            alertas.append(enviar_alerta_operacional("producao_liberada", "✅ Promogg produção liberada pelas travas do supervisor.", dry_run=dry_run))
        else:
            alertas.append(enviar_alerta_operacional("deploy_bloqueado", "Publicação automática segue bloqueada pelas travas de segurança.", dry_run=dry_run))
    else:
        alertas.append(enviar_alerta_operacional("telegram_ofertas_bloqueado", "Publicação de ofertas/deploy bloqueada: PROMOGG_SUPERVISOR_PUBLICAR=false.", dry_run=dry_run))

    contagens = _contagens()
    resumo = {
        "ofertas_publicas": catalogo["ofertas"],
        "pendentes": contagens["pendentes"],
        "aprovadas_auto": contagens["aprovadas_auto"],
        "rejeitadas": contagens["rejeitadas"],
        "publicaveis": _resumo_ciclo_do_stdout(comandos[-1]["stdout"]).get("publicáveis estimadas", "n/d"),
        "deploy": "liberado" if cfg["publicar"] and not bloqueios else "bloqueado",
        "telegram_ofertas": "liberado" if cfg["publicar"] and not bloqueios else "bloqueado",
        "saude": saude.get("status_geral", "desconhecida"),
    }
    if not bloqueios:
        alertas.append(enviar_resumo_ciclo(resumo, dry_run=dry_run))
    elif len(bloqueios) >= cfg["max_erros_seguidos"]:
        alertas.append(enviar_alerta_operacional("intervencao_humana_necessaria", "Supervisor detectou múltiplos bloqueios: " + "; ".join(bloqueios[:5]), dry_run=dry_run))

    modo_atual = "degradado" if problemas_ml or playwright["modo"] in {"login_necessario", "degradado"} else "normal"
    status_final = "ok" if not bloqueios else "bloqueado"
    recomendacao = (
        "Rode login-mercadolivre e testar-playwright-sessao antes de retomar coleta/afiliados."
        if modo_atual == "degradado"
        else "Supervisor pronto. Publicação real depende de PROMOGG_SUPERVISOR_PUBLICAR=true e Git sem alterações bloqueantes."
    )
    resultado = {
        "dry_run": dry_run,
        "config": cfg,
        "estado": estado,
        "catalogo": catalogo,
        "qualidade": qualidade,
        "saude": saude,
        "playwright": playwright,
        "problemas_ml": problemas_ml,
        "git": git,
        "comandos": comandos,
        "alertas": alertas,
        "bloqueios": bloqueios,
        "contagens": contagens,
        "modo_atual": modo_atual,
        "status_final": status_final,
        "recomendacao": recomendacao,
        "ultimo_alerta": ultimo_alerta(),
    }
    _escrever_relatorio(resultado)
    if not dry_run:
        registrar_evento_sistema("supervisor", "supervisor", "sucesso" if status_final == "ok" else "aviso", f"Supervisor {status_final}", "; ".join(bloqueios[:5]))
    return resultado


def supervisor_loop():
    cfg = config_supervisor()
    print(f"Supervisor loop iniciado. Intervalo: {cfg['intervalo_minutos']} min. Ctrl+C para parar.")
    try:
        while True:
            resultado = executar_supervisor(dry_run=False)
            print(f"{agora()} supervisor: {resultado['status_final']} modo={resultado['modo_atual']}")
            time.sleep(cfg["intervalo_minutos"] * 60)
    except KeyboardInterrupt:
        print("\nSupervisor loop parado com segurança. Checkpoints preservados.")
        return 0
