"""Pré-voo seguro para a operação de produção do Promogg."""

import os
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

from banco import DB_PATH, registrar_evento_sistema


ROOT = Path.cwd()


def _resultado(nome, nivel, mensagem):
    return {"nome": nome, "nivel": nivel, "mensagem": mensagem}


def _git_limpo():
    try:
        resultado = subprocess.run(
            ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True,
            text=True, check=False,
        )
    except OSError as erro:
        return False, f"Git indisponível: {erro}"
    if resultado.returncode:
        return False, "Não foi possível consultar o estado do Git."
    quantidade = len([linha for linha in resultado.stdout.splitlines() if linha.strip()])
    return quantidade == 0, "árvore de trabalho limpa" if not quantidade else f"{quantidade} alteração(ões) pendente(s)"


def _ignorado_no_git(caminho):
    resultado = subprocess.run(
        ["git", "check-ignore", "-q", caminho], cwd=ROOT, check=False,
    )
    return resultado.returncode == 0


def _tem_backups():
    pasta = ROOT / "backups"
    return bool(pasta.exists() and any(arquivo.is_file() for arquivo in pasta.rglob("*")))


def _conectar_banco_somente_leitura():
    caminho = (ROOT / DB_PATH).resolve()
    if not caminho.is_file():
        raise FileNotFoundError("banco.db não encontrado")
    conexao = sqlite3.connect(f"file:{caminho}?mode=ro", uri=True)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA query_only = ON")
    return conexao


def validar_preflight_somente_leitura():
    """Valida banco e artefatos estáticos existentes sem escrita ou migração."""
    erros = []
    try:
        with _conectar_banco_somente_leitura() as conn:
            integridade = str(conn.execute("PRAGMA integrity_check").fetchone()[0]).lower()
        if integridade != "ok":
            erros.append(f"SQLite integrity_check={integridade}")
    except (sqlite3.Error, OSError) as erro:
        erros.append(f"Banco somente leitura indisponível: {erro}")

    site = ROOT / "site"
    ofertas_path = site / "ofertas.json"
    try:
        ofertas = json.loads(ofertas_path.read_text(encoding="utf-8")).get("ofertas", [])
    except (OSError, json.JSONDecodeError) as erro:
        return erros + [f"ofertas.json inválido: {erro}"]
    if not isinstance(ofertas, list) or not ofertas:
        return erros + ["ofertas.json não contém ofertas públicas"]

    paginas = {str(caminho.relative_to(site).parent) for caminho in (site / "produto").glob("*/*/index.html")}
    esperadas = {str(oferta.get("produto_url") or "").strip("/") for oferta in ofertas}
    esperadas.discard("")
    if esperadas != paginas:
        erros.append("ofertas públicas e páginas individuais não correspondem")

    for indice, oferta in enumerate(ofertas, start=1):
        link = str(oferta.get("link") or "")
        imagem = str(oferta.get("imagem_url") or "")
        produto_url = str(oferta.get("produto_url") or "").strip("/")
        partes_url = produto_url.split("/")
        item_id = str(oferta.get("item_id") or (partes_url[1] if len(partes_url) >= 2 and partes_url[0] == "produto" else ""))
        titulo = str(oferta.get("titulo") or "")
        if not re.fullmatch(r"MLB\d{5,}", item_id):
            erros.append(f"oferta {indice}: item_id inválido")
        if not link.startswith("https://meli.la/"):
            erros.append(f"oferta {indice}: link meli.la inválido")
        if not imagem.startswith(("https://", "http://")):
            erros.append(f"oferta {indice}: imagem pública inválida")
        if re.search(r"(?i)(?:R\$\s*\d|\d+\s*%\s*OFF)", titulo):
            erros.append(f"oferta {indice}: título contém preço ou desconto")
        pagina = site / produto_url / "index.html"
        if not produto_url or not pagina.is_file():
            erros.append(f"oferta {indice}: página individual ausente")
            continue
        conteudo = pagina.read_text(encoding="utf-8").lower()
        if not all(marcador in conteudo for marcador in ("rel=\"canonical\"", "og:title", "twitter:card", "application/ld+json")):
            erros.append(f"oferta {indice}: SEO incompleto")
        if any(marcador in conteudo for marcador in ("observacao_interna", "aprovado_auto", "aprovado_manual", "pendente_revisao", "rejeitado")):
            erros.append(f"oferta {indice}: dado interno exposto")

    try:
        index = (site / "index.html").read_text(encoding="utf-8").lower()
        robots = (site / "robots.txt").read_text(encoding="utf-8").lower()
        sitemap = (site / "sitemap.xml").read_text(encoding="utf-8")
        analytics = (site / "analytics.js").read_text(encoding="utf-8")
        if not all(marcador in index for marcador in ("rel=\"canonical\"", "og:image", "twitter:card")):
            erros.append("SEO da página inicial incompleto")
        if "sitemap:" not in robots or "<urlset" not in sitemap:
            erros.append("robots.txt ou sitemap.xml inválido")
        if "PromoggAnalytics" not in analytics:
            erros.append("instrumentação de analytics ausente")
    except OSError as erro:
        erros.append(f"Artefato público ausente: {erro}")
    return erros


