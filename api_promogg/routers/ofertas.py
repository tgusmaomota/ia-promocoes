from fastapi import APIRouter, Query, Request

from api_promogg.catalogo import listar_categorias, listar_ofertas, obter_oferta
from api_promogg.errors import request_id_from


router = APIRouter(tags=["ofertas"])


@router.get("/ofertas")
def ofertas(
    request: Request,
    categoria: str | None = None,
    q: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    itens, total, limit, offset = listar_ofertas(categoria=categoria, q=q, limit=limit, offset=offset)
    return {
        "data": itens,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": total,
        },
        "request_id": request_id_from(request),
    }


@router.get("/ofertas/{oferta_id}")
def oferta_detalhe(oferta_id: str, request: Request):
    return {
        "data": obter_oferta(oferta_id),
        "request_id": request_id_from(request),
    }


@router.get("/categorias")
def categorias(request: Request):
    return {
        "data": listar_categorias(),
        "request_id": request_id_from(request),
    }

