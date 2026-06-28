from typing import Any, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    ok: bool
    service: str
    version: str


class HealthDetalhadaResponse(BaseModel):
    estado: str
    catalogo_publico: str
    total_ofertas: int
    total_categorias: int
    fonte: str
    autenticacao: str


class OfertaPublica(BaseModel):
    oferta_id: str
    item_id: Optional[str] = None
    titulo: str
    categoria: str
    preco: Optional[float] = None
    preco_formatado: Optional[str] = None
    link: Optional[str] = None
    imagem_url: Optional[str] = None
    produto_url: Optional[str] = None
    plataforma: Optional[str] = None


class CategoriaPublica(BaseModel):
    id: str
    nome: str
    total_ofertas: int


class Pagination(BaseModel):
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    total: int = Field(ge=0)


class Envelope(BaseModel):
    data: Any
    request_id: str


class PaginatedEnvelope(BaseModel):
    data: list[Any]
    pagination: Pagination
    request_id: str

