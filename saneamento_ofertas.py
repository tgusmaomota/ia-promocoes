"""Saneamento de título e informações promocionais sem tocar no histórico."""

import re
from decimal import Decimal, InvalidOperation


PADRAO_PRECO = re.compile(
    r"(?i)(?:\s*[-|–—,:]?\s*)(?:(de|por)\s*)?R\$\s*([0-9][0-9.]*(?:,[0-9]{1,2})?)(?![0-9])"
)
PADRAO_OFF = re.compile(r"(?i)(?:\s*[-|–—,:]?\s*)?\d{1,3}\s*%\s*OFF\b|(?:\s*[-|–—,:]?\s*)\bOFF\b")


def numero_brl(texto):
    valor = str(texto or "").strip().replace("R$", "").strip()
    if not valor:
        return None
    if "," in valor:
        valor = valor.replace(".", "").replace(",", ".")
    elif valor.count(".") >= 1:
        partes = valor.split(".")
        valor = "".join(partes) if len(partes[-1]) == 3 else valor
    try:
        numero = float(Decimal(valor))
    except (InvalidOperation, ValueError):
        return None
    return numero if numero > 0 else None


def sanear_titulo(titulo, preco_atual=None, preco_original=None, desconto_percentual=None):
    """Remove preço/desconto textual e infere comparativo somente quando seguro."""
    original = numero_brl(preco_original)
    atual = numero_brl(preco_atual)
    desconto = numero_brl(desconto_percentual) or 0
    valores_encontrados = []

    def substituir_preco(correspondencia):
        nonlocal original
        tipo, texto_preco = correspondencia.groups()
        valor = numero_brl(texto_preco)
        if valor:
            valores_encontrados.append((tipo or "", valor))
            if (tipo or "").lower() == "de" and (original is None or valor > original):
                original = valor
        return " "

    limpo = PADRAO_PRECO.sub(substituir_preco, str(titulo or ""))
    limpo = PADRAO_OFF.sub(" ", limpo)
    limpo = re.sub(r"\s{2,}", " ", limpo)
    limpo = re.sub(r"\s*[-|–—,:]\s*$", "", limpo).strip()

    # Preço avulso maior que o preço atual provavelmente é o antigo/de.
    if atual:
        for _, valor in valores_encontrados:
            if valor > atual and (original is None or valor > original):
                original = valor
    if original and atual and original > atual:
        desconto = round(((original - atual) / original) * 100, 2)
        economia = round(original - atual, 2)
    else:
        original = original if original and (not atual or original > atual) else None
        economia = None
    return {
        "titulo": limpo or str(titulo or "").strip(),
        "preco_original": original,
        "desconto_percentual": desconto or None,
        "economia_valor": economia,
        "corrigido": limpo != str(titulo or "").strip(),
    }
