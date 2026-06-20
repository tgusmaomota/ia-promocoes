import json
import hashlib
import os
import re
import shutil
import struct
import unicodedata
import zlib
from datetime import datetime
from html import escape
from pathlib import Path
from urllib.parse import urlparse

from banco import conectar, inicializar_banco, registrar_evento_sistema, registrar_log
from estado_sistema import MANUTENCAO, OFFLINE, obter_estado_sistema
from gerador_link_mercadolivre import link_afiliado_valido


SITE_DIR = Path("site")
INDEX_PATH = SITE_DIR / "index.html"
STYLE_PATH = SITE_DIR / "style.css"
SCRIPT_PATH = SITE_DIR / "app.js"
FAVICON_PATH = SITE_DIR / "favicon.svg"
FAVICON_ICO_PATH = SITE_DIR / "favicon.ico"
LOGO_SVG_PATH = SITE_DIR / "logo.svg"
LOGO_PNG_PATH = SITE_DIR / "logo.png"
OFERTAS_PATH = SITE_DIR / "ofertas.json"
ASSISTENTE_DADOS_PATH = SITE_DIR / "assistente_dados.json"
ASSISTENTE_DIR = SITE_DIR / "assistente"
PRODUTOS_DIR = SITE_DIR / "produto"
CATEGORIAS_DIR = SITE_DIR / "categoria"
SITEMAP_PATH = SITE_DIR / "sitemap.xml"
ROBOTS_PATH = SITE_DIR / "robots.txt"
NOT_FOUND_PATH = SITE_DIR / "404.html"
OG_IMAGE_PATH = SITE_DIR / "og-promogg.svg"
SOBRE_DIR = SITE_DIR / "sobre"
SEGURANCA_DIR = SITE_DIR / "seguranca"
OAUTH_CALLBACK_DIR = SITE_DIR / "oauth" / "callback"
BASE_URL = "https://promogg.com.br"
ITEM_ID_RE = re.compile(r"^[A-Za-z0-9_-]{4,80}$")


def formatar_preco(valor):
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "R$ 0,00"


def preco_publico_valido(valor):
    try:
        preco = float(valor)
    except (TypeError, ValueError):
        return None
    return preco if preco > 0 else None


def imagem_publica_valida(url):
    url = str(url or "").strip()
    partes = urlparse(url)
    return url if partes.scheme in {"http", "https"} and partes.netloc else ""


def analytics_public_url():
    url = imagem_publica_valida(os.getenv("PROMOGG_ANALYTICS_URL", ""))
    partes = urlparse(url)
    if partes.scheme != "https" or partes.hostname in {"localhost", "127.0.0.1", "::1"}:
        return ""
    return url


def item_id_publico(valor):
    item_id = str(valor or "").strip().upper()
    return item_id if ITEM_ID_RE.fullmatch(item_id) else ""


def slug_publico(texto, limite=90):
    texto = unicodedata.normalize("NFKD", str(texto or "").lower())
    texto = "".join(caractere for caractere in texto if not unicodedata.combining(caractere))
    texto = re.sub(r"[^a-z0-9]+", "-", texto)
    return texto.strip("-")[:limite].strip("-") or "oferta"


def url_produto(item_id, titulo=""):
    item_id = item_id_publico(item_id)
    if not item_id:
        return ""
    slug = slug_publico(titulo) if str(titulo or "").strip() else item_id.lower()
    return f"produto/{item_id}/{slug or item_id.lower()}/"


def url_categoria(categoria):
    return f"categoria/{slug_publico(categoria)}/"


def listar_ofertas(deduplicar=True):
    inicializar_banco()
    with conectar() as conn:
        rows = conn.execute(
            """
            SELECT produtos.id AS produto_id, produtos.item_id, postagens.titulo,
                   COALESCE(NULLIF(produtos.preco_atual, 0), postagens.preco) AS preco,
                   postagens.link_afiliado, postagens.plataforma,
                   COALESCE(NULLIF(produtos.categoria_nome, ''), NULLIF(produtos.categoria, ''), postagens.categoria, 'ofertas') AS categoria,
                   postagens.data_publicacao, produtos.imagem AS imagem_url,
                   produtos.menor_preco, produtos.maior_preco, produtos.preco_medio, produtos.variacao_preco,
                   produtos.destaque_menor_preco, produtos.ultima_verificacao
                   , produtos.preco_original, produtos.desconto_percentual, produtos.economia_valor,
                   produtos.categoria_caminho, produtos.selo_mais_vendido, produtos.selo_loja_oficial
            FROM postagens
            JOIN produtos ON produtos.id = postagens.produto_id
            WHERE postagens.plataforma = 'mercado_livre'
              AND postagens.status IN ('aprovado_auto', 'aprovado_manual', 'publicado')
              AND produtos.status NOT IN ('indisponivel', 'erro')
            ORDER BY CASE postagens.status
                WHEN 'aprovado_manual' THEN 0
                WHEN 'aprovado_auto' THEN 1
                ELSE 2
            END,
                     postagens.data_criacao DESC
            """
        ).fetchall()

    ofertas = []
    links_usados = set()
    for row in rows:
        oferta = dict(row)
        link = str(oferta.get("link_afiliado") or "").strip()
        preco = preco_publico_valido(oferta.get("preco"))
        titulo = str(oferta.get("titulo") or "").strip()
        item_id = item_id_publico(oferta.get("item_id"))
        if not link_afiliado_valido(link) or link in links_usados or preco is None or not titulo or not item_id:
            continue

        links_usados.add(link)
        categoria = str(oferta.get("categoria") or "ofertas").strip() or "ofertas"
        try:
            variacao_preco = float(oferta.get("variacao_preco") or 0)
        except (TypeError, ValueError):
            variacao_preco = 0
        ofertas.append({
            "_produto_id": oferta["produto_id"],
            "_item_id": item_id,
            "item_id": item_id,
            "oferta_id": hashlib.sha256(link.encode("utf-8")).hexdigest()[:20],
            "titulo": titulo,
            "preco": preco,
            "preco_formatado": formatar_preco(preco),
            "preco_original": preco_publico_valido(oferta.get("preco_original")),
            "desconto_percentual": preco_publico_valido(oferta.get("desconto_percentual")),
            "economia_valor": preco_publico_valido(oferta.get("economia_valor")),
            "menor_preco": preco_publico_valido(oferta.get("menor_preco")) or preco,
            "menor_preco_formatado": formatar_preco(preco_publico_valido(oferta.get("menor_preco")) or preco),
            "variacao_preco": variacao_preco,
            "destaque_menor_preco": bool(oferta.get("destaque_menor_preco")),
            "categoria": categoria,
            "categoria_caminho": str(oferta.get("categoria_caminho") or categoria).strip() or categoria,
            "selo_mais_vendido": bool(oferta.get("selo_mais_vendido")),
            "selo_loja_oficial": bool(oferta.get("selo_loja_oficial")),
            "link": link,
            "imagem_url": imagem_publica_valida(oferta.get("imagem_url")),
            "plataforma": "Mercado Livre",
            "produto_url": url_produto(item_id, titulo),
            "data_publicacao": oferta.get("data_publicacao"),
            "ultima_verificacao": oferta.get("ultima_verificacao"),
            "maior_preco": preco_publico_valido(oferta.get("maior_preco")),
            "preco_medio": preco_publico_valido(oferta.get("preco_medio")),
        })
    if not deduplicar:
        return ofertas
    # A identidade pública estável é o item_id. A primeira oferta respeita a
    # ordenação da consulta (status e atualização mais recente) e vence o conflito.
    unicas = []
    item_ids = set()
    for oferta in ofertas:
        item_id = oferta["_item_id"]
        if item_id in item_ids:
            continue
        item_ids.add(item_id)
        unicas.append(oferta)
    return unicas


def oferta_publica(oferta):
    return {chave: valor for chave, valor in oferta.items() if not chave.startswith("_")}


def escrever_dados_assistente(ofertas):
    """Índice público mínimo para respostas locais, sem dados operacionais."""
    dados = []
    for oferta in ofertas:
        dados.append({
            "item_id": oferta["_item_id"], "titulo": oferta["titulo"], "preco_atual": oferta["preco"],
            "menor_preco": oferta["menor_preco"], "maior_preco": oferta.get("maior_preco"),
            "preco_medio": oferta.get("preco_medio"), "categoria": oferta["categoria"],
            "categoria_caminho": oferta.get("categoria_caminho") or oferta["categoria"],
            "desconto_percentual": oferta.get("desconto_percentual"), "economia_valor": oferta.get("economia_valor"),
            "produto_url": oferta["produto_url"], "imagem_url": oferta.get("imagem_url", ""),
            "ultima_atualizacao": oferta.get("ultima_verificacao") or oferta.get("data_publicacao"),
        })
    ASSISTENTE_DADOS_PATH.write_text(json.dumps({"gerado_em": datetime.now().isoformat(timespec="seconds"), "produtos": dados}, ensure_ascii=False, indent=2), encoding="utf-8")


