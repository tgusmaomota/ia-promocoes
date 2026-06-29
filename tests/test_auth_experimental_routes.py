import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api_promogg.auth.service import criar_experimental_auth_service
from api_promogg.security import constants, feature_flags, settings


@pytest.fixture(autouse=True)
def reload_security_after_env_changes(monkeypatch):
    yield
    importlib.reload(settings)
    importlib.reload(feature_flags)
    from api_promogg.routers import auth as auth_router
    from api_promogg import main as main_module

    importlib.reload(auth_router)
    importlib.reload(main_module)


def _reload_security():
    importlib.reload(settings)
    importlib.reload(feature_flags)


def _client_for_current_env():
    from api_promogg.routers import auth as auth_router
    from api_promogg import main as main_module

    importlib.reload(auth_router)
    main_module = importlib.reload(main_module)
    return TestClient(main_module.app)


def _auth_db_env(monkeypatch, tmp_path):
    auth_db = tmp_path / "auth_experimental.sqlite"
    monkeypatch.setenv("PROMOGG_AUTH_DB_PATH", str(auth_db))
    return auth_db


def test_auth_experimental_flag_desligada_retorna_404(monkeypatch, tmp_path):
    _auth_db_env(monkeypatch, tmp_path)
    monkeypatch.delenv(constants.ENV_AUTH_EXPERIMENTAL_ENABLED, raising=False)
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_DEVELOPMENT)
    _reload_security()
    client = _client_for_current_env()

    response = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "senha"})

    assert response.status_code == 404


@pytest.mark.parametrize("env_name", [constants.ENVIRONMENT_PRODUCTION, constants.ENVIRONMENT_STAGING, "qa"])
def test_auth_experimental_ambiente_nao_development_retorna_404(monkeypatch, tmp_path, env_name):
    _auth_db_env(monkeypatch, tmp_path)
    monkeypatch.setenv(constants.ENV_AUTH_EXPERIMENTAL_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, env_name)
    _reload_security()
    client = _client_for_current_env()

    response = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "senha"})

    assert response.status_code == 404


def test_auth_experimental_development_com_flag_desligada_retorna_404(monkeypatch, tmp_path):
    _auth_db_env(monkeypatch, tmp_path)
    monkeypatch.setenv(constants.ENV_AUTH_EXPERIMENTAL_ENABLED, "false")
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_DEVELOPMENT)
    _reload_security()
    client = _client_for_current_env()

    response = client.get("/api/v1/auth/me", params={"session_id": "ses_inexistente"})

    assert response.status_code == 404


def test_auth_experimental_development_com_flag_ligada_disponibiliza_rotas(monkeypatch, tmp_path):
    _auth_db_env(monkeypatch, tmp_path)
    monkeypatch.setenv(constants.ENV_AUTH_EXPERIMENTAL_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_DEVELOPMENT)
    _reload_security()
    client = _client_for_current_env()

    service = criar_experimental_auth_service()
    service.criar_usuario_experimental("user@example.com", "senha-correta")

    login = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "senha-correta"})
    assert login.status_code == 200
    login_data = login.json()["data"]
    assert login_data["jwt_issued"] is False
    assert login_data["access_token"] is None
    assert login_data["refresh_token"]

    me = client.get("/api/v1/auth/me", params={"session_id": login_data["session_id"]})
    assert me.status_code == 200
    assert me.json()["data"]["user"]["email"] == "user@example.com"
    assert me.json()["data"]["jwt_issued"] is False

    refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": login_data["refresh_token"]})
    assert refresh.status_code == 200
    assert refresh.json()["data"]["status"] == "rotated"
    assert refresh.json()["data"]["jwt_issued"] is False
    assert refresh.json()["data"]["access_token"] is None

    logout = client.post("/api/v1/auth/logout", json={"session_id": login_data["session_id"]})
    assert logout.status_code == 200
    assert logout.json()["data"]["logged_out"] is True


def test_rotas_read_only_continuam_sem_autenticacao(monkeypatch, tmp_path):
    _auth_db_env(monkeypatch, tmp_path)
    monkeypatch.setenv(constants.ENV_AUTH_EXPERIMENTAL_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_DEVELOPMENT)
    _reload_security()
    client = _client_for_current_env()

    health = client.get("/api/v1/health")
    ofertas = client.get("/api/v1/ofertas")
    categorias = client.get("/api/v1/categorias")

    assert health.status_code == 200
    assert ofertas.status_code == 200
    assert categorias.status_code == 200


def test_auth_experimental_nao_utiliza_banco_operacional(monkeypatch, tmp_path):
    _auth_db_env(monkeypatch, tmp_path)
    monkeypatch.setenv(constants.ENV_AUTH_EXPERIMENTAL_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_DEVELOPMENT)
    _reload_security()
    client = _client_for_current_env()

    operational_db = Path("banco.db")
    before_mtime = operational_db.stat().st_mtime_ns if operational_db.exists() else None

    service = criar_experimental_auth_service()
    service.criar_usuario_experimental("user@example.com", "senha-correta")
    response = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "senha-correta"})

    after_mtime = operational_db.stat().st_mtime_ns if operational_db.exists() else None
    assert response.status_code == 200
    assert before_mtime == after_mtime
