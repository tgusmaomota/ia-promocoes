"""Visão local e sanitizada da saúde operacional do Promogg."""

import json
import os
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from banco import conectar, inicializar_banco
from estado_sistema import ONLINE, obter_estado_sistema


FORMATO_DATA = "%Y-%m-%d %H:%M:%S"
LIMITE_HORAS_OPERACAO = 24
LIMITE_HORAS_DEPLOY = 168
LIMITE_HORAS_COLETA_CRITICA = 48
PID_SCHEDULER = Path(".ia_promocoes.pid")
PID_ANALYTICS = Path(".promogg_analytics.pid")
PID_PAINEL = Path(".promogg_painel.pid")
CATALOGO_MINIMO = int(os.getenv("PROMOGG_CATALOGO_MINIMO", "30") or 30)


def _sanitizar(texto, limite=300):
    texto = " ".join(str(texto or "").replace("\n", " ").split())
    texto = re.sub(r"https?://\S+", "[url removida]", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\b(token|secret|password|senha|api[_-]?key)\s*[:=]\s*\S+", r"\1=[removido]", texto, flags=re.IGNORECASE)
    return texto[:limite]


def _data(valor):
    if not valor:
        return None
    try:
        return datetime.fromisoformat(str(valor))
    except ValueError:
        return None


def _idade_horas(valor, agora=None):
    data_evento = _data(valor)
    if not data_evento:
        return None
    return max(0, ((agora or datetime.now()) - data_evento).total_seconds() / 3600)


def _ultimo_evento(conn, tipo_evento, status="concluido"):
    row = conn.execute(
        """
        SELECT data_evento, mensagem, detalhes, status
        FROM sistema_eventos
        WHERE tipo_evento = ? AND (? IS NULL OR status IN (?, 'sucesso'))
        ORDER BY id DESC LIMIT 1
        """,
        (tipo_evento, status, status),
    ).fetchone()
    return dict(row) if row else None


def _ultimo_log(conn, etapas, trecho=""):
    filtros = " OR ".join("etapa = ?" for _ in etapas)
    parametros = list(etapas)
    consulta = f"SELECT criado_em AS data_evento, mensagem, dados AS detalhes, nivel AS status FROM logs WHERE ({filtros})"
    if trecho:
        consulta += " AND mensagem LIKE ?"
        parametros.append(f"%{trecho}%")
    consulta += " ORDER BY id DESC LIMIT 1"
    row = conn.execute(consulta, parametros).fetchone()
    return dict(row) if row else None


def _registro_recente(conn, tipo, etapas, trecho=""):
    return _ultimo_evento(conn, tipo) or _ultimo_log(conn, etapas, trecho)


def _pid_ativo(arquivo):
    try:
        pid = int(Path(arquivo).read_text(encoding="utf-8").strip())
        os.kill(pid, 0)
        estado = subprocess.run(
            ["ps", "-p", str(pid), "-o", "stat="],
            capture_output=True, text=True, check=False,
        ).stdout.strip()
        return bool(estado) and "Z" not in estado
    except (OSError, ValueError):
        return False


def _catalogo_publico():
    """Lê apenas o catálogo estático para checar a integridade operacional."""
    try:
        catalogo = json.loads(Path("site/ofertas.json").read_text(encoding="utf-8"))
        ofertas = catalogo.get("ofertas", [])
    except (OSError, ValueError, TypeError):
        ofertas = []
    paginas = len(list(Path("site/produto").glob("*/*/index.html")))
    links_invalidos = sum(
        1 for oferta in ofertas
        if not str(oferta.get("link") or oferta.get("link_afiliado") or "").startswith("https://meli.la/")
    )
    imagens_invalidas = sum(
        1 for oferta in ofertas
        if not str(oferta.get("imagem_url") or "").startswith(("https://", "http://"))
    )
    return {
        "ofertas": len(ofertas), "paginas": paginas,
        "links_invalidos": links_invalidos, "imagens_invalidas": imagens_invalidas,
    }


def _catalogo_integro(catalogo):
    return (
        catalogo["ofertas"] >= CATALOGO_MINIMO
        and catalogo["ofertas"] == catalogo["paginas"]
        and not catalogo["links_invalidos"]
        and not catalogo["imagens_invalidas"]
    )


def _coleta_compromete_disponibilidade(coleta, catalogo, momento):
    """Retorna motivos objetivos para elevar falhas de coleta a incidente crítico."""
    motivos = []
    idade = _idade_horas(coleta["data_evento"], momento) if coleta else None
    if not _catalogo_integro(catalogo):
        motivos.append("catálogo público não está íntegro")
    if idade is None or idade > LIMITE_HORAS_COLETA_CRITICA:
        motivos.append("não há coleta válida recente")
    return motivos


def _fallback_playwright_ativo(conn):
    modo = os.getenv("MELI_COLETA_MODO", "auto").strip().lower() or "auto"
    row = conn.execute(
        "SELECT status, bloqueado_ate FROM coleta_api_saude WHERE chave = 'busca'"
    ).fetchone()
    if not row or str(row["status"]) != "403" or modo == "api":
        return False
    bloqueado_ate = _data(row["bloqueado_ate"])
    return modo in {"auto", "playwright"} and (not bloqueado_ate or bloqueado_ate > datetime.now())


def _classificar_evento(item, fallback_playwright=False):
    """Classifica sem elevar falhas degradadas a incidentes críticos."""
    texto = f"{item.get('origem', '')} {item.get('mensagem', '')} {item.get('detalhes', '')}".lower()
    status = str(item.get("status") or "").lower()
    tipo = str(item.get("tipo_evento") or "").lower()

    if "http 403" in texto or ("api" in texto and "fallback" in texto):
        return "alerta"
    if "oferta pública duplicada ignorada" in texto:
        return "info"
    if "fallback local" in texto or ("ollama" in texto and "fallback" in texto):
        return "aviso"
    if "analytics" in texto and ("sem registro" in texto or "indispon" in texto):
        return "aviso"
    if status == "critico" or any(chave in texto for chave in (
        "banco indisponível", "integridade do banco", "sqlite corromp", "dados corrompidos",
    )):
        return "critico"
    if tipo in {"validacao", "deploy_github"} and status in {"erro", "critico"}:
        return "critico"
    if status in {"erro", "error"}:
        return "erro"
    if status in {"alerta", "atencao", "aviso", "warning"}:
        return "alerta" if status in {"alerta", "atencao", "warning"} else "aviso"
    return "info"


def _eventos_24h(conn, desde, fallback_playwright):
    eventos = [dict(row) for row in conn.execute(
        """
        SELECT data_evento, tipo_evento, origem, status, mensagem, detalhes
        FROM sistema_eventos
        WHERE data_evento >= ?
          AND status IN ('erro', 'critico', 'alerta', 'atencao', 'aviso', 'warning')
        ORDER BY id DESC LIMIT 80
        """, (desde,)
    ).fetchall()]
    logs = [dict(row) for row in conn.execute(
        """
        SELECT criado_em AS data_evento, etapa AS origem, nivel AS status, mensagem, dados AS detalhes
        FROM logs WHERE criado_em >= ? AND nivel IN ('error', 'warning') ORDER BY id DESC LIMIT 80
        """, (desde,)
    ).fetchall()]
    vistos = set()
    resultado = []
    for item in eventos + logs:
        chave = (item["data_evento"], item["origem"], item["mensagem"])
        if chave in vistos:
            continue
        vistos.add(chave)
        resultado.append({
            "data_evento": item["data_evento"], "origem": _sanitizar(item["origem"], 80),
            "mensagem": _sanitizar(item["mensagem"]),
            "nivel": _classificar_evento(item, fallback_playwright),
        })
    return resultado[:80]


def _eventos_recentes(conn, limite=12):
    return [
        {
            "data": row["data_evento"],
            "origem": _sanitizar(row["origem"], 80),
            "mensagem": _sanitizar(row["mensagem"]),
        }
        for row in conn.execute(
            "SELECT data_evento, origem, mensagem FROM sistema_eventos ORDER BY id DESC LIMIT ?",
            (limite,),
        ).fetchall()
    ]


def _exibir_registro(registro):
    return registro["data_evento"] if registro else "sem registro ainda"


def obter_relatorio_saude(agora=None):
    """Retorna um relatório seguro mesmo quando o banco ainda não possui histórico."""
    inicializar_banco()
    momento = agora or datetime.now()
    desde = (momento - timedelta(hours=24)).strftime(FORMATO_DATA)
    integridade_banco = "OK"
    try:
        with conectar() as conn:
            integridade_banco = str(conn.execute("PRAGMA integrity_check").fetchone()[0])
            coleta = _registro_recente(conn, "coleta", ["coletor_mercadolivre"], "Coleta finalizada")
            monitoramento = _registro_recente(conn, "monitoramento_precos", ["monitor_precos_sucesso"])
            site = _registro_recente(conn, "geracao_site", ["site"], "Site público gerado")
            deploy = _registro_recente(conn, "deploy_github", ["deploy_site"], "enviado para GitHub")
            telegram = _registro_recente(conn, "telegram", ["auditoria_telegram"], "publicada no Telegram")
            analytics = conn.execute(
                "SELECT MAX(criado_em) FROM cliques WHERE COALESCE(tipo_evento, 'ver_oferta') != 'teste'"
            ).fetchone()[0]
            ia = conn.execute("SELECT criado_em, modo_resposta FROM perguntas_assistente ORDER BY id DESC LIMIT 1").fetchone()
            ultima_atualizacao_precos = conn.execute(
                "SELECT MAX(data_verificacao) FROM historico_precos"
            ).fetchone()[0]
            fallback_playwright = _fallback_playwright_ativo(conn)
            eventos_24h = _eventos_24h(conn, desde, fallback_playwright)
            eventos = _eventos_recentes(conn)
            monitoradas = conn.execute("SELECT COUNT(*) FROM produtos WHERE plataforma = 'mercado_livre'").fetchone()[0]
            aprovadas = conn.execute(
                "SELECT COUNT(*) FROM postagens WHERE status IN ('aprovado_auto', 'aprovado_manual', 'publicado')"
            ).fetchone()[0]
            pendentes = conn.execute("SELECT COUNT(*) FROM postagens WHERE status = 'pendente_revisao'").fetchone()[0]
            indisponiveis = conn.execute("SELECT COUNT(*) FROM produtos WHERE status = 'indisponivel'").fetchone()[0]
    except Exception as erro:
        return {
            "status_geral": "Erro", "indicador": "vermelho", "integridade_banco": "falha",
            "alertas": [{"nivel": "critico", "mensagem": f"Banco indisponível: {_sanitizar(erro)}"}],
            "ultima_coleta": "sem registro ainda", "ultima_atualizacao_precos": "sem registro ainda",
            "ultimo_monitoramento": "sem registro ainda", "ultimo_site_gerado": "sem registro ainda",
            "ultimo_deploy": "sem registro ainda", "ultimo_telegram": "sem registro ainda",
            "ultimo_analytics": "sem registro ainda", "ultima_ia_consultiva": "sem registro ainda",
            "modo_ultima_ia": "sem registro ainda", "ofertas_monitoradas": 0, "ofertas_aprovadas": 0,
            "ofertas_pendentes": 0, "produtos_indisponiveis": 0, "erros_24h": [], "eventos_recentes": [],
            "eventos_classificados": {"critico": [], "erro": [], "alerta": [], "aviso": [], "info": []},
            "servicos": {}, "catalogo": {}, "fallback_playwright": False,
        }

    alertas = []
    estado = obter_estado_sistema()
    servicos = {
        "site": True,
        "scheduler": _pid_ativo(PID_SCHEDULER),
        "analytics": _pid_ativo(PID_ANALYTICS),
        "painel": _pid_ativo(PID_PAINEL),
    }
    catalogo = _catalogo_publico()
    classificados = {nivel: [] for nivel in ("critico", "erro", "alerta", "aviso", "info")}
    for evento in eventos_24h:
        classificados[evento["nivel"]].append(evento)
    for evento in eventos[:12]:
        classificados["info"].append({
            "data_evento": evento["data"], "origem": evento["origem"],
            "mensagem": evento["mensagem"], "nivel": "info",
        })

    def verificar_recencia(nome, registro, limite):
        idade = _idade_horas(registro["data_evento"], momento) if registro else None
        if idade is None:
            alertas.append({"nivel": "atencao", "mensagem": f"{nome}: sem registro ainda."})
        elif idade > limite:
            alertas.append({"nivel": "atencao", "mensagem": f"{nome}: último registro há {idade:.1f}h."})

    verificar_recencia("Coleta", coleta, LIMITE_HORAS_OPERACAO)
    verificar_recencia("Monitoramento de preços", monitoramento, LIMITE_HORAS_OPERACAO)
    verificar_recencia("Histórico de preços", {"data_evento": ultima_atualizacao_precos} if ultima_atualizacao_precos else None, LIMITE_HORAS_OPERACAO)
    verificar_recencia("Geração do site", site, LIMITE_HORAS_OPERACAO)
    verificar_recencia("Deploy GitHub Pages", deploy, LIMITE_HORAS_DEPLOY)
    if analytics:
        verificar_recencia("Atualização do analytics", {"data_evento": analytics}, LIMITE_HORAS_DEPLOY)
        analytics_situacao = "recebendo eventos"
    else:
        analytics_situacao = "aguardando cliques reais" if servicos["analytics"] else "sem cliques e serviço local indisponível"
    verificar_recencia("Execução da IA consultiva", {"data_evento": ia["criado_em"]} if ia else None, LIMITE_HORAS_DEPLOY)
    if ia and ia["modo_resposta"] == "regras":
        alertas.append({"nivel": "aviso", "mensagem": "A última consulta da IA usou o fallback local."})
    if aprovadas and (not telegram or (_idade_horas(telegram["data_evento"], momento) or 0) > LIMITE_HORAS_OPERACAO):
        alertas.append({"nivel": "atencao", "mensagem": "Há ofertas aprovadas sem publicação recente no Telegram."})
    if integridade_banco.lower() != "ok":
        alertas.insert(0, {"nivel": "critico", "mensagem": "Falha crítica na integridade do banco SQLite."})
    if estado["estado"] == ONLINE and not servicos["scheduler"]:
        alertas.insert(0, {"nivel": "critico", "mensagem": "Estado ONLINE, mas o scheduler não está em execução."})
    if catalogo["ofertas"] != catalogo["paginas"]:
        alertas.insert(0, {"nivel": "critico", "mensagem": "Catálogo público e páginas individuais estão inconsistentes."})
    if catalogo["ofertas"] < CATALOGO_MINIMO:
        alertas.insert(0, {"nivel": "critico", "mensagem": f"Catálogo público abaixo do mínimo configurado ({CATALOGO_MINIMO})."})
    if catalogo["links_invalidos"]:
        alertas.insert(0, {"nivel": "critico", "mensagem": f"Há {catalogo['links_invalidos']} link(s) afiliado(s) inválido(s) no catálogo."})
    if catalogo["imagens_invalidas"]:
        alertas.insert(0, {"nivel": "critico", "mensagem": f"Há {catalogo['imagens_invalidas']} imagem(ns) inválida(s) no catálogo."})
    if estado["estado"] == ONLINE and not servicos["analytics"]:
        alertas.append({"nivel": "alerta", "mensagem": "Analytics em tempo real não está em execução."})
    if estado["estado"] != "OFFLINE" and not servicos["painel"]:
        alertas.append({"nivel": "alerta", "mensagem": "Painel local não está em execução."})
    if fallback_playwright:
        alertas.append({"nivel": "alerta", "mensagem": "Busca da API Mercado Livre está em 403; fallback Playwright está ativo."})
    if classificados["erro"]:
        alertas.append({"nivel": "alerta", "mensagem": f"{len(classificados['erro'])} erro(s) operacional(is) sem impacto crítico confirmado nas últimas 24h."})
    if classificados["alerta"]:
        alertas.append({"nivel": "alerta", "mensagem": f"{len(classificados['alerta'])} alerta(s) operacional(is) nas últimas 24h."})
    if len([evento for evento in classificados["erro"] if evento["origem"] == "telegram"]) >= 3:
        alertas.insert(0, {"nivel": "critico", "mensagem": "Falhas repetidas de publicação no Telegram."})
    erros_coleta = [evento for evento in classificados["erro"] if evento["origem"] in {"coleta", "mercado_livre", "scheduler"}]
    coleta_critica = _coleta_compromete_disponibilidade(coleta, catalogo, momento)
    if len(erros_coleta) >= 3:
        if coleta_critica:
            alertas.insert(0, {"nivel": "critico", "mensagem": "Coleta falhou repetidamente e compromete a disponibilidade: " + "; ".join(coleta_critica) + "."})
            coleta_situacao = "falha crítica de coleta"
        else:
            alertas.append({"nivel": "alerta", "mensagem": f"Última coleta teve falha, mas catálogo público segue íntegro com {catalogo['ofertas']} ofertas e {catalogo['paginas']} páginas."})
            coleta_situacao = "falha isolada sem impacto atual no catálogo"
    else:
        coleta_situacao = "coleta recente disponível"
    if aprovadas == 0:
        alertas.append({"nivel": "alerta", "mensagem": "Não há ofertas aprovadas para publicação."})

    status_geral = "Erro" if any(alerta["nivel"] == "critico" for alerta in alertas) else "Atenção" if alertas else "OK"
    return {
        "status_geral": status_geral,
        "ultima_coleta": _exibir_registro(coleta),
        "coleta_situacao": coleta_situacao,
        "ultimo_analytics": analytics or "sem registro ainda",
        "analytics_situacao": analytics_situacao,
        "ultima_ia_consultiva": ia["criado_em"] if ia else "sem registro ainda",
        "modo_ultima_ia": ia["modo_resposta"] if ia else "sem registro ainda",
        "ultima_atualizacao_precos": ultima_atualizacao_precos or "sem registro ainda",
        "ultimo_monitoramento": _exibir_registro(monitoramento),
        "ultimo_site_gerado": _exibir_registro(site),
        "ultimo_deploy": _exibir_registro(deploy),
        "ultimo_telegram": _exibir_registro(telegram),
        "ofertas_monitoradas": monitoradas,
        "ofertas_aprovadas": aprovadas,
        "ofertas_pendentes": pendentes,
        "produtos_indisponiveis": indisponiveis,
        "erros_24h": classificados["erro"],
        "eventos_recentes": eventos,
        "eventos_classificados": classificados,
        "servicos": servicos,
        "catalogo": catalogo,
        "fallback_playwright": fallback_playwright,
        "estado_sistema": estado["estado"],
        "integridade_banco": integridade_banco,
        "alertas": alertas,
        "indicador": "vermelho" if status_geral == "Erro" else "amarelo" if status_geral == "Atenção" else "verde",
    }


def imprimir_relatorio_saude():
    relatorio = obter_relatorio_saude()
    print(f"Saúde do Sistema: {relatorio['status_geral']}")
    print(f"Última coleta: {relatorio['ultima_coleta']}")
    print(f"Coleta: {relatorio.get('coleta_situacao', 'sem registro')}")
    print(f"Última atualização de preços: {relatorio['ultima_atualizacao_precos']}")
    print(f"Último monitoramento: {relatorio['ultimo_monitoramento']}")
    print(f"Último site gerado: {relatorio['ultimo_site_gerado']}")
    print(f"Último deploy GitHub: {relatorio['ultimo_deploy']}")
    print(f"Último Telegram: {relatorio['ultimo_telegram']}")
    print(f"Último analytics: {relatorio['ultimo_analytics']}")
    print(f"Analytics: {relatorio.get('analytics_situacao', 'sem registro')}")
    print(f"Última IA consultiva: {relatorio['ultima_ia_consultiva']} ({relatorio['modo_ultima_ia']})")
    print(f"Banco SQLite: {relatorio['integridade_banco']}")
    print(f"Ofertas monitoradas: {relatorio['ofertas_monitoradas']}")
    print(f"Ofertas aprovadas: {relatorio['ofertas_aprovadas']}")
    print(f"Ofertas pendentes: {relatorio['ofertas_pendentes']}")
    print(f"Produtos indisponíveis: {relatorio['produtos_indisponiveis']}")
    print(f"Estado do sistema: {relatorio.get('estado_sistema', 'sem registro')}")
    print(f"Catálogo público: {relatorio.get('catalogo', {}).get('ofertas', 0)} ofertas | {relatorio.get('catalogo', {}).get('paginas', 0)} páginas")
    print(f"Fallback Playwright: {'ativo' if relatorio.get('fallback_playwright') else 'não necessário'}")
    print(f"Erros operacionais nas últimas 24h: {len(relatorio['erros_24h'])}")
    if relatorio["alertas"]:
        print("Alertas:")
        for alerta in relatorio["alertas"]:
            print(f"- {alerta['nivel'].upper()}: {alerta['mensagem']}")
    else:
        print("Alertas: nenhum")
    return relatorio


def imprimir_relatorio_saude_detalhada():
    """Exibe categorias operacionais sem imprimir detalhes sensíveis."""
    relatorio = imprimir_relatorio_saude()
    print("\nServiços:")
    for nome, ativo in relatorio.get("servicos", {}).items():
        print(f"- {nome}: {'ativo' if ativo else 'parado'}")
    nomes = {
        "critico": "Erros críticos",
        "erro": "Erros operacionais",
        "alerta": "Alertas",
        "aviso": "Avisos",
        "info": "Eventos informativos",
    }
    for nivel, titulo in nomes.items():
        itens = relatorio.get("eventos_classificados", {}).get(nivel, [])
        print(f"\n{titulo}: {len(itens)}")
        for item in itens[:10]:
            print(f"- {item['data_evento']} [{item['origem']}] {item['mensagem']}")
    alertas_criticos = [alerta for alerta in relatorio.get("alertas", []) if alerta["nivel"] == "critico"]
    if alertas_criticos:
        print("\nDiagnósticos críticos:")
        for alerta in alertas_criticos:
            print(f"- {alerta['mensagem']}")
    if relatorio["status_geral"] == "Erro":
        recomendacao = "Corrija os itens críticos antes de confiar na operação automática."
    elif relatorio["status_geral"] == "Atenção":
        recomendacao = "A operação segue disponível, com degradações acompanhadas pelos alertas."
    else:
        recomendacao = "Operação íntegra; mantenha o acompanhamento normal."
    print(f"\nRecomendação: {recomendacao}")
    return relatorio


def validar_saude_sistema():
    erros = []
    try:
        relatorio = obter_relatorio_saude()
        campos = {"status_geral", "ultima_coleta", "coleta_situacao", "ultima_atualizacao_precos", "ultimo_monitoramento", "ultimo_site_gerado", "ultimo_deploy", "ultimo_telegram", "ultimo_analytics", "analytics_situacao", "ultima_ia_consultiva", "integridade_banco", "erros_24h", "alertas", "eventos_classificados", "catalogo", "servicos"}
        if not campos.issubset(relatorio):
            erros.append("Relatório de saúde incompleto")
        conteudo = json.dumps(relatorio, ensure_ascii=False).lower()
        if any(termo in conteudo for termo in ("telegram_bot_token", "api_key=", "password=", "senha=")):
            erros.append("Relatório de saúde contém dado sensível")
        with conectar() as conn:
            existe = conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'sistema_eventos'").fetchone()
        if not existe:
            erros.append("Tabela sistema_eventos não existe")
    except Exception as erro:
        erros.append(f"Falha no painel de saúde: {_sanitizar(erro)}")
    return erros


if __name__ == "__main__":
    imprimir_relatorio_saude()