def escrever_css():
    STYLE_PATH.write_text("""@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Outfit:wght@600;700&display=swap');

:root {
    --ink: #102a36;
    --muted: #5c717d;
    --line: #d9e4e8;
    --surface: #ffffff;
    --canvas: #f4f8f7;
    --teal: #006d77;
    --teal-dark: #00525a;
    --sun: #ffbd30;
    --sun-dark: #e9a70b;
    --coral: #e95f4d;
    --shadow: 0 8px 24px rgba(16, 42, 54, 0.08);
}

* { box-sizing: border-box; }

html { scroll-behavior: smooth; }

body {
    margin: 0;
    color: var(--ink);
    background: var(--canvas);
    font-family: "DM Sans", Arial, sans-serif;
    line-height: 1.5;
}

button, input, select { font: inherit; }

a { color: inherit; }

.skip-link {
    position: absolute;
    left: 16px;
    top: -48px;
    z-index: 10;
    padding: 10px 14px;
    color: var(--ink);
    background: var(--sun);
    border-radius: 6px;
}

.skip-link:focus { top: 16px; }

.site-header {
    position: sticky;
    top: 0;
    z-index: 5;
    border-bottom: 1px solid rgba(16, 42, 54, 0.1);
    background: rgba(255, 255, 255, 0.96);
}

.header-inner, .container, .footer-inner {
    width: min(1160px, calc(100% - 40px));
    margin: 0 auto;
}

.header-inner {
    min-height: 68px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
}

.brand {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    color: var(--ink);
    font-family: Outfit, Arial, sans-serif;
    font-size: 1.35rem;
    font-weight: 700;
    text-decoration: none;
}

.brand-mark {
    width: 30px;
    height: 30px;
    display: grid;
    place-items: center;
    color: var(--ink);
    background: var(--sun);
    border-radius: 7px;
    font-size: 0.88rem;
    letter-spacing: 0;
}
.brand-logo { width: 148px; height: auto; display: block; }

.header-actions { display: flex; align-items: center; gap: 12px; }
.system-banner { padding: 12px 20px; color: #513a00; background: #fff3c9; border-bottom: 1px solid #e9c857; text-align: center; font-weight: 600; }
.offline-page { min-height: 70vh; display: grid; place-items: center; text-align: center; }
.offline-page .detail-notice { max-width: 620px; margin: 14px auto; }

.button, .icon-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    min-height: 42px;
    border: 0;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 700;
    text-decoration: none;
    transition: background 160ms ease, transform 160ms ease, box-shadow 160ms ease;
}

.button:hover, .icon-button:hover { transform: translateY(-1px); }
.button:focus-visible, .icon-button:focus-visible, input:focus-visible, select:focus-visible, a:focus-visible { outline: 3px solid rgba(0, 109, 119, 0.3); outline-offset: 2px; }

.button-primary { padding: 10px 16px; color: var(--ink); background: var(--sun); box-shadow: 0 3px 0 var(--sun-dark); }
.button-primary:hover { background: #ffc94c; }
.button-secondary { padding: 10px 16px; color: #fff; background: var(--teal); }
.button-secondary:hover { background: var(--teal-dark); }
.button-telegram { padding: 10px 16px; color: var(--ink); background: #fff; }
.button[hidden] { display: none; }

.hero { padding: 58px 0 46px; background: var(--teal); color: #fff; }
.hero-content { max-width: 720px; }
.eyebrow { margin: 0 0 12px; color: #ffe19a; font-size: 0.82rem; font-weight: 700; letter-spacing: 0; text-transform: uppercase; }

h1, h2, h3, p { margin-top: 0; }
h1, h2, h3 { font-family: Outfit, Arial, sans-serif; letter-spacing: 0; }
h1 { max-width: 760px; margin-bottom: 14px; font-size: clamp(2rem, 5vw, 3.6rem); line-height: 1.05; }
.hero-copy { max-width: 620px; margin-bottom: 26px; color: #d4f1ed; font-size: 1.08rem; }
.hero-actions { display: flex; flex-wrap: wrap; gap: 12px; }

.content { padding: 34px 0 56px; }
.section-heading { display: flex; align-items: end; justify-content: space-between; gap: 20px; margin-bottom: 18px; }
.section-heading h2 { margin: 0; font-size: 1.55rem; }
.offer-count { margin: 0; color: var(--muted); font-size: 0.92rem; }

.filters {
    display: grid;
    grid-template-columns: minmax(220px, 2fr) repeat(2, minmax(150px, 1fr));
    gap: 12px;
    padding: 16px;
    margin-bottom: 24px;
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 8px;
    box-shadow: 0 3px 10px rgba(16, 42, 54, 0.04);
}

.field { display: grid; gap: 6px; }
.field label { color: var(--muted); font-size: 0.78rem; font-weight: 700; }
.field input, .field select {
    width: 100%;
    min-height: 42px;
    padding: 9px 11px;
    color: var(--ink);
    background: #fff;
    border: 1px solid #b9c9cf;
    border-radius: 6px;
}

.offer-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }

.offer-card {
    min-width: 0;
    min-height: 360px;
    overflow: hidden;
    padding: 0;
    display: flex;
    flex-direction: column;
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 8px;
    box-shadow: var(--shadow);
}

.offer-media { width: 100%; aspect-ratio: 16 / 10; display: grid; place-items: center; overflow: hidden; background: #e7f4f1; }
.offer-media img { width: 100%; height: 100%; display: block; object-fit: contain; background: #fff; }
.image-fallback { color: var(--teal-dark); font-family: Outfit, Arial, sans-serif; font-size: 1rem; font-weight: 700; }
.card-topline { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin: 16px 18px 13px; }
.marketplace { display: inline-flex; align-items: center; gap: 6px; color: var(--muted); font-size: 0.78rem; font-weight: 700; }
.marketplace::before { width: 18px; height: 18px; display: grid; place-items: center; content: "ML"; color: var(--ink); background: var(--sun); border-radius: 50%; font-size: 0.58rem; }
.tag { max-width: 58%; overflow: hidden; padding: 3px 7px; color: var(--teal-dark); background: #dff3f0; border-radius: 4px; font-size: 0.72rem; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }
.offer-card h3 { margin: 0 18px 12px; font-size: 1.05rem; line-height: 1.3; }
.updated { margin: 0 18px 15px; color: var(--muted); font-size: 0.78rem; }
.price-label { margin: auto 18px 2px; color: var(--muted); font-size: 0.76rem; font-weight: 700; text-transform: uppercase; }
.price { margin: 0 18px 15px; color: var(--teal-dark); font-family: Outfit, Arial, sans-serif; font-size: 1.65rem; font-weight: 700; line-height: 1.1; }
.price-history { display: grid; grid-template-columns: 1fr auto; gap: 6px 10px; margin: -4px 18px 15px; color: var(--muted); font-size: 0.76rem; }
.price-history strong { color: var(--ink); font-size: 0.82rem; }
.variation-down { color: #087443; font-weight: 700; }
.variation-up { color: #b53d31; font-weight: 700; }
.variation-stable { color: var(--muted); font-weight: 700; }
.record-badge { display: inline-flex; width: fit-content; margin: -3px 18px 12px; padding: 4px 7px; color: #075a43; background: #dff3e8; border-radius: 4px; font-size: 0.72rem; font-weight: 700; }
.offer-card .button { width: calc(100% - 36px); margin: 0 18px 18px; }
.details-link { margin: -8px 18px 16px; color: var(--teal-dark); font-size: 0.86rem; font-weight: 700; text-align: center; }

.pagination { display: flex; align-items: center; justify-content: center; gap: 14px; min-height: 52px; margin-top: 28px; }
.pagination button:disabled { cursor: not-allowed; opacity: 0.45; transform: none; }
.page-indicator { min-width: 112px; text-align: center; color: var(--muted); font-size: 0.9rem; font-weight: 700; }

.detail-page { padding: 34px 0 56px; }
.breadcrumb { display: inline-block; margin-bottom: 22px; color: var(--teal-dark); font-weight: 700; text-decoration: none; }
.product-detail { display: grid; grid-template-columns: minmax(0, 1fr) minmax(320px, 0.95fr); gap: 34px; align-items: start; }
.product-image { aspect-ratio: 1 / 1; display: grid; place-items: center; overflow: hidden; background: #e7f4f1; border-radius: 8px; }
.product-image img { width: 100%; height: 100%; object-fit: contain; background: #fff; }
.product-info h1 { margin-bottom: 14px; font-size: 2rem; line-height: 1.12; }
.product-category { display: inline-flex; margin-bottom: 16px; padding: 4px 8px; color: var(--teal-dark); background: #dff3f0; border-radius: 4px; font-size: 0.8rem; font-weight: 700; }
.product-price { margin-bottom: 18px; color: var(--teal-dark); font-family: Outfit, Arial, sans-serif; font-size: 2.25rem; font-weight: 700; }
.detail-updated { color: var(--muted); font-size: 0.85rem; }
.price-summary { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin: 22px 0; }
.price-summary div { padding: 12px; background: #fff; border: 1px solid var(--line); border-radius: 6px; }
.price-summary span { display: block; color: var(--muted); font-size: 0.74rem; font-weight: 700; }
.price-summary strong { display: block; margin-top: 4px; font-size: 0.96rem; }
.detail-notice { color: var(--muted); font-size: 0.84rem; }
.history-section { margin-top: 42px; }
.history-section h2 { margin-bottom: 12px; font-size: 1.35rem; }
.history-table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid var(--line); }
.history-table th, .history-table td { padding: 11px 12px; border-bottom: 1px solid var(--line); text-align: left; }
.history-table th { color: var(--muted); font-size: 0.78rem; }
.history-table tr:last-child td { border-bottom: 0; }

.feedback {
    grid-column: 1 / -1;
    padding: 34px 24px;
    text-align: center;
    background: var(--surface);
    border: 1px dashed #a9bec5;
    border-radius: 8px;
}
.feedback h3 { margin-bottom: 6px; font-size: 1.1rem; }
.feedback p { max-width: 480px; margin: 0 auto; color: var(--muted); }
.trust-section { padding-top: 12px; padding-bottom: 34px; }
.trust-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 20px; }
.trust-grid h2 { font-size: 1.05rem; margin-bottom: 6px; }.trust-grid p { color: var(--muted); margin: 0; }
.assistant { max-width: 780px; }.assistant form { display: grid; grid-template-columns: 1fr auto; gap: 10px; align-items: end; margin: 24px 0 12px; }.assistant label { grid-column: 1 / -1; font-weight: 700; }.assistant input { min-height: 48px; padding: 10px 12px; border: 1px solid var(--line); border-radius: 6px; }.suggestions { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 24px; }.suggestions button { padding: 8px 10px; border: 1px solid var(--line); background: #fff; border-radius: 5px; color: var(--teal-dark); font-weight: 700; }

.disclosure { padding: 28px 0; background: #e7f4f1; }
.disclosure-inner { display: grid; grid-template-columns: auto 1fr; gap: 14px; align-items: start; }
.disclosure-badge { width: 42px; height: 42px; display: grid; place-items: center; color: var(--teal-dark); background: #fff; border-radius: 8px; font-weight: 700; }
.disclosure h2 { margin-bottom: 4px; font-size: 1.1rem; }
.disclosure p { margin-bottom: 0; color: var(--muted); }

.site-footer { padding: 30px 0; color: #cfdfdc; background: var(--ink); }
.footer-inner { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; }
.footer-brand { margin-bottom: 5px; color: #fff; font-family: Outfit, Arial, sans-serif; font-size: 1.1rem; font-weight: 700; }
.footer-note { max-width: 680px; margin: 0; font-size: 0.85rem; }
.footer-link { color: #fff; font-size: 0.9rem; font-weight: 700; }
.footer-links { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 10px 18px; max-width: 420px; }
.footer-updated { margin-top: 10px; font-size: 0.78rem; color: #9fb9b5; }

@media (max-width: 820px) {
    .filters { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .field:first-child { grid-column: 1 / -1; }
    .offer-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .product-detail { grid-template-columns: 1fr; }
}

@media (max-width: 560px) {
    .header-inner, .container, .footer-inner { width: min(100% - 28px, 1160px); }
    .header-inner { min-height: 62px; }
    .brand { font-size: 1.2rem; }
    .brand-logo { width: 132px; }
    .header-actions .button { width: 42px; min-width: 42px; padding: 0; font-size: 0; }
    .header-actions .button::after { content: "↻"; font-size: 1.25rem; }
    .hero { padding: 42px 0 36px; }
    h1 { font-size: 2.25rem; }
    .hero-actions .button { width: 100%; }
    .section-heading { display: block; }
    .offer-count { margin-top: 4px; }
    .filters, .offer-grid { grid-template-columns: 1fr; }
    .field:first-child { grid-column: auto; }
    .offer-card { min-height: 230px; }
    .price-summary { grid-template-columns: 1fr; }
    .trust-grid { grid-template-columns: 1fr; }.assistant form { grid-template-columns: 1fr; }.assistant form .button { width: 100%; }
    .footer-inner { display: block; }
    .footer-links { justify-content: flex-start; margin-top: 16px; }
}
""", encoding="utf-8")


