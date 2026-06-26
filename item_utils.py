"""Utilidades compartilhadas para IDs de anúncios Mercado Livre."""

import re


ITEM_ID_PADRAO = re.compile(r"\bMLB\d{6,14}\b", re.IGNORECASE)


def extrair_item_id(valor):
    """Extrai o primeiro item_id no formato MLB + números."""
    encontrado = ITEM_ID_PADRAO.search(str(valor or ""))
    return encontrado.group(0).upper() if encontrado else ""

