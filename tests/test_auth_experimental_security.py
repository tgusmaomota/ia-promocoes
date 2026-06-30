import importlib
from pathlib import Path

from fastapi.testclient import TestClient

from api_promogg.auth.service import criar_experimental_auth_service
from api_promogg.security import constants, feature_flags, settings


AUTH_ENDPOINTS = (
    ("post", "/api/v1/auth/login", {"json": {"email": "user@example.com", "password": "senha"}}),
    ("post", "/api/v1/auth/logout", {"json": {"session_id": "ses_teste"}}),
    ("post", "/api/v1/auth/refresh", {"json": {"refresh_token": "refresh_teste"}}),
    ("get", "/api/v1/auth/me", {"params": {"session_id": "ses_teste"}}),
)


def _reload_security_and_app():
    importlib.reload(settings)
    importlib.reload(feature_flags)

    from api_promogg.routers import auth as auth_router
    from api_promogg import main as main_module

    importlib.reload(auth_router)
    main_module = importlib.reload(main_module)
    return TestClient(main_module.app), main_module.app


def _call(client, method, path, kwargs):
    return getattr(client, method)(path, **kwargs)


def test_auth_experimental_default_fail_safe_404(monkeypatch):
    monkeypatch.delenv(constants.ENV_AUTH_EXPERIMENTAL_ENABLED, raising=False)
    monkeypatch.delenv(constants.ENV_PROMOGG_ENV, raising=False)
    client, _app = _reload_security_and_app()

    for method, path, kwargs in AUTH_ENDPOINTS:
        response = _call(client, method, path, kwargs)
        assert response.status_code == 404
        assert response.status_code not in {401, 403, 500}
        assert "set-cookie" not in response.headers


def test_auth_experimental_producao_com_flag_ligada_continua_404(monkeypatch):
    monkeypatch.setenv(constants.ENV_AUTH_EXPERIMENTAL_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_PRODUCTION)
    client, _app = _reload_security_and_app()

    for method, path, kwargs in AUTH_ENDPOINTS:
        response = _call(client, method, path, kwargs)
        assert response.status_code == 404
        assert response.status_code not in {401, 403, 500}
        assert "set-cookie" not in response.headers


def test_auth_experimental_ambiente_desconhecido_com_flag_ligada_continua_404(monkeypatch):
    monkeypatch.setenv(constants.ENV_AUTH_EXPERIMENTAL_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, "qa")
    client, _app = _reload_security_and_app()

    for method, path, kwargs in AUTH_ENDPOINTS:
        response = _call(client, method, path, kwargs)
        assert response.status_code == 404
        assert response.status_code not in {401, 403, 500}


def test_auth_experimental_development_com_flag_desligada_continua_404(monkeypatch):
    monkeypatch.setenv(constants.ENV_AUTH_EXPERIMENTAL_ENABLED, "false")
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_DEVELOPMENT)
    client, _app = _reload_security_and_app()

    for method, path, kwargs in AUTH_ENDPOINTS:
        response = _call(client, method, path, kwargs)
        assert response.status_code == 404
        assert response.status_code not in {401, 403, 500}


def test_auth_experimental_development_com_flag_ligada_fica_disponivel(monkeypatch, tmp_path):
    monkeypatch.setenv("PROMOGG_AUTH_DB_PATH", str(tmp_path / "auth_security.sqlite"))
    monkeypatch.setenv(constants.ENV_AUTH_EXPERIMENTAL_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_DEVELOPMENT)
    client, app = _reload_security_and_app()

    service = criar_experimental_auth_service()
    service.criar_usuario_experimental("user@example.com", "senha-correta")

    auth_paths = sorted(getattr(route, "path", "") for route in app.routes if getattr(route, "path", "").startswith("/api/v1/auth"))
    assert auth_paths == [
        "/api/v1/auth/login",
        "/api/v1/auth/logout",
        "/api/v1/auth/me",
        "/api/v1/auth/refresh",
    ]

    response = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "senha-correta"})
    assert response.status_code == 200
    assert response.json()["data"]["jwt_issued"] is False
    assert response.json()["data"]["access_credential"] is None
    assert "refresh_token" not in response.json()["data"]
    assert constants.COOKIE_REFRESH_TOKEN in response.cookies
    set_cookie = response.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie


def test_auth_router_nao_interfere_em_rotas_existentes(monkeypatch, tmp_path):
    monkeypatch.setenv("PROMOGG_AUTH_DB_PATH", str(tmp_path / "auth_security.sqlite"))
    monkeypatch.setenv(constants.ENV_AUTH_EXPERIMENTAL_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_DEVELOPMENT)
    client, _app = _reload_security_and_app()

    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/health/detalhada").status_code == 200
    assert client.get("/api/v1/ofertas").status_code == 200
    assert client.get("/api/v1/categorias").status_code == 200


def test_modulos_read_only_e_operacionais_nao_importam_auth_experimental():
    paths = (
        Path("api_promogg/routers/health.py"),
        Path("api_promogg/routers/ofertas.py"),
        Path("api_promogg/catalogo.py"),
        Path("ia_promocoes.py"),
        Path("gerar_site.py"),
        Path("gerar_site_publico.py"),
        Path("deploy_site.py"),
    )
    forbidden_markers = (
        "api_promogg.auth",
        "api_promogg.routers.auth",
        "criar_experimental_auth_service",
        "ExperimentalAuthService",
        "PROMOGG_AUTH_EXPERIMENTAL_ENABLED",
    )

    for path in paths:
        content = path.read_text(encoding="utf-8")
        for marker in forbidden_markers:
            assert marker not in content, f"{path} nao deve depender de {marker}"


def test_main_registra_apenas_router_auth_sem_depender_do_servico_experimental():
    content = Path("api_promogg/main.py").read_text(encoding="utf-8")

    assert "api_promogg.auth" not in content
    assert "criar_experimental_auth_service" not in content
    assert "ExperimentalAuthService" not in content
    assert "app.include_router(auth.router, prefix=API_PREFIX)" in content