def _escrever_javascript_legacy():
    SCRIPT_PATH.write_text(r"""const state = { ofertas: [], geradoEm: null };

const elements = {
    grid: document.querySelector("#offer-grid"),
    count: document.querySelector("#offer-count"),
    search: document.querySelector("#search"),
    category: document.querySelector("#category"),
    status: document.querySelector("#status"),
    sort: document.querySelector("#sort"),
    generatedAt: document.querySelector("#generated-at"),
    telegramLinks: document.querySelectorAll("[data-telegram-link]")
};

function normalizarData(valor) {
    if (!valor) return null;
    const data = new Date(String(valor).replace(" ", "T"));
    return Number.isNaN(data.getTime()) ? null : data;
}

function formatarData(valor) {
    const data = normalizarData(valor);
    return data ? new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(data) : "data indisponível";
}

function formatarPreco(valor, precoFormatado) {
    if (precoFormatado) return precoFormatado;
    return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(valor) || 0);
}

function textoSeguro(valor) {
    return String(valor || "").trim();
}

function preencherSelect(select, valores, textoPadrao) {
    select.replaceChildren(new Option(textoPadrao, ""));
    valores.sort((a, b) => a.localeCompare(b, "pt-BR")).forEach((valor) => {
        select.add(new Option(valor, valor));
    });
}

function ofertasFiltradas() {
    const busca = elements.search.value.trim().toLocaleLowerCase("pt-BR");
    const categoria = elements.category.value;
    const status = elements.status.value;
    const ofertas = state.ofertas.filter((oferta) => {
        const titulo = textoSeguro(oferta.titulo).toLocaleLowerCase("pt-BR");
        return (!busca || titulo.includes(busca))
            && (!categoria || oferta.categoria === categoria)
            && (!status || oferta.status === status);
    });

    return ofertas.sort((a, b) => {
        if (elements.sort.value === "menor-preco") return Number(a.preco) - Number(b.preco);
        if (elements.sort.value === "maior-preco") return Number(b.preco) - Number(a.preco);
        return (normalizarData(b.data_publicacao || b.data_criacao)?.getTime() || 0)
            - (normalizarData(a.data_publicacao || a.data_criacao)?.getTime() || 0);
    });
}

function criarCard(oferta) {
    const card = document.createElement("article");
    card.className = "offer-card";

    const topo = document.createElement("div");
    topo.className = "card-topline";
    const plataforma = document.createElement("span");
    plataforma.className = "marketplace";
    plataforma.textContent = textoSeguro(oferta.plataforma) || "Mercado Livre";
    const categoria = document.createElement("span");
    categoria.className = "tag";
    const nomeCategoria = textoSeguro(oferta.categoria) || "ofertas";
    const nomeStatus = textoSeguro(oferta.status) || "disponível";
    categoria.title = `${nomeCategoria} · ${nomeStatus}`;
    categoria.textContent = `${nomeCategoria} · ${nomeStatus}`;
    topo.append(plataforma, categoria);

    const titulo = document.createElement("h3");
    titulo.textContent = textoSeguro(oferta.titulo) || "Oferta sem título";
    const atualizado = document.createElement("p");
    atualizado.className = "updated";
    atualizado.textContent = `Atualizada em ${formatarData(oferta.ultima_verificacao || oferta.data_publicacao || oferta.data_criacao)}`;
    const label = document.createElement("p");
    label.className = "price-label";
    label.textContent = "Preço atual";
    const preco = document.createElement("p");
    preco.className = "price";
    preco.textContent = formatarPreco(oferta.preco, oferta.preco_formatado);
    const promocao = document.createElement("p");
    promocao.className = "updated";
    const desconto = Number(oferta.desconto_percentual) || 0;
    const original = Number(oferta.preco_original) || 0;
    promocao.textContent = desconto > 0 ? (desconto.toFixed(0) + "% OFF" + (original > 0 ? " · De " + formatarPreco(original) : "")) : "";
    promocao.hidden = !promocao.textContent;
    const historico = document.createElement("div");
    historico.className = "price-history";
    const menorLabel = document.createElement("span");
    menorLabel.textContent = "Menor preço já visto";
    const menorPreco = document.createElement("strong");
    menorPreco.textContent = formatarPreco(oferta.menor_preco, oferta.menor_preco_formatado);
    const variacao = document.createElement("span");
    const valorVariacao = Number(oferta.variacao_preco) || 0;
    variacao.className = valorVariacao < 0 ? "variation-down" : valorVariacao > 0 ? "variation-up" : "variation-stable";
    variacao.textContent = valorVariacao < 0
        ? `Caiu ${formatarPreco(Math.abs(valorVariacao))}`
        : valorVariacao > 0 ? `Subiu ${formatarPreco(valorVariacao)}` : "Sem variação";
    historico.append(menorLabel, menorPreco, variacao);
    const destaque = document.createElement("span");
    destaque.className = "record-badge";
    destaque.textContent = "Menor preço já visto";
    if (!oferta.destaque_menor_preco) destaque.hidden = true;
    const link = document.createElement("a");
    link.className = "button button-secondary";
    link.href = textoSeguro(oferta.link);
    link.target = "_blank";
    link.rel = "noopener sponsored";
    link.textContent = "Ver oferta";

    card.append(topo, titulo, atualizado, label, preco, promocao, historico, destaque, link);
    return card;
}

function exibirFeedback(titulo, mensagem) {
    const feedback = document.createElement("section");
    feedback.className = "feedback";
    const heading = document.createElement("h3");
    heading.textContent = titulo;
    const texto = document.createElement("p");
    texto.textContent = mensagem;
    feedback.append(heading, texto);
    elements.grid.replaceChildren(feedback);
}

function renderizar() {
    const ofertas = ofertasFiltradas();
    elements.count.textContent = `${ofertas.length} ${ofertas.length === 1 ? "oferta encontrada" : "ofertas encontradas"}`;
    if (!ofertas.length) {
        exibirFeedback("Nenhuma oferta encontrada", "Ajuste os filtros ou volte mais tarde para ver novas seleções.");
        return;
    }
    elements.grid.replaceChildren(...ofertas.map(criarCard));
}

function configurarTelegram() {
    const url = document.body.dataset.telegramUrl.trim();
    if (!/^https:\/\/t\.me\//.test(url)) return;
    elements.telegramLinks.forEach((link) => {
        link.href = url;
        link.hidden = false;
    });
}

async function carregarOfertas() {
    exibirFeedback("Carregando ofertas", "Buscando as ofertas selecionadas para você.");
    try {
        const resposta = await fetch("ofertas.json", { cache: "no-store" });
        if (!resposta.ok) throw new Error(`HTTP ${resposta.status}`);
        const dados = await resposta.json();
        state.ofertas = Array.isArray(dados.ofertas) ? dados.ofertas.filter((oferta) => /^https?:\/\//.test(textoSeguro(oferta.link))) : [];
        state.geradoEm = dados.gerado_em;
        preencherSelect(elements.category, [...new Set(state.ofertas.map((oferta) => textoSeguro(oferta.categoria)).filter(Boolean))], "Todas as categorias");
        preencherSelect(elements.status, [...new Set(state.ofertas.map((oferta) => textoSeguro(oferta.status)).filter(Boolean))], "Todos os status");
        elements.generatedAt.textContent = state.geradoEm ? `Lista atualizada em ${formatarData(state.geradoEm)}` : "Lista atualizada";
        renderizar();
    } catch (erro) {
        elements.count.textContent = "Ofertas indisponíveis";
        exibirFeedback("Não foi possível carregar as ofertas", "Atualize a página em alguns instantes. O catálogo pode estar sendo atualizado.");
    }
}

elements.search.addEventListener("input", renderizar);
[elements.category, elements.status, elements.sort].forEach((campo) => campo.addEventListener("change", renderizar));
document.querySelector("#refresh").addEventListener("click", () => window.location.reload());
configurarTelegram();
carregarOfertas();
""", encoding="utf-8")


