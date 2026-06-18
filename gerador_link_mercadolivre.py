import os
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from dotenv import load_dotenv


load_dotenv()


def link_afiliado_valido(link):
    link = str(link or "").strip()
    if not link:
        return False

    if "meli.la/" in link:
        return True

    affiliate_id = os.getenv("MERCADO_LIVRE_AFFILIATE_ID", "").strip()
    return bool(affiliate_id and "mercadolivre.com" in link)


def gerar_link_afiliado(link_original):
    link_original = str(link_original or "").strip()

    if not link_original:
        return ""

    if "meli.la/" in link_original:
        return link_original

    affiliate_id = os.getenv("MERCADO_LIVRE_AFFILIATE_ID", "").strip()

    if not affiliate_id or "mercadolivre.com" not in link_original:
        return ""

    partes = urlparse(link_original)
    query = dict(parse_qsl(partes.query, keep_blank_values=True))
    query.setdefault("utm_source", "ia-promocoes")
    query.setdefault("utm_medium", "affiliate")
    query.setdefault("utm_campaign", affiliate_id)

    return urlunparse(partes._replace(query=urlencode(query)))
