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


def test_auth_experimental_producao_com_rbac_ligado_continua_404(monkeypatch, tmp_path):
    _auth_db_env(monkeypatch, tmp_path)
    monkeypatch.setenv(constants.ENV_AUTH_EXPERIMENTAL_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_RBAC_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_PRODUCTION)
    _reload_security()
    client = _client_for_current_env()

    assert client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "senha"}).status_code == 404
    assert client.get("/api/v1/auth/me", params={"session_id": "ses_inexistente"}).status_code == 404
    assert client.post("/api/v1/auth/logout", json={"session_id": "ses_inexistente"}).status_code == 404
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": "token"}).status_code == 404


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
    assert login_data["access_credential"] is None
    assert "refresh_token" not in login_data
    assert constants.COOKIE_REFRESH_TOKEN in login.cookies
    refresh_token = login.cookies.get(constants.COOKIE_REFRESH_TOKEN)

    me = client.get("/api/v1/auth/me", params={"session_id": login_data["session_id"]})
    assert me.status_code == 200
    assert me.json()["data"]["user"]["email"] == "user@example.com"
    assert me.json()["data"]["session"]["id"] == login_data["session_id"]
    assert me.json()["data"]["jwt_issued"] is False

    refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh.status_code == 200
    assert refresh.json()["data"]["status"] == "rotated"
    assert refresh.json()["data"]["jwt_issued"] is False
    assert refresh.json()["data"]["access_credential"] is None
    assert "refresh_token" not in refresh.json()["data"]

    logout = client.post("/api/v1/auth/logout", json={"session_id": login_data["session_id"]})
    assert logout.status_code == 200
    assert logout.json()["data"]["logged_out"] is True


def test_auth_experimental_development_com_rbac_desligado_mantem_fluxo_atual(monkeypatch, tmp_path):
    _auth_db_env(monkeypatch, tmp_path)
    monkeypatch.setenv(constants.ENV_AUTH_EXPERIMENTAL_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_RBAC_ENABLED, "false")
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_DEVELOPMENT)
    _reload_security()
    client = _client_for_current_env()

    service = criar_experimental_auth_service()
    service.criar_usuario_experimental("user@example.com", "senha-correta")

    login = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "senha-correta"})
    session_id = login.json()["data"]["session_id"]
    refresh_token = login.cookies.get(constants.COOKIE_REFRESH_TOKEN)

    assert login.status_code == 200
    assert client.get("/api/v1/auth/me", params={"session_id": session_id}).status_code == 200
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token}).status_code == 200
    assert client.post("/api/v1/auth/logout", json={"session_id": session_id}).status_code == 200


def test_auth_experimental_development_com_rbac_ligado_exige_sessao_valida(monkeypatch, tmp_path):
    _auth_db_env(monkeypatch, tmp_path)
    monkeypatch.setenv(constants.ENV_AUTH_EXPERIMENTAL_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_RBAC_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_DEVELOPMENT)
    _reload_security()
    client = _client_for_current_env()

    service = criar_experimental_auth_service()
    service.criar_usuario_experimental("user@example.com", "senha-correta")
    login = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "senha-correta"})
    session_id = login.json()["data"]["session_id"]

    assert client.get("/api/v1/auth/me", params={"session_id": session_id}).status_code == 200
    assert client.post("/api/v1/auth/logout", json={"session_id": session_id}).status_code == 200
    assert client.get("/api/v1/auth/me", params={"session_id": session_id}).status_code == 401
    assert client.post("/api/v1/auth/logout", json={"session_id": session_id}).status_code == 401


def test_auth_experimental_development_com_rbac_ligado_nega_sessao_invalida(monkeypatch, tmp_path):
    _auth_db_env(monkeypatch, tmp_path)
    monkeypatch.setenv(constants.ENV_AUTH_EXPERIMENTAL_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_RBAC_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_DEVELOPMENT)
    _reload_security()
    client = _client_for_current_env()

    assert client.get("/api/v1/auth/me", params={"session_id": "ses_inexistente"}).status_code == 401
    assert client.post("/api/v1/auth/logout", json={"session_id": "ses_inexistente"}).status_code == 401


@pytest.mark.parametrize("status", ["disabled", "locked"])
def test_auth_experimental_development_com_rbac_ligado_nega_usuario_inativo_ou_bloqueado(
    monkeypatch, tmp_path, status
):
    _auth_db_env(monkeypatch, tmp_path)
    monkeypatch.setenv(constants.ENV_AUTH_EXPERIMENTAL_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_RBAC_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_DEVELOPMENT)
    _reload_security()
    client = _client_for_current_env()

    service = criar_experimental_auth_service()
    user = service.criar_usuario_experimental(f"{status}@example.com", "senha-correta")
    login = client.post("/api/v1/auth/login", json={"email": f"{status}@example.com", "password": "senha-correta"})
    session_id = login.json()["data"]["session_id"]
    refresh_token = login.cookies.get(constants.COOKIE_REFRESH_TOKEN)

    service.repository.conn.execute("UPDATE users SET status = ? WHERE id = ?", (status, user.id))
    service.repository.conn.commit()

    assert client.get("/api/v1/auth/me", params={"session_id": session_id}).status_code == 401
    assert client.post("/api/v1/auth/logout", json={"session_id": session_id}).status_code == 401
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token}).status_code == 401


