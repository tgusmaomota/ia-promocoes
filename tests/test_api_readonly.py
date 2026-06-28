import json
import subprocess
import sys

from fastapi.testclient import TestClient

from api_promogg.config import ALLOWED_ORIGINS, CATALOGO_PUBLICO_PATH
from api_promogg.main import app


client = TestClient(app)


def _primeiro_item_id():
    dados = json.loads(CATALOGO_PUBLICO_PATH.read_text(encoding="utf-8"))
    return dados["ofertas"][0]["item_id"]


def _assert_erro_padronizado(response, code):
    payload = response.json()
    assert "error" in payload
    assert payload["error"]["code"] == code
    assert payload["error"]["request_id"]


def test_health_retorna_200():
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_detalhada_retorna_200():
    response = client.get("/api/v1/health/detalhada")
    assert response.status_code == 200


def test_ofertas_retorna_200():
    response = client.get("/api/v1/ofertas")
    assert response.status_code == 200
    assert isinstance(response.json()["data"], list)


def test_ofertas_limit_acima_do_maximo_retorna_erro_padronizado():
    response = client.get("/api/v1/ofertas?limit=101")
    assert response.status_code == 400
    _assert_erro_padronizado(response, "VALIDATION_ERROR")


def test_ofertas_offset_negativo_retorna_erro_padronizado():
    response = client.get("/api/v1/ofertas?offset=-1")
    assert response.status_code == 400
    _assert_erro_padronizado(response, "VALIDATION_ERROR")


def test_oferta_existente_retorna_200():
    response = client.get(f"/api/v1/ofertas/{_primeiro_item_id()}")
    assert response.status_code == 200
    assert response.json()["data"]["item_id"] == _primeiro_item_id()


def test_oferta_inexistente_retorna_not_found():
    response = client.get("/api/v1/ofertas/OFERTA_INEXISTENTE")
    assert response.status_code == 404
    _assert_erro_padronizado(response, "NOT_FOUND")


def test_categorias_retorna_lista():
    response = client.get("/api/v1/categorias")
    assert response.status_code == 200
    assert isinstance(response.json()["data"], list)


def test_x_request_id_e_preservado():
    response = client.get("/api/v1/health", headers={"X-Request-ID": "req_teste_2c"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req_teste_2c"
    assert response.json()["request_id"] == "req_teste_2c"


def test_resposta_de_erro_contem_request_id():
    response = client.get("/api/v1/ofertas/OFERTA_INEXISTENTE", headers={"X-Request-ID": "req_erro_2c"})
    assert response.status_code == 404
    assert response.json()["error"]["request_id"] == "req_erro_2c"


def test_headers_de_seguranca_sao_aplicados():
    response = client.get("/api/v1/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "microphone=()" in response.headers["Permissions-Policy"]
    assert response.headers["Cache-Control"] == "no-store"


def test_cors_default_nao_usa_wildcard():
    assert "*" not in ALLOWED_ORIGINS


def test_cli_api_teste_funciona():
    resultado = subprocess.run(
        [sys.executable, "ia_promocoes.py", "api-teste"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert resultado.returncode == 0
    assert "API_TESTE=ok" in resultado.stdout
    assert "rotas somente leitura" in resultado.stdout
