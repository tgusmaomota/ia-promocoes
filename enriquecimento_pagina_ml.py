"""Extrai apenas sinais públicos visíveis da página de produto do Mercado Livre."""

import re
from datetime import datetime


def _numero(texto):
    texto = re.sub(r"[^0-9,.]", "", str(texto or "")).replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


def _inteiro(texto):
    numero = _numero(texto)
    return int(numero) if numero is not None else None


def _texto(pagina):
    try:
        return pagina.inner_text("body", timeout=12000)
    except Exception:
        return ""


def _breadcrumb(pagina):
    seletores = (
        "ol.andes-breadcrumb a", "nav[aria-label*='breadcrumb' i] a",
        "[data-testid*='breadcrumb' i] a", ".andes-breadcrumb a",
    )
    partes = []
    for seletor in seletores:
        try:
            partes = [item.inner_text().strip() for item in pagina.locator(seletor).all() if item.inner_text().strip()]
        except Exception:
            partes = []
        if partes:
            break
    partes = list(dict.fromkeys(partes))[:4]
    return partes


def extrair_sinais_comerciais(pagina):
    """Retorna dados públicos e sua origem; não acessa cookies, tokens ou dados privados."""
    texto = _texto(pagina)
    texto_normalizado = " ".join(texto.lower().split())
    caminho = _breadcrumb(pagina)
    off = re.search(r"\b(\d{1,2})\s*%\s*off\b", texto, re.I)
    avaliacao = re.search(r"\b([0-5][,.]\d)\s*(?:de\s*5)?\b", texto, re.I)
    avaliacoes = re.search(r"([\d.]+)\s*(?:opiniões|opiniones|avaliações|avaliaçoes)", texto, re.I)
    vendidos = re.search(r"\+?\s*([\d.]+)\s*vendidos", texto, re.I)
    preco_original = None
    for seletor in ("s.ui-pdp-price__original-value", ".ui-pdp-price__original-value", "del"):
        try:
            valor = _numero(pagina.locator(seletor).first.inner_text())
            if valor and valor > 0:
                preco_original = valor
                break
        except Exception:
            continue
    parcelamento = ""
    for linha in texto.splitlines():
        if re.search(r"\b\d+\s*x\s*R\$|sem juros", linha, re.I):
            parcelamento = linha.strip()[:180]
            break
    vendedor = ""
    for seletor in (".ui-pdp-seller__header__title", "[data-testid*='seller' i]", ".ui-pdp-seller"):
        try:
            candidato = pagina.locator(seletor).first.inner_text().strip()
            if candidato:
                vendedor = candidato.split("\n")[0][:120]
                break
        except Exception:
            continue
    return {
        "categoria_nivel_1": caminho[0] if len(caminho) > 0 else "",
        "categoria_nivel_2": caminho[1] if len(caminho) > 1 else "",
        "categoria_nivel_3": caminho[2] if len(caminho) > 2 else "",
        "categoria_nivel_4": caminho[3] if len(caminho) > 3 else "",
        "categoria_nome": caminho[-1] if caminho else "",
        "categoria_caminho": " > ".join(caminho),
        "origem_categoria": "breadcrumb_playwright" if caminho else "",
        "selo_mais_vendido": "mais vendido" in texto_normalizado,
        "selo_loja_oficial": "loja oficial" in texto_normalizado,
        "percentual_off": _inteiro(off.group(1)) if off else None,
        "preco_original_visivel": preco_original,
        "avaliacao": _numero(avaliacao.group(1)) if avaliacao else None,
        "quantidade_avaliacoes": _inteiro(avaliacoes.group(1)) if avaliacoes else None,
        "quantidade_vendida": _inteiro(vendidos.group(1)) if vendidos else None,
        "melhor_preco": "melhor preço" in texto_normalizado or "melhor preco" in texto_normalizado,
        "parcelamento": parcelamento,
        "vendedor_nome": vendedor,
        "vendedor_confiavel": "mercadolíder" in texto_normalizado or "mercadolider" in texto_normalizado or "loja oficial" in texto_normalizado,
        "dados_comerciais_origem": "playwright_pagina_publica",
        "dados_comerciais_atualizado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