def escrever_javascript():
    (SITE_DIR / "analytics.js").write_text(r"""(() => {
const endpoint = String(document.body?.dataset.analyticsUrl || "").trim();
const valido = valor => { try { return new URL(valor).protocol === "https:"; } catch (_) { return false; } };
function enviar(dados) {
  if (!valido(endpoint)) return;
  const evento = JSON.stringify({
    oferta_id: String(dados.item_id || "").trim(), item_id: String(dados.item_id || "").trim(),
    titulo: String(dados.titulo || "").trim(), categoria: String(dados.categoria || "ofertas").trim() || "ofertas",
    origem: "site_publico", pagina_origem: window.location.pathname || "/", tipo_evento: dados.tipo_evento || "ver_oferta"
  });
  const blob = new Blob([evento], { type: "application/json" });
  if (navigator.sendBeacon && navigator.sendBeacon(endpoint, blob)) return;
  fetch(endpoint, { method: "POST", body: evento, headers: { "Content-Type": "application/json" }, keepalive: true }).catch(() => {});
}
window.PromoggAnalytics = { enviar };
document.addEventListener("click", evento => {
  const alvo = evento.target.closest("[data-analytics-click]");
  if (!alvo) return;
  enviar({ item_id: alvo.dataset.itemId, titulo: alvo.dataset.titulo, categoria: alvo.dataset.categoria, tipo_evento: alvo.dataset.analyticsClick });
});
})();
""", encoding="utf-8")
    SCRIPT_PATH.write_text(r"""const POR_PAGINA = 20;
const state = { ofertas: [], geradoEm: null, pagina: 1 };

const elements = {
    grid: document.querySelector("#offer-grid"),
    count: document.querySelector("#offer-count"),
    search: document.querySelector("#search"),
    category: document.querySelector("#category"),
    sort: document.querySelector("#sort"),
    generatedAt: document.querySelector("#generated-at"),
    previous: document.querySelector("#previous-page"),
    next: document.querySelector("#next-page"),
    pageIndicator: document.querySelector("#page-indicator"),
    analyticsUrl: document.body.dataset.analyticsUrl.trim(),
    telegramLinks: document.querySelectorAll("[data-telegram-link]")
};

function normalizarData(valor) {
    if (!valor) return null;
    const data = new Date(String(valor).replace(" ", "T"));
    return Number.isNaN(data.getTime()) ? null : data;
}

function formatarData(valor) {
    const data = normalizarData(valor);
    return data ? new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(data) : "data indisponível";
}

function formatarPreco(valor, precoFormatado) {
    if (precoFormatado) return precoFormatado;
    return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(valor) || 0);
}

function textoSeguro(valor) {
    return String(valor || "").trim();
}

function imagemPublica(url) {
    try {
        const imagem = new URL(textoSeguro(url));
        return imagem.protocol === "https:" || imagem.protocol === "http:" ? imagem.href : "";
    } catch (_) {
        return "";
    }
}

function preencherSelect(select, valores, textoPadrao) {
    select.replaceChildren(new Option(textoPadrao, ""));
    valores.sort((a, b) => a.localeCompare(b, "pt-BR")).forEach((valor) => select.add(new Option(valor, valor)));
}

function ofertasFiltradas() {
    const busca = elements.search.value.trim().toLocaleLowerCase("pt-BR");
    const categoria = elements.category.value;
    const ofertas = state.ofertas.filter((oferta) => {
        const titulo = textoSeguro(oferta.titulo).toLocaleLowerCase("pt-BR");
        return (!busca || titulo.includes(busca)) && (!categoria || oferta.categoria === categoria);
    });
    return ofertas.sort((a, b) => {
        if (elements.sort.value === "menor-preco") return Number(a.preco) - Number(b.preco);
        if (elements.sort.value === "maior-preco") return Number(b.preco) - Number(a.preco);
        return (normalizarData(b.ultima_verificacao || b.data_publicacao)?.getTime() || 0)
            - (normalizarData(a.ultima_verificacao || a.data_publicacao)?.getTime() || 0);
    });
}

function criarMidia(oferta) {
    const midia = document.createElement("div");
    midia.className = "offer-media";
    const url = imagemPublica(oferta.imagem_url);
    if (!url) {
        const fallback = document.createElement("span");
        fallback.className = "image-fallback";
        fallback.textContent = "Promogg";
        midia.append(fallback);
        return midia;
    }
    const imagem = document.createElement("img");
    imagem.src = url;
    imagem.alt = textoSeguro(oferta.titulo) || "Produto em oferta";
    imagem.loading = "lazy";
    imagem.addEventListener("error", () => {
        imagem.remove();
        const fallback = document.createElement("span");
        fallback.className = "image-fallback";
        fallback.textContent = "Imagem indisponível";
        midia.append(fallback);
    }, { once: true });
    midia.append(imagem);
    return midia;
}

function registrarClique(oferta, tipoEvento) {
    if (!window.PromoggAnalytics) return;
    window.PromoggAnalytics.enviar({
        item_id: textoSeguro(oferta.item_id), titulo: textoSeguro(oferta.titulo),
        categoria: textoSeguro(oferta.categoria) || "ofertas", tipo_evento: tipoEvento || "ver_oferta"
    });
}

function criarCard(oferta) {
    const card = document.createElement("article");
    card.className = "offer-card";
    const topo = document.createElement("div");
    topo.className = "card-topline";
    const plataforma = document.createElement("span");
    plataforma.className = "marketplace";
    plataforma.textContent = textoSeguro(oferta.plataforma) || "Mercado Livre";
    const categoria = document.createElement("span");
    categoria.className = "tag";
    categoria.textContent = textoSeguro(oferta.categoria) || "ofertas";
    categoria.title = categoria.textContent;
    topo.append(plataforma, categoria);
    const sinais = document.createElement("p");
    sinais.className = "updated";
    const listaSinais = [];
    if (Number(oferta.desconto_percentual) > 0) listaSinais.push(`${Number(oferta.desconto_percentual).toFixed(0)}% OFF`);
    if (oferta.selo_mais_vendido) listaSinais.push("Mais vendido");
    if (oferta.selo_loja_oficial) listaSinais.push("Loja oficial");
    sinais.textContent = listaSinais.join(" · ");
    sinais.hidden = !sinais.textContent;

    const titulo = document.createElement("h3");
    titulo.textContent = textoSeguro(oferta.titulo) || "Oferta sem título";
    const atualizado = document.createElement("p");
    atualizado.className = "updated";
    atualizado.textContent = `Atualizada em ${formatarData(oferta.ultima_verificacao || oferta.data_publicacao)}`;
    const label = document.createElement("p");
    label.className = "price-label";
    label.textContent = "Preço atual";
    const preco = document.createElement("p");
    preco.className = "price";
    preco.textContent = formatarPreco(oferta.preco, oferta.preco_formatado);
    const historico = document.createElement("div");
    historico.className = "price-history";
    const menorLabel = document.createElement("span");
    menorLabel.textContent = "Menor preço já visto";
    const menorPreco = document.createElement("strong");
    menorPreco.textContent = formatarPreco(oferta.menor_preco, oferta.menor_preco_formatado);
    const variacao = document.createElement("span");
    const valorVariacao = Number(oferta.variacao_preco) || 0;
    variacao.className = valorVariacao < 0 ? "variation-down" : valorVariacao > 0 ? "variation-up" : "variation-stable";
    variacao.textContent = valorVariacao < 0 ? `Caiu ${formatarPreco(Math.abs(valorVariacao))}` : valorVariacao > 0 ? `Subiu ${formatarPreco(valorVariacao)}` : "Sem variação";
    historico.append(menorLabel, menorPreco, variacao);
    const destaque = document.createElement("span");
    destaque.className = "record-badge";
    destaque.textContent = "Menor preço já visto";
    destaque.hidden = !oferta.destaque_menor_preco;
    const link = document.createElement("a");
    link.className = "button button-secondary";
    link.href = textoSeguro(oferta.link);
    link.target = "_blank";
    link.rel = "noopener sponsored";
    link.textContent = "Ver oferta";
    link.addEventListener("click", () => registrarClique(oferta, "ver_oferta"));
    const detalhes = document.createElement("a");
    detalhes.className = "details-link";
    detalhes.href = textoSeguro(oferta.produto_url);
    detalhes.textContent = "Ver detalhes";
    detalhes.addEventListener("click", () => registrarClique(oferta, "card_oferta"));
    card.append(criarMidia(oferta), topo, titulo, sinais, atualizado, label, preco, historico, destaque, link, detalhes);
    return card;
}

function exibirFeedback(titulo, mensagem) {
    const feedback = document.createElement("section");
    feedback.className = "feedback";
    const heading = document.createElement("h3");
    heading.textContent = titulo;
    const texto = document.createElement("p");
    texto.textContent = mensagem;
    feedback.append(heading, texto);
    elements.grid.replaceChildren(feedback);
}

function renderizar() {
    const ofertas = ofertasFiltradas();
    const totalPaginas = Math.max(1, Math.ceil(ofertas.length / POR_PAGINA));
    state.pagina = Math.min(Math.max(state.pagina, 1), totalPaginas);
    const inicio = (state.pagina - 1) * POR_PAGINA;
    const pagina = ofertas.slice(inicio, inicio + POR_PAGINA);
    elements.count.textContent = `${ofertas.length} ${ofertas.length === 1 ? "oferta encontrada" : "ofertas encontradas"}`;
    elements.pageIndicator.textContent = `Página ${state.pagina} de ${totalPaginas}`;
    elements.previous.disabled = state.pagina === 1;
    elements.next.disabled = state.pagina === totalPaginas;
    if (!ofertas.length) {
        exibirFeedback("Nenhuma oferta encontrada", "Ajuste os filtros ou volte mais tarde para ver novas seleções.");
        return;
    }
    elements.grid.replaceChildren(...pagina.map(criarCard));
}

function configurarTelegram() {
    const url = document.body.dataset.telegramUrl.trim();
    if (!/^https:\/\/t\.me\//.test(url)) return;
    elements.telegramLinks.forEach((link) => { link.href = url; link.hidden = false; });
}

async function carregarOfertas() {
    exibirFeedback("Carregando ofertas", "Buscando as ofertas selecionadas para você.");
    try {
        const resposta = await fetch("ofertas.json", { cache: "no-store" });
        if (!resposta.ok) throw new Error(`HTTP ${resposta.status}`);
        const dados = await resposta.json();
        state.ofertas = Array.isArray(dados.ofertas) ? dados.ofertas.filter((oferta) => /^https?:\/\//.test(textoSeguro(oferta.link))) : [];
        state.geradoEm = dados.gerado_em;
        preencherSelect(elements.category, [...new Set(state.ofertas.map((oferta) => textoSeguro(oferta.categoria)).filter(Boolean))], "Todas as categorias");
        elements.generatedAt.textContent = state.geradoEm ? `Lista atualizada em ${formatarData(state.geradoEm)}` : "Lista atualizada";
        renderizar();
    } catch (_) {
        elements.count.textContent = "Ofertas indisponíveis";
        elements.pageIndicator.textContent = "";
        elements.previous.disabled = true;
        elements.next.disabled = true;
        exibirFeedback("Não foi possível carregar as ofertas", "Atualize a página em alguns instantes. O catálogo pode estar sendo atualizado.");
    }
}

function filtrarDaPrimeiraPagina() { state.pagina = 1; renderizar(); }
elements.search.addEventListener("input", filtrarDaPrimeiraPagina);
[elements.category, elements.sort].forEach((campo) => campo.addEventListener("change", filtrarDaPrimeiraPagina));
elements.previous.addEventListener("click", () => { state.pagina -= 1; renderizar(); });
elements.next.addEventListener("click", () => { state.pagina += 1; renderizar(); });
document.querySelector("#refresh").addEventListener("click", () => window.location.reload());
configurarTelegram();
carregarOfertas();
""", encoding="utf-8")


def escrever_favicon():
    FAVICON_PATH.write_text("""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#006d77"/><path fill="#ffbd30" d="M14 17h36v24H14z"/><path fill="#102a36" d="M20 23h24v5H20zm0 9h17v5H20zm0 9h12v5H20z"/></svg>""", encoding="utf-8")


def _png_rgb(largura, altura):
    """PNG leve da marca, gerado sem dependências de imagem externas."""
    linhas = []
    for y in range(altura):
        linha = bytearray([0])
        for x in range(largura):
            cor = (0, 109, 119) if x < 112 else (16, 42, 54)
            if 20 <= x < 92 and 22 <= y < 94:
                cor = (255, 189, 48)
            linha.extend(cor)
        linhas.append(bytes(linha))
    def bloco(nome, dados):
        return struct.pack(">I", len(dados)) + nome + dados + struct.pack(">I", zlib.crc32(nome + dados) & 0xffffffff)
    return b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", struct.pack(">IIBBBBB", largura, altura, 8, 2, 0, 0, 0)) + bloco(b"IDAT", zlib.compress(b"".join(linhas), 9)) + bloco(b"IEND", b"")


def _favicon_ico():
    tamanho = 16
    pixels = bytearray()
    for y in range(tamanho - 1, -1, -1):
        for x in range(tamanho):
            azul, verde, vermelho, alfa = (119, 109, 0, 255) if 4 <= x < 13 and 4 <= y < 13 else (119, 109, 0, 255)
            if 6 <= x < 11 and 6 <= y < 11:
                azul, verde, vermelho = (48, 189, 255)
            pixels.extend((azul, verde, vermelho, alfa))
    cabecalho = struct.pack("<HHH", 0, 1, 1)
    entrada = struct.pack("<BBBBHHII", tamanho, tamanho, 0, 0, 1, 32, 40 + len(pixels) + 64, 22)
    bmp = struct.pack("<IIIHHIIIIII", 40, tamanho, tamanho * 2, 1, 32, 0, len(pixels), 0, 0, 0, 0)
    return cabecalho + entrada + bmp + pixels + (b"\x00" * 64)


