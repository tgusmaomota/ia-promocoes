import re
import os

import requests
from dotenv import load_dotenv


API_BASE = "https://api.mercadolibre.com"
ITEM_ID_RE = re.compile(r"^MLB\d{8,14}$", re.IGNORECASE)
TIMEOUT_PADRAO = (4, 8)

# O token recém-renovado no .env deve prevalecer sobre variáveis antigas
# herdadas do shell, evitando chamadas com access token expirado.
load_dotenv(override=True)


class ErroMercadoLivre(RuntimeError):
    pass


def item_id_valido(item_id):
    return bool(ITEM_ID_RE.fullmatch(str(item_id or "").strip()))


def _cabecalhos():
    cabecalhos = {
        "Accept": "application/json",
        "User-Agent": "Promogg/1.0 (monitoramento de precos)",
    }
    token = os.getenv("MELI_ACCESS_TOKEN", "").strip()
    if token:
        cabecalhos["Authorization"] = f"Bearer {token}"
    return cabecalhos


def _get_json(url, timeout, params=None):
    cabecalhos = _cabecalhos()
    token = os.getenv("MELI_ACCESS_TOKEN", "").strip()
    try:
        resposta = requests.get(url, timeout=timeout, headers=cabecalhos, params=params)
    except requests.RequestException as erro:
        raise ErroMercadoLivre(f"falha de rede: {erro}") from erro

    if resposta.status_code == 404:
        return None
    if resposta.status_code != 200:
        detalhe = ""
        if resposta.status_code == 403 and not token:
            detalhe = "; configure MELI_ACCESS_TOKEN via OAuth"
        raise ErroMercadoLivre(f"API respondeu HTTP {resposta.status_code}{detalhe}")

    try:
        return resposta.json()
    except ValueError as erro:
        raise ErroMercadoLivre("API retornou conteúdo inválido") from erro


def buscar_itens(termo, limite=50, timeout=TIMEOUT_PADRAO):
    """Pesquisa anúncios ativos no catálogo público autenticado do Mercado Livre."""
    termo = str(termo or "").strip()
    if not termo:
        raise ErroMercadoLivre("termo de busca vazio")
    try:
        limite = max(1, min(int(limite), 50))
    except (TypeError, ValueError):
        limite = 50

    dados = _get_json(
        f"{API_BASE}/sites/MLB/search",
        timeout,
        params={"q": termo, "limit": limite},
    )
    if not isinstance(dados, dict):
        raise ErroMercadoLivre("busca não retornou uma lista válida")
    return dados.get("results", [])


def consultar_categoria(category_id, timeout=TIMEOUT_PADRAO):
    category_id = str(category_id or "").strip()
    if not category_id:
        return {}
    dados = _get_json(f"{API_BASE}/categories/{category_id}", timeout)
    return dados if isinstance(dados, dict) else {}


def consultar_item(item_id, timeout=TIMEOUT_PADRAO):
    """Consulta apenas dados públicos necessários ao monitoramento de um item MLB."""
    item_id = str(item_id or "").strip().upper()
    if not item_id_valido(item_id):
        raise ErroMercadoLivre(f"item_id inválido: {item_id or 'vazio'}")

    item = _get_json(f"{API_BASE}/items/{item_id}", timeout)
    if item is None:
        return {"item_id": item_id, "disponivel": False, "motivo": "item não encontrado"}

    status = str(item.get("status", "")).lower()
    if status and status != "active":
        return {
            "item_id": item_id,
            "disponivel": False,
            "motivo": f"status Mercado Livre: {status}",
        }

    preco = item.get("price")
    try:
        preco = float(preco)
    except (TypeError, ValueError) as erro:
        raise ErroMercadoLivre("item sem preço numérico") from erro
    if preco <= 0:
        raise ErroMercadoLivre("item com preço inválido")

    categoria_id = str(item.get("category_id") or "").strip()
    categoria_nome = ""
    if categoria_id:
        try:
            categoria = consultar_categoria(categoria_id, timeout)
            if categoria:
                categoria_nome = str(categoria.get("name") or "").strip()
        except ErroMercadoLivre:
            # O item continua útil para monitoramento mesmo se o endpoint de
            # categorias estiver temporariamente restrito.
            categoria_nome = ""

    return {
        "item_id": item_id,
        "titulo": str(item.get("title") or "").strip(),
        "preco": preco,
        "link_original": str(item.get("permalink") or "").strip(),
        "categoria_id": categoria_id,
        "categoria_nome": categoria_nome,
        "imagem_url": str(item.get("thumbnail") or "").strip(),
        "disponivel": True,
        "motivo": "ok",
    }
