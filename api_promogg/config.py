from pathlib import Path


API_PREFIX = "/api/v1"
APP_TITLE = "Promogg API"
CATALOGO_PUBLICO_PATH = Path("catalogo_publico/ofertas.json")

ALLOWED_ORIGINS = [
    "http://localhost:8501",
    "http://localhost:8503",
    "http://127.0.0.1:8501",
    "http://127.0.0.1:8503",
    "https://promogg.com.br",
]


def validar_allowed_origins(origins):
    if "*" in origins:
        raise RuntimeError("CORS wildcard não permitido na configuração padrão da API.")
