from fastapi import APIRouter, Request

from api_promogg.catalogo import carregar_catalogo, listar_categorias
from api_promogg.errors import request_id_from


router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request):
    return {
        "data": {
            "ok": True,
            "service": "promogg-api",
            "version": "v1",
        },
        "request_id": request_id_from(request),
    }


@router.get("/health/detalhada")
def health_detalhada(request: Request):
    catalogo = carregar_catalogo()
    return {
        "data": {
            "estado": "ONLINE",
            "catalogo_publico": "ok",
            "total_ofertas": len(catalogo.get("ofertas", [])),
            "total_categorias": len(listar_categorias()),
            "fonte": "catalogo_publico/ofertas.json",
            "autenticacao": "nao_implementada",
        },
        "request_id": request_id_from(request),
    }

