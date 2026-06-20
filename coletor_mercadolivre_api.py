"""Coleta de candidatos pela API oficial do Mercado Livre.

A API de busca do Mercado Livre trabalha por termos; os termos ficam no .env
para que a fonte seja explícita e ajustável sem alterar código.
"""

import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

from mercadolivre_api import ErroMercadoLivre, buscar_itens, consultar_categoria
from banco import obter_saude_coleta_api, registrar_evento_sistema, registrar_log, registrar_saude_coleta_api


load_dotenv()

TERMOS_PADRAO = ("ofertas", "tecnologia", "casa", "moda")


class BuscaApiTemporariamenteIndisponivel(ErroMercadoLivre):
    pass


def termos_coleta():
    valor = os.getenv("MELI_COLETA_TERMOS", "").strip()
    termos = [termo.strip() for termo in valor.split(",") if termo.strip()]
    return termos or list(TERMOS_PADRAO)


def limite_coleta():
    try:
        return max(1, min(int(os.getenv("MELI_COLETA_LIMITE", "30")), 50))
    except ValueError:
        return 30


def horas_cache_busca():
    try:
        return max(1, min(int(os.getenv("MELI_API_BUSCA_CACHE_HORAS", "6")), 24))
    except ValueError:
        return 6


def busca_api_bloqueada():
    saude = obter_saude_coleta_api()
    if saude.get("status") != "403" or not saude.get("bloqueado_ate"):
        return False
    try:
        return datetime.strptime(saude["bloqueado_ate"], "%Y-%m-%d %H:%M:%S") > datetime.now()
    except ValueError:
        return False


def _registrar_busca_403(erro):
    bloqueado_ate = (datetime.now() + timedelta(hours=horas_cache_busca())).strftime("%Y-%m-%d %H:%M:%S")
    registrar_saude_coleta_api("403", "Busca oficial respondeu HTTP 403", bloqueado_ate)
    registrar_log(
        "coleta_api",
        f"Busca API indisponível (HTTP 403); Playwright será usado até {bloqueado_ate}",
        nivel="warning",
    )
    registrar_evento_sistema(
        "coleta_api_busca", "mercado_livre", "aviso",
        "Busca API indisponível; fallback Playwright ativado", str(erro),
    )


def _numero(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return 0.0


def _normalizar_item(item, categorias):
    item_id = str(item.get("id") or "").strip().upper()
    titulo = str(item.get("title") or "").strip()
    permalink = str(item.get("permalink") or "").strip()
    preco = _numero(item.get("price"))
    if not item_id or not titulo or not permalink or preco <= 0:
        return None

    categoria_id = str(item.get("category_id") or "").strip()
    if categoria_id and categoria_id not in categorias:
        try:
            categorias[categoria_id] = str(consultar_categoria(categoria_id).get("name") or "").strip()
        except ErroMercadoLivre:
            categorias[categoria_id] = ""

    original = _numero(item.get("original_price"))
    if original <= preco:
        original = None
    vendedor = item.get("seller") or {}
    return {
        "item_id": item_id,
        "titulo": titulo,
        "preco": preco,
        "preco_atual": preco,
        "preco_anterior": original,
        "link": permalink,
        "link_original": permalink,
        "imagem": str(item.get("thumbnail") or "").strip(),
        "categoria_id": categoria_id,
        "categoria_nome": categorias.get(categoria_id, ""),
        "categoria": categorias.get(categoria_id, "") or "ofertas",
        "disponivel": True,
        "status_api": str(item.get("status") or "active").lower(),
        "seller_id": vendedor.get("id"),
        "condicao": str(item.get("condition") or "").strip(),
        "desconto": round(((original - preco) / original) * 100, 2) if original else 0,
        "tipo_promocao": "api_oficial",
        "origem_coleta": "api",
        "data_coleta": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def coletar_ofertas_api(termos=None, limite=None):
    """Retorna candidatos válidos sem persistir nenhum dado no SQLite."""
    if busca_api_bloqueada():
        raise BuscaApiTemporariamenteIndisponivel("Busca API em cache de indisponibilidade (HTTP 403)")

    termos = termos or termos_coleta()
    limite = limite or limite_coleta()
    vistos = set()
    categorias = {}
    resultados = []
    falhas = []

    for termo in termos:
        try:
            itens = buscar_itens(termo, limite=limite)
        except ErroMercadoLivre as erro:
            if "HTTP 403" in str(erro):
                _registrar_busca_403(erro)
                raise BuscaApiTemporariamenteIndisponivel("Busca API bloqueada por HTTP 403") from erro
            falhas.append(f"{termo}: {erro}")
            continue
        for item in itens:
            produto = _normalizar_item(item, categorias)
            if not produto or produto["item_id"] in vistos:
                continue
            vistos.add(produto["item_id"])
            resultados.append(produto)

    if not resultados and falhas:
        raise ErroMercadoLivre("; ".join(falhas))
    registrar_saude_coleta_api("ok", f"Busca oficial retornou {len(resultados)} candidato(s)", None)
    return resultados


def validar_coleta_api():
    modo = os.getenv("MELI_COLETA_MODO", "auto").strip().lower()
    erros = []
    if modo not in {"api", "playwright", "auto"}:
        erros.append("MELI_COLETA_MODO deve ser api, playwright ou auto")
    if not termos_coleta():
        erros.append("MELI_COLETA_TERMOS não possui termos válidos")
    return erros
