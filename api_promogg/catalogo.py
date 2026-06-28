import json
import re
from functools import lru_cache
from unicodedata import normalize

from api_promogg.config import CATALOGO_PUBLICO_PATH
from api_promogg.errors import NotFoundError, ValidationApiError


def _texto(valor):
    return " ".join(str(valor or "").split())


def _slug(valor):
    texto = normalize("NFKD", _texto(valor).lower())
    texto = "".join(ch for ch in texto if not 0x300 <= ord(ch) <= 0x36F)
    texto = re.sub(r"[^a-z0-9]+", "-", texto).strip("-")
    return texto or "ofertas"


@lru_cache(maxsize=1)
def carregar_catalogo():
    try:
        dados = json.loads(CATALOGO_PUBLICO_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationApiError("Catálogo público indisponível.") from exc
    ofertas = dados.get("ofertas")
    if not isinstance(ofertas, list):
        raise ValidationApiError("Catálogo público inválido.")
    return dados


def listar_ofertas(categoria=None, q=None, limit=20, offset=0):
    limit = min(max(int(limit), 1), 100)
    offset = max(int(offset), 0)
    categoria_normalizada = _texto(categoria).lower()
    termo = _texto(q).lower()
    ofertas = carregar_catalogo().get("ofertas", [])

    filtradas = []
    for oferta in ofertas:
        if categoria_normalizada:
            categoria_oferta = _texto(oferta.get("categoria")).lower()
            caminho = _texto(oferta.get("categoria_caminho")).lower()
            if categoria_normalizada not in {categoria_oferta, caminho, _slug(categoria_oferta), _slug(caminho)}:
                continue
        if termo:
            texto_busca = " ".join((
                _texto(oferta.get("titulo")),
                _texto(oferta.get("categoria")),
                _texto(oferta.get("item_id")),
                _texto(oferta.get("oferta_id")),
            )).lower()
            if termo not in texto_busca:
                continue
        filtradas.append(oferta)

    return filtradas[offset:offset + limit], len(filtradas), limit, offset


def obter_oferta(oferta_id):
    alvo = _texto(oferta_id)
    for oferta in carregar_catalogo().get("ofertas", []):
        if alvo in {_texto(oferta.get("oferta_id")), _texto(oferta.get("item_id"))}:
            return oferta
    raise NotFoundError()


def listar_categorias():
    totais = {}
    nomes = {}
    for oferta in carregar_catalogo().get("ofertas", []):
        nome = _texto(oferta.get("categoria")) or "Ofertas"
        slug = _slug(nome)
        totais[slug] = totais.get(slug, 0) + 1
        nomes.setdefault(slug, nome)
    return [
        {"id": slug, "nome": nomes[slug], "total_ofertas": totais[slug]}
        for slug in sorted(totais, key=lambda item: nomes[item].lower())
    ]

