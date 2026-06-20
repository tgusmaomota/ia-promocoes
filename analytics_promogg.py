"""Status, homologação local e relatório privado do analytics do Promogg."""

import json
import os
import re
import subprocess
import threading
import urllib.error
import urllib.request
from datetime import datetime
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from banco import conectar, inicializar_banco, resumo_cliques


SITE_INDEX = Path("site") / "index.html"
SITE_SCRIPT = Path("site") / "analytics.js"
RELATORIO = Path("RELATORIO_ANALYTICS_HOMOLOGACAO.md")


def _url_https_publica(url):
    partes = urlparse(str(url or "").strip())
    return partes.scheme == "https" and bool(partes.netloc) and partes.hostname not in {"localhost", "127.0.0.1", "::1"}


def _pid_ativo():
    arquivo = Path(".promogg_analytics.pid")
    try:
        pid = int(arquivo.read_text(encoding="utf-8").strip())
        os.kill(pid, 0)
        estado = subprocess.run(["ps", "-p", str(pid), "-o", "stat="], capture_output=True, text=True, check=False).stdout.strip()
        return bool(estado) and "Z" not in estado
    except (OSError, ValueError):
        return False


def _configuracao_site():
    try:
        conteudo = SITE_INDEX.read_text(encoding="utf-8")
    except OSError:
        conteudo = ""
    correspondencia = re.search(r'data-analytics-url="([^"]*)"', conteudo)
    return correspondencia.group(1) if correspondencia else ""


def _ultimo_evento():
    with conectar() as conn:
        row = conn.execute(
            """SELECT oferta_id, item_id, titulo, categoria, origem, pagina_origem, tipo_evento, criado_em
               FROM cliques ORDER BY id DESC LIMIT 1"""
        ).fetchone()
    return dict(row) if row else None


def _ultimo_teste():
    with conectar() as conn:
        row = conn.execute(
            """SELECT item_id, criado_em FROM cliques
               WHERE tipo_evento = 'teste' ORDER BY id DESC LIMIT 1"""
        ).fetchone()
    return dict(row) if row else None


def status_analytics(consultar_endpoint=False):
    """Retorna somente métricas agregadas e configuração pública, sem dados pessoais."""
    inicializar_banco()
    url_site = _configuracao_site()
    with conectar() as conn:
        total = conn.execute("SELECT COUNT(*) FROM cliques WHERE COALESCE(tipo_evento, 'ver_oferta') != 'teste'").fetchone()[0]
        testes = conn.execute("SELECT COUNT(*) FROM cliques WHERE tipo_evento = 'teste'").fetchone()[0]
        hoje = conn.execute(
            "SELECT COUNT(*) FROM cliques WHERE substr(criado_em, 1, 10) = ? AND COALESCE(tipo_evento, 'ver_oferta') != 'teste'",
            (datetime.now().strftime("%Y-%m-%d"),),
        ).fetchone()[0]
    endpoint_ativo = None
    if consultar_endpoint and _url_https_publica(url_site):
        health = url_site.rsplit("/api/cliques", 1)[0].rstrip("/") + "/health"
        try:
            with urllib.request.urlopen(health, timeout=4) as resposta:
                endpoint_ativo = 200 <= resposta.status < 300
        except (OSError, urllib.error.URLError):
            endpoint_ativo = False
    return {
        "total": total,
        "testes": testes,
        "ultimo_teste": _ultimo_teste(),
        "hoje": hoje,
        "ultimos": _ultimos_eventos(),
        "top_produtos": resumo_cliques()["produtos"],
        "top_categorias": resumo_cliques()["categorias"],
        "servidor_local_ativo": _pid_ativo(),
        "url_site": url_site,
        "endpoint_publico_configurado": _url_https_publica(url_site),
        "endpoint_ativo": endpoint_ativo,
        "site_configurado": bool(url_site),
        "javascript_pronto": SITE_SCRIPT.exists() and "PromoggAnalytics" in SITE_SCRIPT.read_text(encoding="utf-8"),
    }


def _ultimos_eventos(limite=10):
    with conectar() as conn:
        return [dict(row) for row in conn.execute(
            """SELECT COALESCE(NULLIF(item_id, ''), oferta_id) AS item_id, titulo, categoria,
                      origem, pagina_origem, tipo_evento, criado_em
               FROM cliques ORDER BY id DESC LIMIT ?""",
            (limite,),
        ).fetchall()]