def escrever_identidade():
    LOGO_SVG_PATH.write_text("""<svg xmlns="http://www.w3.org/2000/svg" width="360" height="88" viewBox="0 0 360 88" role="img" aria-label="PROMOGG"><rect x="4" y="8" width="72" height="72" rx="18" fill="#006d77"/><path fill="#ffbd30" d="M20 25h40v27H20z"/><path fill="#102a36" d="M27 32h26v5H27zm0 9h19v5H27zm0 9h13v5H27z"/><text x="96" y="57" font-family="Arial,sans-serif" font-size="42" font-weight="700" fill="#102a36">PROMOGG</text></svg>""", encoding="utf-8")
    LOGO_PNG_PATH.write_bytes(_png_rgb(360, 112))
    FAVICON_ICO_PATH.write_bytes(_favicon_ico())


def escrever_imagem_social():
    OG_IMAGE_PATH.write_text("""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630"><rect width="1200" height="630" fill="#006d77"/><rect x="72" y="84" width="1056" height="462" rx="24" fill="#ffffff"/><rect x="128" y="154" width="128" height="128" rx="24" fill="#ffbd30"/><path fill="#102a36" d="M158 188h68v20h-68zm0 34h50v20h-50zm0 34h35v20h-35z"/><text x="304" y="240" font-family="Arial,sans-serif" font-size="88" font-weight="700" fill="#102a36">Promogg</text><text x="304" y="322" font-family="Arial,sans-serif" font-size="38" fill="#35505b">Ofertas selecionadas do Mercado Livre</text><text x="128" y="460" font-family="Arial,sans-serif" font-size="30" fill="#35505b">Compare preços, acompanhe histórico e compre com segurança.</text></svg>""", encoding="utf-8")


def rodape_publico(ultima_atualizacao):
    return f"""<footer class="site-footer"><div class="footer-inner"><div><img src="/logo.svg" class="brand-logo" alt="PROMOGG"><p class="footer-note">Ofertas selecionadas com links seguros. Preços e disponibilidade podem mudar no Mercado Livre.</p><p class="footer-updated">Última atualização: {escape(ultima_atualizacao)}</p></div><nav class="footer-links" aria-label="Links institucionais"><a class="footer-link" href="/sobre/">Sobre</a><a class="footer-link" href="/seguranca/">Segurança</a><a class="footer-link" href="/sobre/#afiliados">Política de Afiliados</a><a class="footer-link" data-telegram-link hidden target="_blank" rel="noopener">Telegram</a></nav></div></footer>"""


def montar_index():
    estado = obter_estado_sistema()
    if estado["estado"] == OFFLINE:
        return montar_pagina_offline(estado)
    banner = ""
    if estado["estado"] == MANUTENCAO:
        banner = '<div class="system-banner" role="status">Estamos realizando melhorias internas. Algumas informações podem estar temporariamente desatualizadas.</div>'
    pagina = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="robots" content="index, follow">
    <meta name="description" content="Ofertas do Mercado Livre selecionadas pelo Promogg, com links seguros e atualização frequente.">
    <meta property="og:type" content="website">
    <meta property="og:locale" content="pt_BR">
    <meta property="og:site_name" content="Promogg">
    <meta property="og:title" content="Promogg | Ofertas selecionadas do Mercado Livre">
    <meta property="og:description" content="Encontre ofertas selecionadas do Mercado Livre com links seguros.">
    <meta property="og:url" content="https://promogg.com.br/">
    <meta property="og:image" content="https://promogg.com.br/og-promogg.svg">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="Promogg | Ofertas selecionadas do Mercado Livre">
    <meta name="twitter:description" content="Ofertas selecionadas do Mercado Livre com links seguros.">
    <meta name="twitter:image" content="https://promogg.com.br/og-promogg.svg">
    <title>Promogg | Ofertas selecionadas do Mercado Livre</title>
    <link rel="canonical" href="https://promogg.com.br/">
    <link rel="icon" href="favicon.ico" sizes="any">
    <link rel="icon" href="favicon.svg" type="image/svg+xml">
    <link rel="stylesheet" href="style.css">
    <script src="analytics.js" defer></script>
</head>
<body data-telegram-url="" data-analytics-url="__ANALYTICS_URL__">
    <a class="skip-link" href="#ofertas">Ir para as ofertas</a>
    <header class="site-header">
        <div class="header-inner">
            <a class="brand" href="#inicio" aria-label="Promogg, página inicial"><img src="logo.svg" class="brand-logo" alt="PROMOGG"></a>
            <div class="header-actions">
                <button class="button button-primary" id="refresh" type="button" aria-label="Atualizar ofertas">Atualizar ofertas</button>
            </div>
        </div>
    </header>
__BANNER__
    <main id="inicio">
        <section class="hero" aria-labelledby="titulo-principal">
            <div class="container hero-content">
                <p class="eyebrow">Promogg seleciona para você</p>
                <h1 id="titulo-principal">Ofertas do Mercado Livre, em um lugar fácil de acompanhar.</h1>
                <p class="hero-copy">Ofertas selecionadas com link seguro para você comparar e decidir com tranquilidade.</p>
                <div class="hero-actions">
                    <a class="button button-primary" href="#ofertas">Ver ofertas</a>
                    <a class="button button-secondary" href="assistente/">Consultar preços</a>
                    <a class="button button-telegram" data-telegram-link hidden target="_blank" rel="noopener">Entrar no Telegram</a>
                </div>
            </div>
        </section>
        <section class="content" id="ofertas" aria-labelledby="titulo-ofertas">
            <div class="container">
                <div class="section-heading">
                    <div>
                        <h2 id="titulo-ofertas">Ofertas em destaque</h2>
                        <p class="offer-count" id="offer-count" aria-live="polite">Carregando ofertas</p>
                    </div>
                    <p class="offer-count" id="generated-at"></p>
                </div>
                <form class="filters" id="filters" onsubmit="return false" aria-label="Filtrar ofertas">
                    <div class="field">
                        <label for="search">Buscar</label>
                        <input id="search" type="search" placeholder="O que você está procurando?" autocomplete="off">
                    </div>
                    <div class="field">
                        <label for="category">Categoria</label>
                        <select id="category"><option value="">Todas as categorias</option></select>
                    </div>
                    <div class="field">
                        <label for="sort">Ordenar</label>
                        <select id="sort">
                            <option value="recentes">Mais recentes</option>
                            <option value="menor-preco">Menor preço</option>
                            <option value="maior-preco">Maior preço</option>
                        </select>
                    </div>
                </form>
                <div class="offer-grid" id="offer-grid" aria-live="polite"></div>
                <nav class="pagination" aria-label="Paginação de ofertas">
                    <button class="button button-secondary" id="previous-page" type="button">Anterior</button>
                    <span class="page-indicator" id="page-indicator" aria-live="polite"></span>
                    <button class="button button-secondary" id="next-page" type="button">Próxima</button>
                </nav>
            </div>
        </section>
        <section class="disclosure" aria-labelledby="titulo-afiliado">
            <div class="container disclosure-inner">
                <div class="disclosure-badge" aria-hidden="true">i</div>
                <div>
                    <h2 id="titulo-afiliado">Sobre os links</h2>
                    <p>Alguns links são afiliados. Isso ajuda a manter o Promogg sem custo extra para você.</p>
                </div>
            </div>
        </section>
        <section class="content trust-section" aria-label="Como o Promogg funciona"><div class="container trust-grid"><div><h2>Ofertas com contexto</h2><p>Organizamos ofertas públicas, preço atual e histórico para facilitar comparações.</p></div><div><h2>Histórico de preços</h2><p>Quando há verificações suficientes, mostramos menor preço, média e variação.</p></div><div><h2>Transparência</h2><p>Alguns links são afiliados e podem gerar comissão sem alterar o preço para você.</p></div></div></section>
    </main>
    __FOOTER__
    <script src="app.js" defer></script>
</body>
</html>
"""
    return pagina.replace("__ANALYTICS_URL__", escape(analytics_public_url(), quote=True)).replace("__FOOTER__", rodape_publico(datetime.now().strftime("%d/%m/%Y %H:%M"))).replace("__BANNER__", banner)


def montar_pagina_offline(estado):
    atualizado = datetime.now().strftime("%d/%m/%Y %H:%M")
    return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="robots" content="noindex, follow"><title>Promogg temporariamente offline</title><meta name="description" content="Promogg temporariamente offline para manutenção."><link rel="icon" href="favicon.ico" sizes="any"><link rel="stylesheet" href="style.css"></head><body><header class="site-header"><div class="header-inner"><img src="logo.svg" class="brand-logo" alt="PROMOGG"></div></header><main class="offline-page"><section class="container"><h1>Promogg temporariamente offline para manutenção.</h1><p class="hero-copy">Estamos cuidando de melhorias internas para voltar com uma experiência mais confiável.</p><p class="detail-notice">Banco, histórico e backups permanecem preservados. Última alteração de estado: {escape(estado.get('atualizado_em') or atualizado)}.</p></section></main>{rodape_publico(atualizado)}</body></html>"""


