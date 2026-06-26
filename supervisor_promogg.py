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
from estado_sistema import MANUTENCAO, MANUTENCAO_PARCIAL, definir_estado_sistema, obter_estado_sistema
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


def _catalogo_integro_para_fallback(catalogo, qualidade):
    metricas = qualidade.get("metricas", {})
    return (
        not catalogo.get("erro")
        and int(catalogo.get("ofertas") or 0) >= 30
        and int(catalogo.get("paginas") or 0) == int(catalogo.get("ofertas") or 0)
        and int(catalogo.get("links_invalidos") or 0) == 0
        and int(catalogo.get("paginas_ausentes") or 0) == 0
        and not qualidade.get("ressalvas_bloqueantes")
        and int(metricas.get("preco_invalido") or 0) == 0
        and int(metricas.get("imagens_quebradas") or 0) == 0
        and int(metricas.get("paginas_quebradas") or 0) == 0
    )


def classificar_dependencias_ml(problemas_ml, playwright, catalogo, qualidade, dry_run=True, auditoria_ml=None):
    """Separa falhas reais de produção de degradações aceitáveis com fallback.

    A API de busca/categoria do Mercado Livre pode responder 403 mesmo com OAuth,
    item básico e Playwright saudáveis. Nessa condição o supervisor deve alertar,
    mas não travar coleta/supervisão nem forçar MANUTENCAO_PARCIAL.
    """
    bloqueantes = []
    avisos = []
    auditoria_ml = auditoria_ml or {}
    oauth_item_ok = bool(auditoria_ml.get("users_me_ok")) and bool(auditoria_ml.get("item_ok"))
    catalogo_ok = _catalogo_integro_para_fallback(catalogo, qualidade)
    playwright_ok_para_fallback = bool(playwright.get("ok")) and playwright.get("modo") in {
        "normal",
        "nao_verificado_em_dry_run",
    }

    for problema in problemas_ml:
        tipo = problema.get("tipo")
        mensagem = str(problema.get("mensagem") or "")
        mensagem_lower = mensagem.lower()

        if tipo == "oauth_expirado" or "http 401" in mensagem_lower or "invalid token" in mensagem_lower:
            if oauth_item_ok:
                avisos.append({
                    "tipo": "oauth_401_historico_resolvido",
                    "mensagem": "HTTP 401 histórico não bloqueia: auditoria atual confirmou /users/me e item básicos OK.",
                })
                continue
            bloqueantes.append(problema)
        elif tipo == "playwright_logout" and playwright_ok_para_fallback:
            avisos.append({
                "tipo": "playwright_login_evento_resolvido",
                "mensagem": "Evento anterior de login necessário não bloqueia: perfil Playwright está disponível/logado.",
            })
        elif tipo in {"login_mercado_livre_necessario", "playwright_logout"}:
            bloqueantes.append(problema)
        elif "403" in mensagem_lower or "categoria" in mensagem_lower or tipo == "api_401_403":
            if catalogo_ok and playwright_ok_para_fallback:
                avisos.append({
                    "tipo": "api_busca_403_fallback",
                    "mensagem": "API busca ML em 403, usando fallback Playwright.",
                })
            else:
                bloqueantes.append(problema)
        else:
            avisos.append(problema)

    if playwright.get("modo") == "nao_verificado_em_dry_run":
        avisos.append({
            "tipo": "playwright_nao_verificado_dry_run",
            "mensagem": "Playwright não verificado no dry-run; perfil existe e não está bloqueado.",
        })
    elif not playwright.get("ok"):
        bloqueantes.append({
            "tipo": "playwright_degradado",
            "mensagem": playwright.get("motivo") or "Playwright indisponível ou deslogado.",
        })

    if auditoria_ml and not auditoria_ml.get("users_me_ok"):
        bloqueantes.append({
            "tipo": "oauth_nao_confirmado",
            "mensagem": "Auditoria atual não confirmou /users/me OK.",
        })
    elif auditoria_ml and not auditoria_ml.get("item_ok") and not catalogo_ok:
        bloqueantes.append({
            "tipo": "item_api_sem_fallback",
            "mensagem": "Item básico da API não foi confirmado e o catálogo/fallback não está íntegro.",
        })

    vistos = set()
    avisos_unicos = []
    for aviso in avisos:
        chave = (aviso.get("tipo"), aviso.get("mensagem"))
        if chave not in vistos:
            vistos.add(chave)
            avisos_unicos.append(aviso)

    vistos = set()
    bloqueantes_unicos = []
    for bloqueio in bloqueantes:
        chave = (bloqueio.get("tipo"), bloqueio.get("mensagem"))
        if chave not in vistos:
            vistos.add(chave)
            bloqueantes_unicos.append(bloqueio)

    if bloqueantes_unicos:
        modo = "degradado"
    elif any(a.get("tipo") == "api_busca_403_fallback" for a in avisos_unicos):
        modo = "degradado_nao_bloqueante"
    elif avisos_unicos:
        modo = "normal_com_alertas"
    else:
        modo = "normal"

    return {
        "catalogo_ok_para_fallback": catalogo_ok,
        "playwright_ok_para_fallback": playwright_ok_para_fallback,
        "bloqueantes": bloqueantes_unicos,
        "avisos": avisos_unicos,
        "modo": modo,
    }


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
        venv_python = Path("venv/bin/python")
        erro_texto = str(erro).lower()
        fora_do_venv = Path(sys.prefix).resolve() != Path("venv").resolve()
        if "no module named" in erro_texto and "playwright" in erro_texto and venv_python.exists() and fora_do_venv:
            proc = subprocess.run(
                [str(venv_python), "ia_promocoes.py", "testar-playwright-sessao"],
                capture_output=True,
                text=True,
                timeout=90,
            )
            saida = f"{proc.stdout}\n{proc.stderr}"
            if proc.returncode == 0 and "Logado Mercado Livre: sim" in saida:
                return {"ok": True, "modo": "normal", "motivo": "sessão validada via venv/bin/python", "diagnostico": diagnostico}
            return {
                "ok": False,
                "modo": "login_necessario",
                "motivo": "falha ao validar sessão via venv/bin/python",
                "diagnostico": diagnostico,
            }
        return {"ok": False, "modo": "degradado", "motivo": f"falha ao verificar sessão Playwright: {erro}", "diagnostico": diagnostico}


