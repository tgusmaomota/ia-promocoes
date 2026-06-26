"""Ciclo automático seguro do Promogg.

Orquestra coleta -> histórico -> afiliados -> curadoria -> site -> validação
-> publicação, mantendo dry-run sem mutações e publicação real atrás de
flag explícita.
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from banco import conectar, inicializar_banco, proxima_postagem_pendente
from curadoria_automatica import executar_curadoria_automatica
from estado_sistema import obter_estado_sistema
from gerador_link_mercadolivre import link_afiliado_valido
from meli_oauth import status_oauth_local
from operacao_sistema import criar_backup_emergencia
from publicador_telegram import validar_postagem
from homologacao_publicacao import _git_status_classificado
from qualidade_catalogo import auditar_qualidade_catalogo
from saude_sistema import obter_relatorio_saude


RELATORIO_CICLO = Path("RELATORIO_CICLO_AUTOMATICO.md")
RELATORIO_SCORE = Path("RELATORIO_SCORE_ADAPTATIVO.md")


def agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _contagens_banco():
    inicializar_banco()
    with conectar() as conn:
        status_postagens = {
            row["status"]: row["total"]
            for row in conn.execute("SELECT status, COUNT(*) AS total FROM postagens GROUP BY status")
        }
        historico = conn.execute("SELECT COUNT(*) FROM historico_precos").fetchone()[0]
        com_queda = conn.execute(
            "SELECT COUNT(*) FROM produtos WHERE COALESCE(variacao_preco, 0) < 0"
        ).fetchone()[0]
        menor_preco = conn.execute(
            "SELECT COUNT(*) FROM produtos WHERE COALESCE(destaque_menor_preco, 0) = 1"
        ).fetchone()[0]
        com_meli = conn.execute(
            "SELECT COUNT(*) FROM produtos WHERE link_afiliado LIKE 'https://meli.la/%'"
        ).fetchone()[0]
        publicaveis = conn.execute(
            """
            SELECT COUNT(*) FROM postagens
            WHERE status IN ('aprovado_auto','aprovado_manual')
              AND link_afiliado LIKE 'https://meli.la/%'
            """
        ).fetchone()[0]
    return {
        "status_postagens": status_postagens,
        "historico_registros": historico,
        "produtos_com_queda": com_queda,
        "produtos_no_menor_preco": menor_preco,
        "produtos_com_meli_la": com_meli,
        "publicaveis_atuais": publicaveis,
    }


def _site_atual():
    def resumo(pasta):
        base = Path(pasta)
        try:
            dados = json.loads((base / "ofertas.json").read_text(encoding="utf-8"))
            ofertas = dados.get("ofertas", [])
        except Exception:
            ofertas = []
        paginas = len(list((base / "produto").glob("*/*/index.html")))
        return {"ofertas": len(ofertas), "paginas": paginas}

    return {"site": resumo("site"), "dist_site": resumo("dist_site")}


def _simular_telegram(analises_curadoria=None):
    postagem = proxima_postagem_pendente()
    if postagem:
        ok, motivo = validar_postagem(postagem, forcar_intervalo=False)
        return {
            "ok": bool(ok),
            "motivo": motivo,
            "postagem_id": postagem.get("id"),
            "titulo": postagem.get("titulo"),
            "preco": postagem.get("preco"),
            "link_afiliado_valido": link_afiliado_valido(postagem.get("link_afiliado")),
            "origem": "fila_atual",
        }

    aprovados_simulados = [a for a in (analises_curadoria or []) if a.get("decisao") == "aprovado_auto"]
    if aprovados_simulados:
        item = aprovados_simulados[0]
        return {
            "ok": True,
            "motivo": "publicaria após aplicar curadoria automática",
            "postagem_id": item.get("postagem_id") or "novo",
            "titulo": item.get("titulo"),
            "preco": None,
            "link_afiliado_valido": True,
            "origem": "curadoria_dry_run",
        }

    return {"ok": False, "motivo": "nenhuma oferta aprovada disponível para simulação", "origem": "sem_fila"}


def _executar_comando(args):
    proc = subprocess.run([sys.executable, "ia_promocoes.py", *args], capture_output=True, text=True)
    return {
        "comando": " ".join(["python3", "ia_promocoes.py", *args]),
        "codigo": proc.returncode,
        "stdout": (proc.stdout or "").strip()[-2000:],
        "stderr": (proc.stderr or "").strip()[-2000:],
    }


def _bloqueios_publicacao(qualidade, saude, site, publicar, telegram, git):
    bloqueios = []
    metricas = qualidade.get("metricas", {})
    if not publicar:
        bloqueios.append("publicação real exige --publicar")
    if site["site"]["ofertas"] < 30:
        bloqueios.append("catálogo abaixo do mínimo de 30 ofertas")
    if site["site"]["ofertas"] != site["site"]["paginas"]:
        bloqueios.append("páginas de produto não batem com ofertas")
    if metricas.get("sem_meli_la", 0):
        bloqueios.append("há ofertas públicas sem meli.la")
    if metricas.get("imagens_quebradas", 0) or metricas.get("imagens_ausentes", 0):
        bloqueios.append("há imagens ausentes/quebradas")
    if metricas.get("preco_invalido", 0):
        bloqueios.append("há preços inválidos")
    if metricas.get("paginas_quebradas", 0) or metricas.get("seo_sem_titulo", 0) or metricas.get("seo_sem_descricao", 0):
        bloqueios.append("há falhas de páginas/SEO")
    if qualidade.get("ressalvas_bloqueantes"):
        bloqueios.append("auditoria de qualidade tem ressalvas bloqueantes")
    if site["dist_site"]["ofertas"] and site["dist_site"]["ofertas"] != site["site"]["ofertas"]:
        bloqueios.append("dist_site diverge de site em quantidade de ofertas")
    if saude.get("criticos"):
        bloqueios.append("saúde do sistema possui críticos")
    if not telegram.get("ok"):
        bloqueios.append(f"Telegram em simulação falhou: {telegram.get('motivo')}")
    if git.get("bloqueantes"):
        bloqueios.append("Git possui alterações bloqueantes fora dos artefatos permitidos")
    return bloqueios


def _gerar_relatorio_score(curadoria):
    itens = curadoria.get("itens", [])
    linhas = [
        "# Relatório de Score Adaptativo",
        "",
        f"- Gerado em: {agora()}",
        "- Fonte: banco local, histórico de preços, dados comerciais coletados e analytics local quando disponível.",
        "- Aprendizado por clique: aguardando volume público suficiente; nenhum dado foi inventado.",
        "",
        "## Componentes",
        "- `score_integridade`: item_id, meli.la, preço, imagem, título, permalink e disponibilidade.",
        "- `score_preco`: desconto atual e economia real.",
        "- `score_historico`: menor preço, queda recente e observações históricas.",
        "- `score_vendedor`: avaliação, vendidos, vendedor confiável, loja oficial e mais vendido.",
        "- `score_categoria`: categoria real/confiável.",
        "- `score_publicacao`: confiabilidade da fonte, histórico e aptidão de publicação.",
        "- `score_final`: soma normalizada usada na decisão.",
        "",
        "## Amostras",
    ]
    for item in itens[:30]:
        comp = item.get("componentes", {})
        score_vendedor = min(14, comp.get("comercial", 0))
        score_categoria = 1 if "categoria confiável" in item.get("positivos", []) else 0
        score_publicacao = comp.get("confiabilidade", 0)
        linhas.append(
            f"- {item['decisao']} | final={item['score']:g} | "
            f"integridade={comp.get('integridade', 0):g}, preço={comp.get('preco', 0):g}, "
            f"histórico={comp.get('historico', 0):g}, vendedor={score_vendedor:g}, "
            f"categoria={score_categoria:g}, publicação={score_publicacao:g} | "
            f"{item['item_id']} | {item['motivo']}"
        )
    RELATORIO_SCORE.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def _gerar_relatorio(resultado):
    linhas = [
        "# Relatório do Ciclo Automático",
        "",
        f"- Gerado em: {agora()}",
        f"- Modo: {'dry-run' if resultado['dry_run'] else 'execução real'}",
        f"- Publicar solicitado: {resultado['publicar']}",
        f"- Backup: {resultado.get('backup') or 'não aplicável'}",
        f"- Estado do sistema: {resultado['estado'].get('estado')}",
        "",
        "## Resumo",
        f"- Coletadas: {resultado['coleta'].get('coletadas', 0)}",
        f"- Atualizadas: {resultado['precos'].get('atualizadas', 0)}",
        f"- Com histórico: {resultado['banco']['historico_registros']}",
        f"- Com queda: {resultado['banco']['produtos_com_queda']}",
        f"- No menor preço: {resultado['banco']['produtos_no_menor_preco']}",
        f"- Com meli.la: {resultado['banco']['produtos_com_meli_la']}",
        f"- Aprovadas automaticamente: {resultado['curadoria']['aprovados_auto']}",
        f"- Rejeitadas automaticamente: {resultado['curadoria']['rejeitados']}",
        f"- Pendentes: {resultado['curadoria']['pendentes']}",
        f"- Pendentes estimados após aplicar: {resultado['curadoria'].get('pendentes_estimados_pos_aplicacao', resultado['curadoria']['pendentes'])}",
        f"- Publicáveis atuais: {resultado['banco']['publicaveis_atuais']}",
        f"- Publicáveis estimadas após curadoria: {resultado['publicaveis_estimadas']}",
        "",
        "## Site e qualidade",
        f"- site/: {resultado['site']['site']['ofertas']} ofertas, {resultado['site']['site']['paginas']} páginas",
        f"- dist_site/: {resultado['site']['dist_site']['ofertas']} ofertas, {resultado['site']['dist_site']['paginas']} páginas",
        f"- Qualidade: {resultado['qualidade'].get('indicador')}",
        f"- Git permitido: {len(resultado['git'].get('permitidas', []))}",
        f"- Git bloqueante: {len(resultado['git'].get('bloqueantes', []))}",
        "",
        "## Telegram simulado",
        f"- OK: {resultado['telegram']['ok']}",
        f"- Motivo: {resultado['telegram']['motivo']}",
        f"- Oferta: {resultado['telegram'].get('titulo') or 'nenhuma'}",
        "",
        "## Bloqueios",
    ]
    linhas += [f"- {b}" for b in resultado["bloqueios"]] or ["- nenhum"]
    linhas += [
        "",
        "## Status final",
        f"- Seguro para `ciclo-automatico`: {resultado['seguro_ciclo']}",
        f"- Seguro para `ciclo-automatico --publicar`: {resultado['seguro_publicar']}",
        "- Telegram real, deploy real e ONLINE não são executados no dry-run.",
    ]
    if resultado.get("passos_reais"):
        linhas += ["", "## Passos reais executados"]
        for passo in resultado["passos_reais"]:
            linhas.append(f"- `{passo['comando']}` -> código {passo['codigo']}")
    RELATORIO_CICLO.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def executar_ciclo_automatico(dry_run=True, publicar=False):
    estado = obter_estado_sistema()
    backup = "" if dry_run else str(criar_backup_emergencia())
    oauth_status = status_oauth_local()
    oauth = oauth_status if isinstance(oauth_status, dict) else {"configurado": bool(oauth_status)}
    perfil_ok = Path("perfil_mercadolivre").exists()
    passos_reais = []

    if dry_run:
        coleta = {"status": "simulado", "coletadas": 0, "observacao": "coleta real não executada em dry-run"}
        precos = {"status": "simulado", "atualizadas": 0, "observacao": "consulta/atualização real não executada em dry-run"}
        afiliados = {"status": "simulado", "gerados": 0, "observacao": "portal afiliado não aberto em dry-run"}
        curadoria = executar_curadoria_automatica(dry_run=True)
    else:
        for args in (["coletar"], ["gerar-afiliados"]):
            passos_reais.append(_executar_comando(args))
        curadoria = executar_curadoria_automatica(dry_run=False)
        passos_reais.append(_executar_comando(["gerar-site"]))
        precos = {"status": "executado_indiretamente", "atualizadas": 0, "observacao": "histórico atualizado pelas rotinas de coleta/monitoramento disponíveis"}
        coleta = {"status": "executado", "coletadas": 0, "observacao": "ver saída dos passos reais"}
        afiliados = {"status": "executado", "gerados": 0, "observacao": "ver saída dos passos reais"}

    banco = _contagens_banco()
    site = _site_atual()
    qualidade = auditar_qualidade_catalogo()
    saude = obter_relatorio_saude()
    telegram = _simular_telegram(curadoria.get("itens", []))
    git = _git_status_classificado()
    publicaveis_estimadas = banco["publicaveis_atuais"] + (curadoria["aprovados_auto"] if dry_run else 0)
    bloqueios = _bloqueios_publicacao(qualidade, saude, site, publicar, telegram, git)

    if not dry_run:
        passos_reais.append(_executar_comando(["validar", "--somente-leitura"]))
        passos_reais.append(_executar_comando(["auditar-qualidade-catalogo"]))
        if publicar and not bloqueios:
            passos_reais.append(_executar_comando(["subir-site"]))
            passos_reais.append(_executar_comando(["publicar-um"]))

    resultado = {
        "dry_run": dry_run,
        "publicar": publicar,
        "backup": backup,
        "estado": estado,
        "oauth": oauth,
        "perfil_playwright_ok": perfil_ok,
        "coleta": coleta,
        "precos": precos,
        "afiliados": afiliados,
        "curadoria": curadoria,
        "banco": banco,
        "site": site,
        "qualidade": qualidade,
        "saude": saude,
        "telegram": telegram,
        "git": git,
        "publicaveis_estimadas": publicaveis_estimadas,
        "bloqueios": bloqueios,
        "seguro_ciclo": bool(oauth.get("configurado") and perfil_ok),
        "seguro_publicar": not bloqueios,
        "passos_reais": passos_reais,
    }
    _gerar_relatorio_score(curadoria)
    _gerar_relatorio(resultado)
    return resultado