def gerar_pagina_assistente():
    ASSISTENTE_DIR.mkdir(parents=True, exist_ok=True)
    (ASSISTENTE_DIR / "index.html").write_text("""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="robots" content="index, follow"><title>Assistente de Preços | Promogg</title><meta name="description" content="Consulte preços e histórico disponíveis no catálogo público do Promogg."><link rel="canonical" href="https://promogg.com.br/assistente/"><link rel="icon" href="../favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="../style.css"></head><body><header class="site-header"><div class="header-inner"><a class="brand" href="../" aria-label="Página inicial"><img src="../logo.svg" class="brand-logo" alt="PROMOGG"></a></div></header><main class="content"><div class="container assistant"><a class="breadcrumb" href="../">Voltar para as ofertas</a><h1>Assistente de preços</h1><p class="hero-copy">Respostas locais baseadas somente no catálogo público e histórico disponível.</p><form id="assistant-form"><label for="question">Sua pergunta</label><input id="question" type="search" placeholder="Ex.: Qual foi o menor preço do PS5?"><button class="button button-primary" type="submit">Consultar</button></form><div class="suggestions"><button data-q="Quais produtos estão no menor preço?">Menor preço</button><button data-q="Quais ofertas têm maior desconto?">Maior desconto</button><button data-q="Qual categoria tem mais ofertas?">Categorias</button></div><section id="assistant-answer" class="feedback" aria-live="polite"><h2>Pronto para consultar</h2><p>Não enviamos sua pergunta para servidores externos.</p></section></div></main><script src="assistant.js" defer></script></body></html>""", encoding="utf-8")
    (ASSISTENTE_DIR / "assistant.js").write_text(r"""const box=document.querySelector('#assistant-answer'),form=document.querySelector('#assistant-form'),q=document.querySelector('#question');let produtos=[];const money=v=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(Number(v)||0);const esc=s=>String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));function link(p){return `<a href="../${esc(p.produto_url)}">${esc(p.titulo)}</a>`}function responder(pergunta){const texto=pergunta.toLowerCase();if(!produtos.length)return 'Não foi possível carregar os dados públicos agora. Tente novamente mais tarde.';if(texto.includes('categoria')){const c={};produtos.forEach(p=>c[p.categoria]=(c[p.categoria]||0)+1);const [n,t]=Object.entries(c).sort((a,b)=>b[1]-a[1])[0];return `A categoria com mais ofertas é <strong>${esc(n)}</strong>, com ${t} oferta(s).`}if(texto.includes('maior desconto')){const p=[...produtos].sort((a,b)=>(b.desconto_percentual||0)-(a.desconto_percentual||0))[0];return p&&p.desconto_percentual?`Maior desconto disponível: ${link(p)} com <strong>${Number(p.desconto_percentual).toFixed(0)}% OFF</strong>.`: 'Ainda não há descontos suficientes no catálogo público.'}if(texto.includes('menor preço')&&!texto.match(/do |da /)){const itens=produtos.filter(p=>Number(p.preco_atual)<=Number(p.menor_preco)+.01).slice(0,5);return itens.length?`Produtos no menor preço registrado: ${itens.map(link).join(', ')}.`:'Não encontrei produtos no menor preço histórico.'}const termos=texto.replace(/qual|foi|menor|preço|preco|vale|comprar|agora|esse|produto|do|da|o|a|\?/g,' ').trim().split(/\s+/).filter(Boolean);const p=produtos.map(x=>({...x,pontos:termos.reduce((n,t)=>n+(x.titulo||'').toLowerCase().includes(t),0)})).sort((a,b)=>b.pontos-a.pontos)[0];if(!p||!p.pontos)return 'Não encontrei um produto correspondente no catálogo público. Tente usar marca ou modelo.';const hist=Number(p.menor_preco)>0,barato=hist&&Number(p.preco_atual)<=Number(p.menor_preco)+.01;return `${link(p)}. Preço atual: <strong>${money(p.preco_atual)}</strong>${hist?`; menor preço registrado: <strong>${money(p.menor_preco)}</strong>`:''}${p.preco_medio?`; média: ${money(p.preco_medio)}`:''}. ${barato?'Está no menor preço registrado disponível.':'Não há sinal histórico suficiente para afirmar que está barato.'} Atualização: ${esc(p.ultima_atualizacao||'indisponível')}.`}function render(t){box.innerHTML=`<h2>Resposta</h2><p>${t}</p>`}form.addEventListener('submit',e=>{e.preventDefault();render(responder(q.value))});document.querySelectorAll('[data-q]').forEach(b=>b.onclick=()=>{q.value=b.dataset.q;render(responder(q.value))});fetch('../assistente_dados.json').then(r=>r.ok?r.json():Promise.reject()).then(d=>produtos=d.produtos||[]).catch(()=>render('Não foi possível carregar os dados públicos agora. O restante do site continua disponível.'));""", encoding="utf-8")


def formatar_data_publica(valor):
    if not valor:
        return "Data indisponível"
    try:
        return datetime.strptime(str(valor), "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
    except ValueError:
        try:
            return datetime.strptime(str(valor), "%Y-%m-%d %H:%M").strftime("%d/%m/%Y %H:%M")
        except ValueError:
            return str(valor)


def historico_publico_produto(produto_id, limite=10):
    with conectar() as conn:
        registros = [dict(row) for row in conn.execute(
            """
            SELECT preco, data_verificacao
            FROM historico_precos
            WHERE produto_id = ? AND preco IS NOT NULL
            ORDER BY id DESC LIMIT ?
            """,
            (produto_id, limite),
        ).fetchall()]
        menor = conn.execute(
            """
            SELECT preco, data_verificacao FROM historico_precos
            WHERE produto_id = ? AND preco IS NOT NULL
            ORDER BY preco ASC, id ASC LIMIT 1
            """,
            (produto_id,),
        ).fetchone()
    return registros, dict(menor) if menor else None


def tendencia_preco(variacao):
    if variacao < 0:
        return "caindo"
    if variacao > 0:
        return "subindo"
    return "estável"


def montar_pagina_produto(oferta, historico, menor_historico):
    titulo = escape(oferta["titulo"])
    descricao = escape(f"{oferta['titulo']} por {oferta['preco_formatado']} no Mercado Livre. Histórico e link seguro no Promogg.", quote=True)
    url = f"{BASE_URL}/{oferta['produto_url']}"
    imagem = oferta.get("imagem_url", "")
    imagem_tag = (
        f'<img src="{escape(imagem, quote=True)}" alt="{titulo}">' if imagem
        else '<span class="image-fallback">Promogg</span>'
    )
    og_imagem = f'\n    <meta property="og:image" content="{escape(imagem, quote=True)}">' if imagem else ""
    twitter_imagem = imagem or f"{BASE_URL}/og-promogg.svg"
    variacao = float(oferta.get("variacao_preco") or 0)
    preco_original = oferta.get("preco_original")
    desconto = float(oferta.get("desconto_percentual") or 0)
    economia = float(oferta.get("economia_valor") or 0)
    detalhes_preco = ""
    if preco_original:
        detalhes_preco += f'<p class="detail-notice"><s>{escape(formatar_preco(preco_original))}</s></p>'
    if desconto or economia:
        detalhes_preco += f'<p class="record-badge">{escape(f"{desconto:.0f}% OFF" if desconto else "")}{escape(f" · Economize {formatar_preco(economia)}" if economia else "")}</p>'
    resumo = [
        ("Menor preço", oferta["menor_preco_formatado"]),
        ("Tendência", tendencia_preco(variacao).capitalize()),
    ]
    if oferta.get("maior_preco"):
        resumo.append(("Maior preço", formatar_preco(oferta["maior_preco"])))
    if oferta.get("preco_medio"):
        resumo.append(("Preço médio", formatar_preco(oferta["preco_medio"])))
    resumo_html = "".join(
        f"<div><span>{escape(rotulo)}</span><strong>{escape(valor)}</strong></div>" for rotulo, valor in resumo
    )
    linhas_historico = "".join(
        f"<tr><td>{escape(formatar_data_publica(registro['data_verificacao']))}</td><td>{escape(formatar_preco(registro['preco']))}</td></tr>"
        for registro in historico
    )
    bloco_historico = ""
    if historico:
        menor_data = formatar_data_publica(menor_historico["data_verificacao"]) if menor_historico else "Data indisponível"
        bloco_historico = f"""
        <section class="history-section" aria-labelledby="historico-titulo">
            <h2 id="historico-titulo">Histórico de preços</h2>
            <p class="detail-notice">Menor preço histórico: <strong>{escape(oferta['menor_preco_formatado'])}</strong> em {escape(menor_data)}.</p>
            <table class="history-table">
                <thead><tr><th>Verificação</th><th>Preço</th></tr></thead>
                <tbody>{linhas_historico}</tbody>
            </table>
        </section>"""
    schema = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": oferta["titulo"],
        "category": oferta["categoria"],
        "url": url,
        "image": imagem or None,
        "offers": {
            "@type": "Offer",
            "price": oferta["preco"],
            "priceCurrency": "BRL",
            "url": oferta["link"],
        },
    }
    schema = {chave: valor for chave, valor in schema.items() if valor is not None}
    schema_json = json.dumps(schema, ensure_ascii=False).replace("<", "\\u003c")
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="robots" content="index, follow">
    <title>{titulo} | Promogg</title>
    <meta name="description" content="{descricao}">
    <link rel="canonical" href="{escape(url, quote=True)}">
    <meta property="og:type" content="product">
    <meta property="og:locale" content="pt_BR">
    <meta property="og:site_name" content="Promogg">
    <meta property="og:title" content="{titulo} | Promogg">
    <meta property="og:description" content="{descricao}">
    <meta property="og:url" content="{escape(url, quote=True)}">{og_imagem}
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{titulo} | Promogg">
    <meta name="twitter:description" content="{descricao}">
    <meta name="twitter:image" content="{escape(twitter_imagem, quote=True)}">
    <link rel="icon" href="../../../favicon.svg" type="image/svg+xml">
    <link rel="stylesheet" href="../../../style.css">
    <script type="application/ld+json">{schema_json}</script>
</head>
<body data-analytics-url="{escape(analytics_public_url(), quote=True)}">
    <header class="site-header"><div class="header-inner"><a class="brand" href="../../../" aria-label="Promogg, página inicial"><span class="brand-mark" aria-hidden="true">P</span>Promogg</a></div></header>
    <main class="detail-page"><div class="container">
        <a class="breadcrumb" href="../../../">Voltar para as ofertas</a>
        <article class="product-detail">
            <div class="product-image">{imagem_tag}</div>
            <div class="product-info">
                <span class="product-category">{escape(oferta.get('categoria_caminho') or oferta['categoria'])}</span>
                <h1>{titulo}</h1>
                <p class="product-price">{escape(oferta['preco_formatado'])}</p>
                {detalhes_preco}
                <p class="detail-updated">Última atualização: {escape(formatar_data_publica(oferta.get('ultima_verificacao') or oferta.get('data_publicacao')))}</p>
                <div class="price-summary">{resumo_html}</div>
                <a class="button button-secondary" href="{escape(oferta['link'], quote=True)}" target="_blank" rel="noopener sponsored" data-analytics-click="compra_produto" data-item-id="{escape(oferta['item_id'], quote=True)}" data-titulo="{escape(oferta['titulo'], quote=True)}" data-categoria="{escape(oferta['categoria'], quote=True)}">Ver oferta no Mercado Livre</a>
                <p class="detail-notice">O preço e a disponibilidade podem mudar no Mercado Livre.</p>
                <p class="detail-notice">Este link pode ser afiliado, sem custo extra para você.</p>
            </div>
        </article>{bloco_historico}
    </div></main>
    <footer class="site-footer"><div class="footer-inner"><div><div class="footer-brand">Promogg</div><p class="footer-note">Ofertas selecionadas com links seguros.</p></div></div></footer>
    <script src="../../../analytics.js" defer></script>
</body>
</html>
"""


def montar_redirecionamento_produto(oferta):
    destino = f"/{oferta['produto_url']}"
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8"><meta name="robots" content="noindex, follow">
<meta http-equiv="refresh" content="0; url={escape(destino, quote=True)}">
<link rel="canonical" href="{BASE_URL}/{escape(oferta['produto_url'], quote=True)}">
<title>Redirecionando para Promogg</title></head>
<body><p><a href="{escape(destino, quote=True)}">Abrir oferta no Promogg</a></p></body></html>"""