def _resumo_ciclo_do_stdout(stdout):
    resumo = {}
    for linha in str(stdout or "").splitlines():
        if ":" not in linha:
            continue
        chave, valor = linha.split(":", 1)
        resumo[chave.strip().lower()] = valor.strip()
    return resumo


def _resumo_auditoria_ml(stdout):
    texto = str(stdout or "")
    return {
        "users_me_ok": "/users/me: ok" in texto,
        "item_ok": "Item: ok" in texto,
        "categoria_falhou": "Categoria: não testada/falhou" in texto,
        "refresh_nao_necessario": "Refresh automático: não necessário" in texto,
        "stdout": texto[-1200:],
    }


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
        "## Bloqueios de publicação",
    ]
    linhas += [f"- {b}" for b in resultado.get("bloqueios_publicacao", [])] or ["- nenhum"]
    linhas += [
        "",
        "## Avisos não bloqueantes",
    ]
    linhas += [f"- {a['tipo']}: {a['mensagem']}" for a in resultado.get("avisos", [])] or ["- nenhum"]
    linhas += [
        "",
        "## Status Mercado Livre",
        f"- Problemas detectados: {len(resultado['problemas_ml'])}",
        f"- /users/me atual: {'ok' if resultado.get('auditoria_ml', {}).get('users_me_ok') else 'não confirmado'}",
        f"- Item atual: {'ok' if resultado.get('auditoria_ml', {}).get('item_ok') else 'não confirmado'}",
        f"- Categoria: {'não testada/falhou' if resultado.get('auditoria_ml', {}).get('categoria_falhou') else 'ok/não informada'}",
        f"- Modo ML: {resultado.get('classificacao_ml', {}).get('modo', 'n/d')}",
        f"- Bloqueantes ML: {len(resultado.get('classificacao_ml', {}).get('bloqueantes', []))}",
        f"- Avisos ML: {len(resultado.get('classificacao_ml', {}).get('avisos', []))}",
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
    bloqueios_publicacao = []
    comandos = []
    estado = obter_estado_sistema()
    catalogo = resumo_catalogo("site")
    qualidade = auditar_qualidade_catalogo()
    saude = obter_relatorio_saude()
    playwright = status_playwright_supervisor(dry_run=dry_run)
    problemas_ml = detectar_erros_ml()
    git = _git_status_classificado()

    comandos.append(_executar(["status"]))
    auditoria_ml_cmd = _executar(["meli-auditar-api"])
    comandos.append(auditoria_ml_cmd)
    auditoria_ml = _resumo_auditoria_ml(auditoria_ml_cmd["stdout"])
    classificacao_ml = classificar_dependencias_ml(
        problemas_ml, playwright, catalogo, qualidade, dry_run=dry_run, auditoria_ml=auditoria_ml
    )
    comandos.append(_executar(["validar", "--somente-leitura"]))
    comandos.append(_executar(["auditar-qualidade-catalogo"]))
    comandos.append(_executar(["ciclo-automatico", "--dry-run"]))

    if comandos[-1]["codigo"] != 0:
        bloqueios_publicacao.append("ciclo-automatico --dry-run falhou")
    if comandos[-2]["codigo"] != 0:
        bloqueios.append("auditoria de qualidade falhou")
    if comandos[-3]["codigo"] != 0:
        bloqueios.append("validar --somente-leitura falhou")
    if qualidade.get("ressalvas_bloqueantes"):
        bloqueios.append("catálogo possui ressalvas bloqueantes")
    dist = resumo_catalogo("dist_site")
    if dist["ofertas"] != catalogo["ofertas"] or dist["paginas"] != catalogo["paginas"]:
        bloqueios_publicacao.append("dist_site diverge de site")
        alertas.append(enviar_alerta_operacional("catalogo_degradado", "dist_site diverge do site validado; publicação segue bloqueada.", dry_run=dry_run))
    if saude.get("criticos"):
        bloqueios.append("saúde possui críticos")
    if git.get("bloqueantes"):
        bloqueios_publicacao.append("Git possui alterações bloqueantes para publicação")
    if classificacao_ml["bloqueantes"]:
        bloqueios.append("Mercado Livre/API/Playwright em modo degradado bloqueante")
    if not playwright["ok"] and playwright["modo"] == "login_necessario":
        bloqueios.append("login Mercado Livre necessário")

    for aviso in classificacao_ml["avisos"]:
        if aviso["tipo"] == "api_busca_403_fallback":
            alertas.append(enviar_alerta_operacional("api_busca_403_fallback", aviso["mensagem"], dry_run=dry_run))

    if classificacao_ml["bloqueantes"] or playwright["modo"] in {"login_necessario", "degradado"}:
        if not dry_run:
            definir_estado_sistema(MANUTENCAO_PARCIAL, "Supervisor detectou dependência Mercado Livre degradada")
        mensagem = (
            "⚠️ Promogg precisa de login no Mercado Livre. A automação foi pausada com segurança. "
            "Rode: python3 ia_promocoes.py login-mercadolivre Depois: "
            "python3 ia_promocoes.py testar-playwright-sessao python3 ia_promocoes.py supervisor"
        )
        alertas.append(enviar_alerta_operacional("login_mercado_livre_necessario", mensagem, dry_run=dry_run))
    elif (
        not dry_run
        and estado.get("estado") == MANUTENCAO_PARCIAL
        and "Supervisor detectou dependência Mercado Livre degradada" in str(estado.get("motivo") or "")
    ):
        definir_estado_sistema(MANUTENCAO, "Supervisor: degradação ML não bloqueante; publicação segue protegida")

    pode_rodar_ciclo_real = not dry_run and not classificacao_ml["bloqueantes"] and playwright["ok"] and comandos[-1]["codigo"] == 0
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
            bloqueios_publicacao.append("ciclo-automatico --publicar ainda não está homologado pelas travas de segurança")
            alertas.append(enviar_alerta_operacional("deploy_bloqueado", "Publicação automática segue bloqueada pelas travas de segurança.", dry_run=dry_run))
    else:
        bloqueios_publicacao.append("PROMOGG_SUPERVISOR_PUBLICAR=false")
        alertas.append(enviar_alerta_operacional("telegram_ofertas_bloqueado", "Publicação de ofertas/deploy bloqueada: PROMOGG_SUPERVISOR_PUBLICAR=false.", dry_run=dry_run))

    contagens = _contagens()
    resumo = {
        "ofertas_publicas": catalogo["ofertas"],
        "pendentes": contagens["pendentes"],
        "aprovadas_auto": contagens["aprovadas_auto"],
        "rejeitadas": contagens["rejeitadas"],
        "publicaveis": _resumo_ciclo_do_stdout(comandos[-1]["stdout"]).get("publicáveis estimadas", "n/d"),
        "deploy": "liberado" if cfg["publicar"] and not bloqueios and not bloqueios_publicacao else "bloqueado",
        "telegram_ofertas": "liberado" if cfg["publicar"] and not bloqueios and not bloqueios_publicacao else "bloqueado",
        "saude": saude.get("status_geral", "desconhecida"),
    }
    if not bloqueios:
        alertas.append(enviar_resumo_ciclo(resumo, dry_run=dry_run))
    elif len(bloqueios) >= cfg["max_erros_seguidos"]:
        alertas.append(enviar_alerta_operacional("intervencao_humana_necessaria", "Supervisor detectou múltiplos bloqueios: " + "; ".join(bloqueios[:5]), dry_run=dry_run))

    modo_atual = classificacao_ml["modo"]
    status_final = "ok" if not bloqueios else "bloqueado"
    recomendacao = (
        "Rode login-mercadolivre e testar-playwright-sessao antes de retomar coleta/afiliados."
        if modo_atual == "degradado"
        else "Supervisor pronto. Publicação real segue protegida por validação, Git, catálogo, qualidade e PROMOGG_SUPERVISOR_PUBLICAR=true."
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
        "auditoria_ml": auditoria_ml,
        "classificacao_ml": classificacao_ml,
        "git": git,
        "comandos": comandos,
        "alertas": alertas,
        "avisos": classificacao_ml["avisos"],
        "bloqueios": bloqueios,
        "bloqueios_publicacao": bloqueios_publicacao,
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
