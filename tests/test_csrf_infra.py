import importlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

from api_promogg.security import constants, settings


def _reload_security_modules():
    importlib.reload(settings)
    from api_promogg.auth import cookies
    from api_promogg.security import csrf, origin, session_security

    importlib.reload(cookies)
    importlib.reload(csrf)
    importlib.reload(origin)
    importlib.reload(session_security)
    return cookies, csrf, origin, session_security


def test_csrf_gera_e_valida_token(monkeypatch):
    monkeypatch.setenv(constants.ENV_CSRF_TOKEN_TTL, "120")
    _cookies, csrf, _origin, _session_security = _reload_security_modules()

    token = csrf.generate_csrf_token()

    assert len(token.value) >= 40
    assert csrf.validate_csrf_token(token, token.value)


def test_csrf_token_invalido(monkeypatch):
    monkeypatch.setenv(constants.ENV_CSRF_TOKEN_TTL, "120")
    _cookies, csrf, _origin, _session_security = _reload_security_modules()
    token = csrf.generate_csrf_token()

    assert not csrf.validate_csrf_token(token, "outro-token")
    assert not csrf.constant_time_compare(token.value, "")


def test_csrf_token_expirado(monkeypatch):
    monkeypatch.setenv(constants.ENV_CSRF_TOKEN_TTL, "60")
    _cookies, csrf, _origin, _session_security = _reload_security_modules()
    token = csrf.generate_csrf_token()
    future = token.expires_at + timedelta(seconds=1)

    assert csrf.is_csrf_token_expired(token, now=future)
    assert not csrf.validate_csrf_token(token, token.value, now=future)


def test_origin_host_referer_development(monkeypatch):
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_DEVELOPMENT)
    _cookies, _csrf, origin, _session_security = _reload_security_modules()

    assert origin.allowed_domains_for_environment() == ("localhost", "127.0.0.1")
    assert origin.validate_origin("http://localhost:8501")
    assert origin.validate_origin("http://127.0.0.1:8001")
    assert not origin.validate_origin("https://promogg.com.br")
    assert origin.validate_host("localhost:8501")
    assert origin.validate_referer("http://localhost:8501/auth")
    assert origin.validate_referer(None, required=False)
    assert not origin.validate_referer(None, required=True)


def test_origin_host_referer_production(monkeypatch):
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_PRODUCTION)
    monkeypatch.setenv(constants.ENV_ALLOWED_HOSTS, "promogg.com.br,admin.promogg.com.br")
    _cookies, _csrf, origin, _session_security = _reload_security_modules()

    assert origin.validate_origin("https://promogg.com.br")
    assert origin.validate_host("admin.promogg.com.br")
    assert origin.validate_referer("https://promogg.com.br/painel", required=True)
    assert not origin.validate_origin("http://localhost:8501")
    assert not origin.validate_host("evil.example")
    assert not origin.validate_referer("https://evil.example/painel", required=True)


def test_origin_ambiente_desconhecido_bloqueia(monkeypatch):
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, "qa")
    _cookies, _csrf, origin, _session_security = _reload_security_modules()

    assert origin.allowed_domains_for_environment() == ()
    assert not origin.validate_origin("https://promogg.com.br")
    assert not origin.validate_host("promogg.com.br")


def test_sessao_regenerada_e_protecao_session_fixation(monkeypatch):
    monkeypatch.setenv(constants.ENV_SESSION_ROTATION_ENABLED, "true")
    _cookies, _csrf, _origin, session_security = _reload_security_modules()

    plan = session_security.regenerate_session("ses_antiga", reason="post_login")

    assert plan.old_session_id == "ses_antiga"
    assert plan.new_session_id.startswith("ses_")
    assert plan.new_session_id != "ses_antiga"
    assert plan.old_session_invalidated is True
    assert session_security.prevents_session_fixation(plan)


def test_politicas_de_timeout_de_sessao(monkeypatch):
    monkeypatch.setenv(constants.ENV_SESSION_IDLE_TIMEOUT, "300")
    monkeypatch.setenv(constants.ENV_SESSION_ABSOLUTE_TIMEOUT, "3600")
    _cookies, _csrf, _origin, session_security = _reload_security_modules()
    policy = session_security.build_session_timeout_policy()
    base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

    assert policy.idle_timeout_seconds == 300
    assert policy.absolute_timeout_seconds == 3600
    assert session_security.is_session_idle_expired(base, now=base + timedelta(seconds=301), policy=policy)
    assert not session_security.is_session_idle_expired(base, now=base + timedelta(seconds=299), policy=policy)
    assert session_security.is_session_absolute_expired(base, now=base + timedelta(seconds=3600), policy=policy)


def test_cookies_passivos_refresh_e_csrf(monkeypatch):
    monkeypatch.setenv(constants.ENV_CSRF_COOKIE_NAME, "promogg_csrf_test")
    monkeypatch.setenv(constants.ENV_CSRF_TOKEN_TTL, "600")
    cookies, csrf, _origin, _session_security = _reload_security_modules()
    token = csrf.generate_csrf_token()

    refresh_cookie = cookies.build_refresh_cookie_spec("refresh-token")
    csrf_cookie = cookies.build_csrf_cookie_spec(token.value)

    assert refresh_cookie.httponly is True
    assert refresh_cookie.secure is True
    assert csrf_cookie.name == "promogg_csrf_test"
    assert csrf_cookie.httponly is False
    assert csrf_cookie.secure is True
    assert csrf_cookie.max_age == 600


def test_producao_continua_sem_cookies_reais(monkeypatch):
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_PRODUCTION)
    cookies, csrf, _origin, _session_security = _reload_security_modules()

    token = csrf.generate_csrf_token()
    spec = cookies.build_csrf_cookie_spec(token.value)

    assert spec.as_response_kwargs()["key"] == settings.CSRF_COOKIE_NAME
    assert spec.secure is True
    assert not hasattr(spec, "set_cookie")


def test_nenhuma_rota_usa_csrf_cookies_ou_session_security():
    route_files = (
        Path("api_promogg/main.py"),
        Path("api_promogg/routers/auth.py"),
        Path("api_promogg/routers/health.py"),
        Path("api_promogg/routers/ofertas.py"),
    )
    forbidden_markers = (
        "security.csrf",
        "generate_csrf_token",
        "validate_csrf_token",
        "build_csrf_cookie_spec",
        "set_cookie",
        "delete_cookie",
        "session_security",
        "plan_session_rotation",
    )

    for path in route_files:
        content = path.read_text(encoding="utf-8")
        for marker in forbidden_markers:
            assert marker not in content, f"{path} nao deve usar {marker}"