def montar_pagina_categoria(categoria, ofertas):
    caminho = url_categoria(categoria)
    url = f"{BASE_URL}/{caminho}"
    descricao = f"Ofertas de {categoria} selecionadas pelo Promogg, com preços e links seguros."
    cards = "".join(
        f"""<article class="offer-card"><a class="offer-image" href="/{escape(oferta['produto_url'], quote=True)}" data-analytics-click="card_oferta" data-item-id="{escape(oferta['item_id'], quote=True)}" data-titulo="{escape(oferta['titulo'], quote=True)}" data-categoria="{escape(oferta['categoria'], quote=True)}">"""
        + (f'<img src="{escape(oferta["imagem_url"], quote=True)}" alt="{escape(oferta["titulo"])}" loading="lazy">' if oferta.get("imagem_url") else '<span class="image-fallback">Promogg</span>')
        + f"""</a><div class="offer-body"><h2><a href="/{escape(oferta['produto_url'], quote=True)}">{escape(oferta['titulo'])}</a></h2>
        <p class="offer-price">{escape(oferta['preco_formatado'])}</p><a class="button button-secondary" href="/{escape(oferta['produto_url'], quote=True)}" data-analytics-click="card_oferta" data-item-id="{escape(oferta['item_id'], quote=True)}" data-titulo="{escape(oferta['titulo'], quote=True)}" data-categoria="{escape(oferta['categoria'], quote=True)}">Ver detalhes</a></div></article>"""
        for oferta in ofertas
    )
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="index, follow"><title>Ofertas de {escape(categoria)} | Promogg</title>
<meta name="description" content="{escape(descricao, quote=True)}"><link rel="canonical" href="{escape(url, quote=True)}">
<meta property="og:type" content="website"><meta property="og:locale" content="pt_BR"><meta property="og:site_name" content="Promogg">
<meta property="og:title" content="Ofertas de {escape(categoria)} | Promogg"><meta property="og:description" content="{escape(descricao, quote=True)}">
<meta property="og:url" content="{escape(url, quote=True)}"><meta property="og:image" content="{BASE_URL}/og-promogg.svg">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="Ofertas de {escape(categoria)} | Promogg">
<meta name="twitter:description" content="{escape(descricao, quote=True)}"><meta name="twitter:image" content="{BASE_URL}/og-promogg.svg">
<link rel="icon" href="../../favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="../../style.css"></head>
<body data-analytics-url="{escape(analytics_public_url(), quote=True)}"><header class="site-header"><div class="header-inner"><a class="brand" href="../../" aria-label="Promogg, página inicial"><span class="brand-mark" aria-hidden="true">P</span>Promogg</a></div></header>
<main class="content"><div class="container"><a class="breadcrumb" href="../../">Todas as ofertas</a><section aria-labelledby="titulo-categoria"><h1 id="titulo-categoria">Ofertas de {escape(categoria)}</h1><p class="hero-copy">Produtos selecionados com histórico de preços e links seguros.</p><div class="offer-grid">{cards}</div></section></div></main>
<footer class="site-footer"><div class="footer-inner"><div><div class="footer-brand">Promogg</div><p class="footer-note">Os preços podem mudar no Mercado Livre.</p></div></div></footer><script src="../../analytics.js" defer></script></body></html>"""


def gerar_paginas_categorias(ofertas):
    if CATEGORIAS_DIR.exists():
        shutil.rmtree(CATEGORIAS_DIR)
    CATEGORIAS_DIR.mkdir(parents=True, exist_ok=True)
    por_categoria = {}
    for oferta in ofertas:
        por_categoria.setdefault(oferta["categoria"], []).append(oferta)
    for categoria, itens in por_categoria.items():
        destino = SITE_DIR / url_categoria(categoria)
        destino.mkdir(parents=True, exist_ok=True)
        (destino / "index.html").write_text(montar_pagina_categoria(categoria, itens), encoding="utf-8")
    return sorted(por_categoria)


def gerar_sitemap(ofertas, categorias):
    urls = ["/", "/sobre/", "/seguranca/", "/assistente/"] + [f"/{oferta['produto_url']}" for oferta in ofertas] + [f"/{url_categoria(categoria)}" for categoria in categorias]
    hoje = datetime.now().date().isoformat()
    entradas = "".join(
        f"  <url><loc>{escape(BASE_URL + caminho)}</loc><lastmod>{hoje}</lastmod></url>\n" for caminho in sorted(set(urls))
    )
    SITEMAP_PATH.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + entradas + "</urlset>\n",
        encoding="utf-8",
    )


def gerar_robots():
    ROBOTS_PATH.write_text(
        f"User-agent: *\nAllow: /\nDisallow: /ofertas.json\nDisallow: /logs/\nDisallow: /tmp/\nDisallow: /backups/\nSitemap: {BASE_URL}/sitemap.xml\n",
        encoding="utf-8",
    )


def gerar_404(categorias):
    links = "".join(f'<a class="tag" href="/{escape(url_categoria(categoria), quote=True)}">{escape(categoria)}</a>' for categoria in categorias[:8])
    NOT_FOUND_PATH.write_text(f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="robots" content="noindex, follow">
<title>Página não encontrada | Promogg</title><meta name="description" content="Encontre ofertas selecionadas no Promogg."><link rel="icon" href="favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="style.css"></head>
<body><main class="detail-page"><div class="container"><section class="empty-state"><h1>Página não encontrada</h1><p>Use a busca para encontrar uma oferta ou volte ao catálogo.</p><form id="busca-404"><label for="termo-404">Buscar ofertas</label><input id="termo-404" type="search" placeholder="Ex.: notebook, TV, tênis"><button class="button button-primary" type="submit">Buscar</button></form><p><a class="button button-secondary" href="/">Ir para a página inicial</a></p><div class="tags">{links}</div><div id="resultado-404" class="offer-grid"></div></section></div></main>
<script>const esc=s=>String(s||'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));document.querySelector('#busca-404').addEventListener('submit',async(e)=>{{e.preventDefault();const t=document.querySelector('#termo-404').value.trim().toLowerCase(),r=document.querySelector('#resultado-404');const d=await fetch('/ofertas.json').then(x=>x.json()).catch(()=>({{ofertas:[]}}));r.innerHTML=(d.ofertas||[]).filter(o=>(o.titulo||'').toLowerCase().includes(t)).slice(0,10).map(o=>`<article class="offer-card"><div class="offer-body"><h2>${{esc(o.titulo)}}</h2><p class="offer-price">${{esc(o.preco_formatado)}}</p><a class="button button-secondary" href="/${{esc(o.produto_url)}}">Ver detalhes</a></div></article>`).join('')||'<p>Nenhuma oferta encontrada.</p>';}});</script></body></html>""", encoding="utf-8")