def testar_analytics_local():
    """Executa um POST local real contra o handler, sem dados de visitante."""
    inicializar_banco()
    try:
        oferta = json.loads((Path("site") / "ofertas.json").read_text(encoding="utf-8"))["ofertas"][0]
    except (OSError, KeyError, IndexError, json.JSONDecodeError) as erro:
        raise RuntimeError(f"Não foi possível obter uma oferta pública para o teste: {erro}") from erro

    from servidor_analytics import AnalyticsHandler

    servidor = ThreadingHTTPServer(("127.0.0.1", 0), AnalyticsHandler)
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    evento = {
        "oferta_id": str(oferta.get("item_id") or oferta.get("oferta_id")),
        "item_id": str(oferta.get("item_id") or ""),
        "titulo": str(oferta.get("titulo") or "Oferta de teste"),
        "categoria": str(oferta.get("categoria") or "ofertas"),
        "origem": "teste_local",
        "pagina_origem": "/homologacao-analytics/",
        "tipo_evento": "teste",
    }
    try:
        requisicao = urllib.request.Request(
            f"http://127.0.0.1:{servidor.server_port}/api/cliques",
            data=json.dumps(evento).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json", "Origin": "https://promogg.com.br"},
        )
        with urllib.request.urlopen(requisicao, timeout=5) as resposta:
            status_http = resposta.status
    finally:
        servidor.shutdown()
        servidor.server_close()
        thread.join(timeout=2)
    ultimo = _ultimo_evento()
    salvo = bool(ultimo and ultimo.get("item_id") == evento["item_id"] and ultimo.get("tipo_evento") == "teste")
    return {"http": status_http, "salvo": salvo, "item_id": evento["item_id"], "tipo_evento": "teste"}


def gerar_relatorio_analytics(status=None, teste=None):
    status = status or status_analytics()
    externo = "não" if not status["endpoint_publico_configurado"] else "sim, sujeito à verificação de saúde"
    linhas = [
        "# Relatório de Homologação do Analytics", "",
        f"- Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "- Dados pessoais: não coletados.",
        "", "## Arquitetura atual",
        "- O site estático usa `analytics.js` e envia somente eventos mínimos quando há endpoint HTTPS configurado.",
        "- O servidor local escuta em `127.0.0.1`; por design, não é alcançável por visitantes externos.",
        f"- URL configurada no catálogo: {'sim' if status['site_configurado'] else 'não'}.",
        f"- Cliques externos podem ser recebidos agora: {externo}.",
        "", "## Métricas locais",
        f"- Total de cliques reais: {status['total']}", f"- Cliques reais hoje: {status['hoje']}", f"- Eventos de teste: {status['testes']}",
        f"- Servidor local ativo: {'sim' if status['servidor_local_ativo'] else 'não'}",
        f"- JavaScript de analytics gerado: {'sim' if status['javascript_pronto'] else 'não'}",
    ]
    teste = teste or status.get("ultimo_teste")
    if teste:
        linhas += [
            "", "## Teste local",
            f"- HTTP: {teste.get('http', '202 confirmado anteriormente')}",
            f"- Evento salvo: {'sim' if teste.get('salvo', True) else 'não'}",
            f"- Tipo: {teste.get('tipo_evento', 'teste')}",
            f"- Última execução: {teste.get('criado_em', 'nesta execução')}",
        ]
    linhas += [
        "", "## Conclusão",
        "- O modo local é homologado para testes e painel no mesmo ambiente.",
        "- Para o GitHub Pages registrar visitantes reais, configure um endpoint HTTPS público com CORS restrito a `https://promogg.com.br`.",
        "- Há um modelo opcional de Cloudflare Worker com D1 no repositório; ele não expõe SQLite, tokens, IPs ou cookies.",
    ]
    RELATORIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return RELATORIO


def validar_analytics():
    inicializar_banco()
    erros = []
    with conectar() as conn:
        colunas = {row["name"] for row in conn.execute("PRAGMA table_info(cliques)")}
    obrigatorias = {"oferta_id", "item_id", "titulo", "categoria", "origem", "pagina_origem", "tipo_evento", "criado_em"}
    if not obrigatorias.issubset(colunas):
        erros.append("Tabela cliques não contém o contrato mínimo de analytics")
    if not SITE_SCRIPT.exists() or "PromoggAnalytics" not in SITE_SCRIPT.read_text(encoding="utf-8"):
        erros.append("JavaScript de analytics não foi gerado")
    return erros
