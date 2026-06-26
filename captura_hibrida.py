"""Captura resiliente de produto Mercado Livre sem persistir dados por conta própria."""

import os
import time
from datetime import datetime
from urllib.parse import urlparse

from dotenv import load_dotenv

from enriquecimento_pagina_ml import extrair_sinais_comerciais
from gerador_link_mercadolivre import link_afiliado_valido
from item_utils import extrair_item_id
from mercadolivre_api import ErroMercadoLivre, consultar_item, item_id_valido
from playwright_perfil import LoginNecessario, login_necessario_na_pagina
from saneamento_ofertas import sanear_titulo


load_dotenv(override=True)
_CACHE_API = {}


def _extrair_preco(texto):
    import re

    encontrado = re.search(r"R\$\s*([0-9][0-9.]*(?:,[0-9]{1,2})?)", str(texto or ""))
    if not encontrado:
        return 0.0
    valor = encontrado.group(1).replace(".", "").replace(",", ".")
    try:
        return float(valor)
    except ValueError:
        return 0.0


def captura_hibrida_ativa():
    return os.getenv("CAPTURA_HIBRIDA", "true").strip().lower() not in {"0", "false", "nao", "não"}


def _publica(url):
    partes = urlparse(str(url or "").strip())
    return partes.scheme == "https" and bool(partes.netloc)


def _titulo(pagina):
    for seletor in ('meta[property="og:title"]', "h1"):
        try:
            elemento = pagina.locator(seletor).first
            valor = elemento.get_attribute("content") if seletor.startswith("meta") else elemento.inner_text(timeout=5000)
            if str(valor or "").strip():
                return str(valor).strip()
        except Exception:
            pass
    return ""


def _preco(pagina):
    for seletor in ('meta[itemprop="price"]', 'meta[property="product:price:amount"]'):
        try:
            valor = pagina.locator(seletor).first.get_attribute("content")
            preco = float(str(valor).replace(",", "."))
            if preco > 0:
                return preco
        except Exception:
            pass
    try:
        return _extrair_preco(pagina.inner_text("body", timeout=8000))
    except Exception:
        return 0.0


def _imagem(pagina):
    for seletor in ('meta[property="og:image"]', "img[data-zoom]"):
        try:
            elemento = pagina.locator(seletor).first
            valor = elemento.get_attribute("content") if seletor.startswith("meta") else (elemento.get_attribute("data-zoom") or elemento.get_attribute("src"))
            if _publica(valor):
                return str(valor).strip()
        except Exception:
            pass
    return ""


def _descricao(pagina):
    try:
        return str(pagina.locator('meta[name="description"]').first.get_attribute("content") or "").strip()[:500]
    except Exception:
        return ""


def _api(item_id, tempos, fontes):
    if not item_id_valido(item_id):
        return {}
    inicio = time.monotonic()
    try:
        dados = _CACHE_API.setdefault(item_id, consultar_item(item_id))
        fontes.append("api_item")
        return dados if dados.get("disponivel") else {}
    except ErroMercadoLivre:
        fontes.append("api_indisponivel")
        return {}
    finally:
        tempos["api_item"] = round((time.monotonic() - inicio) * 1000)


def capturar_produto_hibrido(pagina, candidato, visual=False, gerar_afiliado=True):
    """Combina listagem, API e página pública; não grava banco nem altera status."""
    inicio_total = time.monotonic()
    tempos, fontes = {}, ["listagem"]
    permalink = str(candidato.get("permalink") or candidato.get("link_original") or "").strip()
    dados = {"item_id": str(candidato.get("item_id") or extrair_item_id(permalink)).upper(), "titulo": str(candidato.get("titulo") or "").strip(), "preco_atual": float(candidato.get("preco") or candidato.get("preco_atual") or 0), "imagem": str(candidato.get("imagem") or "").strip(), "link_original": permalink}
    api = _api(dados["item_id"], tempos, fontes)
    if api:
        dados.update({"titulo": api.get("titulo") or dados["titulo"], "preco_atual": api.get("preco") or dados["preco_atual"], "imagem": api.get("imagem_url") or dados["imagem"], "categoria_id": api.get("categoria_id", ""), "categoria_nome": api.get("categoria_nome", ""), "disponivel": bool(api.get("disponivel")), "origem_categoria": "api_oficial" if api.get("categoria_nome") else ""})
    # A página continua necessária para confirmar meli.la e complementar campos visíveis.
    inicio_pagina = time.monotonic()
    pagina.goto(permalink, wait_until="domcontentloaded", timeout=45000)
    pagina.wait_for_timeout(2200 if visual else 900)
    if login_necessario_na_pagina(pagina):
        raise LoginNecessario("sessão Mercado Livre não autenticada na captura híbrida")
    tempos["pagina_produto"] = round((time.monotonic() - inicio_pagina) * 1000)
    fontes.append("playwright_pagina")
    dados["item_id"] = extrair_item_id(pagina.url) or extrair_item_id(pagina.content()) or dados["item_id"]
    dados["titulo"] = dados["titulo"] or _titulo(pagina)
    dados["preco_atual"] = dados["preco_atual"] or _preco(pagina)
    dados["imagem"] = dados["imagem"] or _imagem(pagina)
    dados["descricao_curta"] = _descricao(pagina)
    sinais = extrair_sinais_comerciais(pagina)
    if not dados.get("categoria_nome"):
        dados["categoria_nome"] = sinais.get("categoria_nome", "")
        dados["origem_categoria"] = sinais.get("origem_categoria", "")
    inicio_afiliado = time.monotonic()
    if gerar_afiliado:
        from gerador_afiliados_oficial import gerar_link_oficial_na_pagina

        dados["link_afiliado"] = gerar_link_oficial_na_pagina(pagina, permalink, navegar=False)
    tempos["afiliado"] = round((time.monotonic() - inicio_afiliado) * 1000)
    preco_original = sinais.get("preco_original_visivel") or candidato.get("preco_original")
    saneado = sanear_titulo(dados["titulo"], dados["preco_atual"], preco_original, sinais.get("percentual_off") or candidato.get("desconto"))
    categoria_api = dados.get("categoria_nome", "")
    dados.update({**sinais, "titulo": saneado["titulo"], "preco": dados["preco_atual"], "preco_original": saneado["preco_original"], "desconto_percentual": saneado["desconto_percentual"], "economia_valor": saneado["economia_valor"], "categoria_nome": categoria_api or sinais.get("categoria_nome", ""), "categoria": categoria_api or sinais.get("categoria_nome") or "ofertas", "origem_categoria": "api_oficial" if categoria_api else sinais.get("origem_categoria", ""), "plataforma": "mercado_livre", "status": "coletado", "data_coleta": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    obrigatorios = {"item_id": item_id_valido(dados.get("item_id")), "titulo": bool(dados.get("titulo")), "preco": float(dados.get("preco_atual") or 0) > 0, "imagem": _publica(dados.get("imagem")), "permalink": _publica(permalink), "meli_la": link_afiliado_valido(dados.get("link_afiliado"))}
    tempos["total"] = round((time.monotonic() - inicio_total) * 1000)
    return {"produto": dados, "fontes": fontes, "tempos_ms": tempos, "campos_validos": [nome for nome, ok in obrigatorios.items() if ok], "campos_faltantes": [nome for nome, ok in obrigatorios.items() if not ok], "completo": all(obrigatorios.values())}


def validar_captura_hibrida():
    erros = []
    if not callable(capturar_produto_hibrido):
        erros.append("captura híbrida indisponível")
    if not callable(captura_hibrida_ativa):
        erros.append("fallback da captura híbrida indisponível")
    return erros
