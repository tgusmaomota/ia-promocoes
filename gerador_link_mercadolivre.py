from urllib.parse import urlparse


def link_afiliado_valido(link):
    link = str(link or "").strip()
    if not link:
        return False

    partes = urlparse(link)
    return partes.scheme == "https" and (partes.hostname or "").lower() == "meli.la" and bool(partes.path.strip("/"))


def gerar_link_afiliado(link_original):
    link_original = str(link_original or "").strip()

    if not link_original:
        return ""

    if link_afiliado_valido(link_original):
        return link_original
    # O permalink comum nunca é convertido artificialmente em afiliado.
    # O meli.la deve ser obtido no fluxo oficial do portal Mercado Livre.
    return ""