def gerar_paginas_institucionais():
    paginas = {
        "sobre": ("Sobre o Promogg", "O Promogg reúne ofertas do Mercado Livre com curadoria e informações para comparação.", """<h1>Como funciona o Promogg</h1><p>Selecionamos ofertas e mantemos páginas públicas com preço atual, categoria e histórico quando disponível.</p><h2>Histórico e curadoria</h2><p>Os preços são monitorados para mostrar contexto de menor preço, média e variação. A publicação continua sujeita às regras de aprovação do Promogg.</p><h2 id="afiliados">Links afiliados e transparência</h2><p>Alguns links são afiliados. Isso não muda o preço para você e ajuda a manter o projeto. Preços e disponibilidade podem mudar no Mercado Livre.</p>"""),
        "seguranca": ("Segurança | Promogg", "Conheça as práticas de confidencialidade, integridade e disponibilidade do Promogg.", """<h1>Segurança e confiabilidade</h1><h2>Confidencialidade</h2><p>Tokens, arquivos de ambiente, banco local e registros internos não são publicados no site.</p><h2>Integridade</h2><p>Preços, links afiliados e histórico passam por validações. O histórico de verificações é preservado para auditoria.</p><h2>Disponibilidade</h2><p>O Promogg utiliza monitoramento, relatórios de saúde, backups e geração estática para manter o catálogo disponível.</p>"""),
    }
    for nome, (titulo, descricao, conteudo) in paginas.items():
        destino = SITE_DIR / nome
        destino.mkdir(parents=True, exist_ok=True)
        url = f"{BASE_URL}/{nome}/"
        (destino / "index.html").write_text(f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="robots" content="index, follow"><title>{escape(titulo)}</title><meta name="description" content="{escape(descricao, quote=True)}"><link rel="canonical" href="{url}"><meta property="og:type" content="website"><meta property="og:title" content="{escape(titulo)}"><meta property="og:description" content="{escape(descricao, quote=True)}"><meta property="og:url" content="{url}"><meta property="og:image" content="{BASE_URL}/og-promogg.svg"><link rel="icon" href="../favicon.ico" sizes="any"><link rel="stylesheet" href="../style.css"></head><body><header class="site-header"><div class="header-inner"><a class="brand" href="../" aria-label="Página inicial"><img src="../logo.svg" class="brand-logo" alt="PROMOGG"></a></div></header><main class="content"><article class="container detail-page">{conteudo}</article></main>{rodape_publico(datetime.now().strftime('%d/%m/%Y %H:%M'))}</body></html>""", encoding="utf-8")


def gerar_callback_oauth():
    """Página estática de retorno OAuth: exibe o código localmente, sem enviá-lo ao site."""
    OAUTH_CALLBACK_DIR.mkdir(parents=True, exist_ok=True)
    (OAUTH_CALLBACK_DIR / "index.html").write_text("""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="robots" content="noindex, nofollow"><title>Autorização Mercado Livre | Promogg</title><link rel="icon" href="../../favicon.ico" sizes="any"><link rel="stylesheet" href="../../style.css"></head><body><main class="offline-page"><section class="container"><img src="../../logo.svg" class="brand-logo" alt="PROMOGG"><h1>Autorização recebida</h1><p class="hero-copy">Copie o código abaixo e use-o somente no terminal local. Não compartilhe este código.</p><code id="codigo">Código não encontrado na URL.</code><p class="detail-notice">Execute: <strong>venv/bin/python trocar_token_meli.py "SEU_CODE"</strong></p></section></main><script>const c=new URLSearchParams(location.search).get('code');if(c)document.querySelector('#codigo').textContent=c;</script></body></html>""", encoding="utf-8")


def gerar_paginas_produtos(ofertas):
    if PRODUTOS_DIR.exists():
        shutil.rmtree(PRODUTOS_DIR)
    PRODUTOS_DIR.mkdir(parents=True, exist_ok=True)
    validas = []
    falhas = []
    itens_gerados = set()
    for oferta in ofertas:
        item_id = oferta["_item_id"]
        if item_id in itens_gerados:
            falhas.append({"item_id": item_id, "motivo": "item_id duplicado"})
            continue
        destino_relativo = str(oferta.get("produto_url") or "").strip("/")
        if not destino_relativo.startswith(f"produto/{item_id}/") or ".." in destino_relativo:
            falhas.append({"item_id": item_id, "motivo": "URL de produto inválida"})
            continue
        try:
            historico, menor_historico = historico_publico_produto(oferta["_produto_id"])
            destino = SITE_DIR / destino_relativo
            destino.mkdir(parents=True, exist_ok=True)
            pagina = destino / "index.html"
            pagina.write_text(montar_pagina_produto(oferta, historico, menor_historico), encoding="utf-8")
            if not pagina.is_file() or pagina.stat().st_size == 0:
                raise OSError("index.html não foi criado")
            legado = PRODUTOS_DIR / item_id
            legado.mkdir(parents=True, exist_ok=True)
            (legado / "index.html").write_text(montar_redirecionamento_produto(oferta), encoding="utf-8")
            itens_gerados.add(item_id)
            validas.append(oferta)
        except Exception as erro:
            falhas.append({"item_id": item_id, "motivo": str(erro)})
            registrar_log("integridade_site", f"Página de produto não gerada: item_id={item_id}", nivel="error", dados=str(erro))
    return validas, falhas


def gerar_site():
    SITE_DIR.mkdir(exist_ok=True)
    ofertas_brutas = listar_ofertas(deduplicar=False)
    ofertas = listar_ofertas()
    duplicidades_item = len(ofertas_brutas) - len(ofertas)
    ofertas, falhas_paginas = gerar_paginas_produtos(ofertas)
    paginas_produto = len(ofertas)
    categorias = gerar_paginas_categorias(ofertas)
    OFERTAS_PATH.write_text(json.dumps({
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "plataforma": "mercado_livre",
        "total": len(ofertas),
        "ofertas": [oferta_publica(oferta) for oferta in ofertas],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    escrever_dados_assistente(ofertas)
    escrever_css()
    escrever_javascript()
    escrever_favicon()
    escrever_identidade()
    escrever_imagem_social()
    INDEX_PATH.write_text(montar_index(), encoding="utf-8")
    gerar_paginas_institucionais()
    gerar_pagina_assistente()
    gerar_callback_oauth()
    gerar_sitemap(ofertas, categorias)
    gerar_robots()
    gerar_404(categorias)
    registrar_log("site", f"Site público gerado com {len(ofertas)} ofertas e {paginas_produto} páginas de produto em {SITE_DIR}/")
    registrar_log(
        "integridade_catalogo",
        f"Integridade do catálogo: analisadas={len(ofertas_brutas)} duplicidades_item={duplicidades_item} ofertas_publicas={len(ofertas)} paginas={paginas_produto} status={'OK' if not falhas_paginas else 'ATENÇÃO'}",
        dados=f"duplicidades_slug={duplicidades_item} falhas_paginas={len(falhas_paginas)}",
    )
    registrar_log("auditoria_site", f"Catálogo público gerado: ofertas_aprovadas={len(ofertas)} paginas_produto={paginas_produto}")
    registrar_evento_sistema(
        "geracao_site", "site", "concluido", "Site público gerado",
        f"ofertas={len(ofertas)} paginas_produto={paginas_produto} categorias={len(categorias)} falhas={len(falhas_paginas)}",
    )
    return {"ofertas": len(ofertas), "paginas_produto": paginas_produto, "categorias": len(categorias), "falhas_paginas": falhas_paginas, "pasta": str(SITE_DIR)}


def resumo_seo_publico():
    """Resumo apenas de arquivos estáticos para o painel interno."""
    paginas_produto = len(list(PRODUTOS_DIR.glob("*/*/index.html"))) if PRODUTOS_DIR.exists() else 0
    paginas_categoria = len(list(CATEGORIAS_DIR.glob("*/index.html"))) if CATEGORIAS_DIR.exists() else 0
    return {
        "paginas_indexaveis": 1 + paginas_produto + paginas_categoria,
        "produtos_indexaveis": paginas_produto,
        "categorias_indexaveis": paginas_categoria,
        "sitemap_gerado": SITEMAP_PATH.exists() and "<urlset" in SITEMAP_PATH.read_text(encoding="utf-8"),
        "robots_valido": ROBOTS_PATH.exists() and "Sitemap:" in ROBOTS_PATH.read_text(encoding="utf-8"),
    }


def validar_site_publico():
    """Valida o contrato do catálogo estático sem consultar dados sensíveis."""
    erros = []
    campos_permitidos = {
        "oferta_id", "item_id", "titulo", "preco", "preco_formatado", "menor_preco", "menor_preco_formatado",
        "preco_original", "desconto_percentual", "economia_valor",
        "variacao_preco", "destaque_menor_preco", "categoria", "link", "imagem_url",
        "plataforma", "produto_url", "data_publicacao", "ultima_verificacao", "maior_preco", "preco_medio",
        "categoria_caminho", "selo_mais_vendido", "selo_loja_oficial",
    }
    campos_internos = {"status", "observacao_interna", "aprovado_por", "aprovado_em", "id", "token", "cookie", "banco", "sqlite", "env"}
    try:
        dados = json.loads(OFERTAS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as erro:
        return [f"ofertas.json inválido: {erro}"]

    ofertas = dados.get("ofertas")
    if not isinstance(ofertas, list):
        erros.append("ofertas.json não contém uma lista de ofertas")
        return erros
    # A auditoria também detecta órfãs e duplicidades da fonte, além das
    # checagens individuais abaixo.
    from integridade_paginas_produto import auditar_paginas_produto
    integridade = auditar_paginas_produto()
    erros.extend(integridade.get("erros", []))
    if len(ofertas) != len(integridade.get("paginas", [])):
        erros.append("quantidade de ofertas públicas difere das páginas individuais válidas")
    for indice, oferta in enumerate(ofertas, start=1):
        campos = set(oferta)
        extras = campos - campos_permitidos
        internos = campos & campos_internos
        if extras:
            erros.append(f"oferta {indice}: campos públicos não permitidos: {', '.join(sorted(extras))}")
        if internos:
            erros.append(f"oferta {indice}: campo interno exposto: {', '.join(sorted(internos))}")
        if not link_afiliado_valido(oferta.get("link")):
            erros.append(f"oferta {indice}: link afiliado inválido")
        if re.search(r"(?i)(?:R\$\s*\d|\d+\s*%\s*OFF)", str(oferta.get("titulo", ""))):
            erros.append(f"oferta {indice}: título público contém preço ou desconto")
        imagem = oferta.get("imagem_url", "")
        if imagem and not imagem_publica_valida(imagem):
            erros.append(f"oferta {indice}: imagem não possui URL pública")
        pagina = SITE_DIR / str(oferta.get("produto_url", "")) / "index.html"
        if not oferta.get("produto_url") or not pagina.exists():
            erros.append(f"oferta {indice}: página individual não gerada")
        else:
            conteudo_pagina = pagina.read_text(encoding="utf-8").lower()
            if any(campo in conteudo_pagina for campo in ("observacao_interna", "aprovado_auto", "aprovado_manual", "pendente_revisao", "rejeitado")):
                erros.append(f"oferta {indice}: página individual expõe dado interno")
            for marcador in ("rel=\"canonical\"", "og:title", "twitter:card", "application/ld+json", "\"@type\": \"product\""):
                if marcador not in conteudo_pagina:
                    erros.append(f"oferta {indice}: SEO de página individual incompleto ({marcador})")
            partes_url = str(oferta.get("produto_url", "")).strip("/").split("/")
            if len(partes_url) != 3 or partes_url[0] != "produto" or not partes_url[2]:
                erros.append(f"oferta {indice}: URL amigável de produto inválida")

    script = SCRIPT_PATH.read_text(encoding="utf-8") if SCRIPT_PATH.exists() else ""
    if "const POR_PAGINA = 20;" not in script:
        erros.append("paginação de 20 ofertas não encontrada no JavaScript")
    if "oferta.status" in script or 'id="status"' in (INDEX_PATH.read_text(encoding="utf-8") if INDEX_PATH.exists() else ""):
        erros.append("interface pública ainda referencia status interno")
    if "produto_url" not in script:
        erros.append("link para páginas individuais não encontrado na listagem")
    analytics_script = SITE_DIR / "analytics.js"
    if not analytics_script.exists() or "PromoggAnalytics" not in analytics_script.read_text(encoding="utf-8"):
        erros.append("instrumentação de analytics não foi gerada")
    index = INDEX_PATH.read_text(encoding="utf-8").lower() if INDEX_PATH.exists() else ""
    for marcador in ("rel=\"canonical\"", "og:image", "twitter:card", "favicon.svg"):
        if marcador not in index:
            erros.append(f"SEO da página inicial incompleto ({marcador})")
    if not all(caminho.exists() for caminho in (FAVICON_PATH, FAVICON_ICO_PATH, LOGO_SVG_PATH, LOGO_PNG_PATH, OG_IMAGE_PATH, NOT_FOUND_PATH)):
        erros.append("favicon, logo, imagem social ou página 404 não foram gerados")
    if not (SOBRE_DIR / "index.html").exists() or not (SEGURANCA_DIR / "index.html").exists() or not (OAUTH_CALLBACK_DIR / "index.html").exists():
        erros.append("páginas institucionais não foram geradas")
    if not ROBOTS_PATH.exists() or "sitemap:" not in ROBOTS_PATH.read_text(encoding="utf-8").lower():
        erros.append("robots.txt inválido ou sem sitemap")
    if not SITEMAP_PATH.exists():
        erros.append("sitemap.xml não foi gerado")
    else:
        sitemap = SITEMAP_PATH.read_text(encoding="utf-8")
        if "<urlset" not in sitemap or f"{BASE_URL}/" not in sitemap:
            erros.append("sitemap.xml inválido")
        for oferta in ofertas:
            if f"{BASE_URL}/{oferta['produto_url']}" not in sitemap:
                erros.append("sitemap.xml não contém todas as páginas de produto")
                break
        for categoria in {oferta["categoria"] for oferta in ofertas}:
            if f"{BASE_URL}/{url_categoria(categoria)}" not in sitemap:
                erros.append("sitemap.xml não contém todas as páginas de categoria")
                break
        if f"{BASE_URL}/sobre/" not in sitemap or f"{BASE_URL}/seguranca/" not in sitemap:
            erros.append("sitemap.xml não contém as páginas institucionais")
        if f"{BASE_URL}/assistente/" not in sitemap:
            erros.append("sitemap.xml não contém a página do assistente")
    try:
        assistente = json.loads(ASSISTENTE_DADOS_PATH.read_text(encoding="utf-8"))
        permitidos = {"item_id", "titulo", "preco_atual", "menor_preco", "maior_preco", "preco_medio", "categoria", "categoria_caminho", "desconto_percentual", "economia_valor", "produto_url", "imagem_url", "ultima_atualizacao"}
        if not isinstance(assistente.get("produtos"), list) or any(set(item) - permitidos for item in assistente.get("produtos", [])):
            erros.append("assistente_dados.json contém estrutura ou campos não públicos")
    except (OSError, json.JSONDecodeError):
        erros.append("assistente_dados.json não foi gerado")
    if not (ASSISTENTE_DIR / "index.html").exists() or not (ASSISTENTE_DIR / "assistant.js").exists():
        erros.append("página pública do assistente não foi gerada")
    else:
        script_assistente = (ASSISTENTE_DIR / "assistant.js").read_text(encoding="utf-8")
        if any(url in script_assistente for url in ("http://", "https://", "fetch('http", 'fetch("http')):
            erros.append("assistente público referencia serviço externo")
        if not all(termo in script_assistente for termo in ("menor preço", "maior desconto", "categoria")):
            erros.append("perguntas básicas do assistente não foram encontradas")
    return erros


if __name__ == "__main__":
    resultado = gerar_site()
    print(f"Site gerado: {resultado['ofertas']} ofertas em {resultado['pasta']}")