def test_login_senha_errada_retorna_erro_generico(monkeypatch, tmp_path):
    _auth_db_env(monkeypatch, tmp_path)
    monkeypatch.setenv(constants.ENV_AUTH_EXPERIMENTAL_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_DEVELOPMENT)
    _reload_security()
    client = _client_for_current_env()

    service = criar_experimental_auth_service()
    service.criar_usuario_experimental("user@example.com", "senha-correta")

    response = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "senha-errada"})

    assert response.status_code == 401
    assert constants.COOKIE_REFRESH_TOKEN not in response.cookies
    assert "senha" not in response.text.lower()


def test_refresh_rotaciona_cookie_e_reuso_revoga_sessao(monkeypatch, tmp_path):
    _auth_db_env(monkeypatch, tmp_path)
    monkeypatch.setenv(constants.ENV_AUTH_EXPERIMENTAL_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_DEVELOPMENT)
    _reload_security()
    client = _client_for_current_env()

    service = criar_experimental_auth_service()
    service.criar_usuario_experimental("user@example.com", "senha-correta")
    login = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "senha-correta"})
    session_id = login.json()["data"]["session_id"]
    old_refresh = login.cookies.get(constants.COOKIE_REFRESH_TOKEN)

    rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert rotated.status_code == 200
    new_refresh = rotated.cookies.get(constants.COOKIE_REFRESH_TOKEN)
    assert new_refresh
    assert new_refresh != old_refresh

    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reused.status_code == 401
    assert client.get("/api/v1/auth/me", params={"session_id": session_id}).status_code == 401


def test_refresh_nao_aceita_token_em_query_string(monkeypatch, tmp_path):
    _auth_db_env(monkeypatch, tmp_path)
    monkeypatch.setenv(constants.ENV_AUTH_EXPERIMENTAL_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_DEVELOPMENT)
    _reload_security()
    client = _client_for_current_env()

    response = client.post("/api/v1/auth/refresh?refresh_token=texto-puro-url")

    assert response.status_code == 400


def test_logout_revoga_sessao_e_limpa_cookie(monkeypatch, tmp_path):
    _auth_db_env(monkeypatch, tmp_path)
    monkeypatch.setenv(constants.ENV_AUTH_EXPERIMENTAL_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_DEVELOPMENT)
    _reload_security()
    client = _client_for_current_env()

    service = criar_experimental_auth_service()
    service.criar_usuario_experimental("user@example.com", "senha-correta")
    login = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "senha-correta"})
    session_id = login.json()["data"]["session_id"]

    logout = client.post("/api/v1/auth/logout", json={"session_id": session_id})

    assert logout.status_code == 200
    assert logout.json()["data"]["logged_out"] is True
    set_cookie = logout.headers["set-cookie"].lower()
    assert constants.COOKIE_REFRESH_TOKEN in set_cookie
    assert "max-age=0" in set_cookie
    assert client.get("/api/v1/auth/me", params={"session_id": session_id}).status_code == 401


def test_me_nao_expoe_campos_sensiveis(monkeypatch, tmp_path):
    _auth_db_env(monkeypatch, tmp_path)
    monkeypatch.setenv(constants.ENV_AUTH_EXPERIMENTAL_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_DEVELOPMENT)
    _reload_security()
    client = _client_for_current_env()

    service = criar_experimental_auth_service()
    service.criar_usuario_experimental("user@example.com", "senha-correta")
    login = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "senha-correta"})

    response = client.get("/api/v1/auth/me", params={"session_id": login.json()["data"]["session_id"]})
    data = response.json()["data"]
    serialized = str(data).lower()

    assert response.status_code == 200
    assert "password" not in serialized
    assert "hash" not in serialized
    assert "refresh" not in serialized


def test_login_emite_access_credential_quando_jwt_experimental_ligado(monkeypatch, tmp_path):
    _auth_db_env(monkeypatch, tmp_path)
    monkeypatch.setenv(constants.ENV_AUTH_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_AUTH_EXPERIMENTAL_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_JWT_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_JWT_SIGNING_KEY, "secret-dev-only")
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_DEVELOPMENT)
    _reload_security()
    client = _client_for_current_env()

    service = criar_experimental_auth_service()
    service.criar_usuario_experimental("user@example.com", "senha-correta")

    response = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "senha-correta"})
    data = response.json()["data"]

    assert response.status_code == 200
    assert data["jwt_issued"] is True
    assert data["access_credential"]["type"] == "jwt"
    assert data["access_credential"]["value"].count(".") == 2
    assert "refresh_token" not in data


def test_csrf_experimental_bloqueia_refresh_sem_header(monkeypatch, tmp_path):
    _auth_db_env(monkeypatch, tmp_path)
    monkeypatch.setenv(constants.ENV_AUTH_EXPERIMENTAL_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_CSRF_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_DEVELOPMENT)
    _reload_security()
    client = _client_for_current_env()

    service = criar_experimental_auth_service()
    service.criar_usuario_experimental("user@example.com", "senha-correta")
    login = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "senha-correta"})

    assert constants.COOKIE_CSRF_TOKEN in login.cookies
    blocked = client.post("/api/v1/auth/refresh")
    allowed = client.post(
        "/api/v1/auth/refresh",
        headers={settings.CSRF_HEADER_NAME: login.cookies.get(constants.COOKIE_CSRF_TOKEN)},
    )

    assert blocked.status_code == 403
    assert allowed.status_code == 200


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