def _verificar_oauth(testar_remoto):
    from meli_oauth import status_oauth_local

    if not status_oauth_local():
        return _resultado("OAuth", "critico", "Credenciais OAuth ausentes ou incompletas no .env.")
    if not testar_remoto:
        return _resultado("OAuth", "ok", "Credenciais carregadas; teste remoto omitido no modo seco.")
    try:
        from meli_oauth import testar_token

        testar_token()
        return _resultado("OAuth", "ok", "Token validado na API do Mercado Livre.")
    except Exception as erro:
        return _resultado("OAuth", "critico", f"Token OAuth não pôde ser validado: {str(erro)[:220]}")


def executar_preflight_producao(testar_oauth_remoto=True, seco=False):
    """Verifica pré-requisitos sem iniciar, publicar ou alterar ofertas."""
    load_dotenv(ROOT / ".env", override=False)
    itens = []

    itens.append(_resultado("Python", "ok" if sys.version_info >= (3, 10) else "critico", f"Python {sys.version.split()[0]}"))
    try:
        with _conectar_banco_somente_leitura() as conn:
            integridade = str(conn.execute("PRAGMA integrity_check").fetchone()[0]).lower()
        itens.append(_resultado("Banco", "ok" if integridade == "ok" else "critico", f"SQLite integrity_check={integridade}"))
    except (sqlite3.Error, OSError) as erro:
        itens.append(_resultado("Banco", "critico", f"SQLite indisponível: {erro}"))

    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        from playwright_perfil import diagnosticar_perfil

        perfil = diagnosticar_perfil()
        if perfil["disponivel"]:
            itens.append(_resultado("Playwright", "ok", "Biblioteca e perfil Mercado Livre disponíveis."))
        elif perfil["existe"]:
            itens.append(_resultado("Playwright", "critico", "Perfil Mercado Livre está em uso ou possui locks."))
        else:
            itens.append(_resultado("Playwright", "critico", "Perfil Mercado Livre não encontrado."))
    except Exception as erro:
        itens.append(_resultado("Playwright", "critico", f"Playwright indisponível: {str(erro)[:220]}"))

    itens.append(_verificar_oauth(testar_oauth_remoto))

    try:
        analytics_js = ROOT / "site" / "analytics.js"
        analytics_pronto = analytics_js.is_file() and "PromoggAnalytics" in analytics_js.read_text(encoding="utf-8")
        endpoint_configurado = bool(re.search(r'data-analytics-url="https://', (ROOT / "site" / "index.html").read_text(encoding="utf-8")))
        if analytics_pronto:
            texto = "Instrumentação local pronta"
            if not endpoint_configurado:
                texto += "; endpoint público ainda não configurado"
                itens.append(_resultado("Analytics", "alerta", texto))
            else:
                itens.append(_resultado("Analytics", "ok", texto))
        else:
            itens.append(_resultado("Analytics", "critico", "JavaScript de analytics não foi gerado."))
    except Exception as erro:
        itens.append(_resultado("Analytics", "critico", f"Falha ao verificar analytics: {erro}"))

    try:
        import streamlit  # noqa: F401

        itens.append(_resultado("Painel", "ok", "Streamlit disponível para iniciar o painel."))
    except ImportError:
        itens.append(_resultado("Painel", "critico", "Streamlit não está instalado."))

    try:
        erros_catalogo = validar_preflight_somente_leitura()
        if erros_catalogo:
            itens.append(_resultado("Site", "critico", f"Validação do catálogo falhou: {erros_catalogo[0]}"))
        else:
            itens.append(_resultado("Site", "ok", "Catálogo, páginas, imagens, links meli.la e SEO validados."))
    except Exception as erro:
        itens.append(_resultado("Site", "critico", f"Falha ao validar site: {str(erro)[:220]}"))

    env_presente = (ROOT / ".env").is_file()
    tokens_presentes = all(os.getenv(nome, "").strip() for nome in (
        "MELI_ACCESS_TOKEN", "MELI_REFRESH_TOKEN", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
    ))
    itens.append(_resultado("Segurança .env", "ok" if env_presente and tokens_presentes else "critico", "Arquivo .env e tokens necessários carregados." if env_presente and tokens_presentes else "Arquivo .env ou token obrigatório ausente."))
    git_limpo, mensagem_git = _git_limpo()
    itens.append(_resultado("Git", "ok" if git_limpo else "critico", mensagem_git))
    protecoes = all(_ignorado_no_git(caminho) for caminho in (".env", "banco.db", "venv", "logs", "perfil_mercadolivre"))
    itens.append(_resultado("Proteção Git", "ok" if protecoes else "critico", "Arquivos sensíveis ignorados pelo Git." if protecoes else "Um caminho sensível não está ignorado pelo Git."))
    itens.append(_resultado("Backups", "ok" if _tem_backups() else "critico", "Backups locais disponíveis." if _tem_backups() else "Nenhum backup local disponível."))

    servicos = {
        "Scheduler": (ROOT / "scheduler.py").is_file(),
        "Monitor": (ROOT / "monitor_precos.py").is_file(),
        "Analytics": (ROOT / "servidor_analytics.py").is_file(),
        "Painel": (ROOT / "painel.py").is_file(),
        "Telegram": (ROOT / "publicador_telegram.py").is_file() and tokens_presentes,
    }
    for nome, pronto in servicos.items():
        itens.append(_resultado(f"Serviço {nome}", "ok" if pronto else "critico", "Pronto para iniciar." if pronto else "Pré-requisito não encontrado."))

    criticos = [item for item in itens if item["nivel"] == "critico"]
    alertas = [item for item in itens if item["nivel"] == "alerta"]
    return {"itens": itens, "criticos": criticos, "alertas": alertas, "aprovado": not criticos}


def imprimir_preflight(resultado):
    simbolos = {"ok": "[OK]", "alerta": "[ALERTA]", "critico": "[FALHA]"}
    print("Checklist de Produção Promogg")
    for item in resultado["itens"]:
        print(f"{simbolos[item['nivel']]} {item['nome']}: {item['mensagem']}")
    print(f"\nResultado: {'APROVADO' if resultado['aprovado'] else 'BLOQUEADO'}")
    if resultado["criticos"]:
        print("Pendências críticas:")
        for item in resultado["criticos"]:
            print(f"- {item['nome']}: {item['mensagem']}")


def registrar_resultado_preflight(resultado):
    status = "sucesso" if resultado["aprovado"] else "alerta"
    mensagem = "Pré-voo de produção aprovado" if resultado["aprovado"] else "Pré-voo de produção bloqueado"
    detalhes = f"criticos={len(resultado['criticos'])} alertas={len(resultado['alertas'])}"
    registrar_evento_sistema("preflight_producao", "operacao", status, mensagem, detalhes)
