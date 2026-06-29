import base64
import importlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from api_promogg.security import constants, feature_flags, settings


def _reload_jwt_modules():
    importlib.reload(settings)
    importlib.reload(feature_flags)
    from api_promogg.auth import cookies, jwt_provider

    importlib.reload(cookies)
    importlib.reload(jwt_provider)
    return cookies, jwt_provider


def _decode_payload(token: str) -> dict:
    payload = token.split(".")[1]
    padded = payload + "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))


def test_jwt_provider_nao_ativo_por_padrao(monkeypatch):
    for env_name in constants.ENV_VARS:
        monkeypatch.delenv(env_name, raising=False)
    _cookies, jwt_provider = _reload_jwt_modules()

    provider = jwt_provider.ExperimentalJWTProvider()

    assert provider.is_enabled() is False
    with pytest.raises(RuntimeError):
        provider.issue_access_credential(subject="usr_1", session_id="ses_1", signing_key="secret")


def test_jwt_claims_validas_sem_emitir_token(monkeypatch):
    monkeypatch.delenv(constants.ENV_JWT_ENABLED, raising=False)
    monkeypatch.setenv(constants.ENV_JWT_ISSUER, "promogg-test")
    monkeypatch.setenv(constants.ENV_JWT_AUDIENCE, "promogg-admin-test")
    _cookies, jwt_provider = _reload_jwt_modules()

    provider = jwt_provider.ExperimentalJWTProvider(access_ttl_seconds=600)
    now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    claims = provider.build_access_claims(
        subject="usr_123",
        session_id="ses_123",
        roles=["Administrador"],
        permissions=["system:admin"],
        private_claims={"scope": "experimental"},
        now=now,
        token_id="jwt_test",
    )

    assert claims["iss"] == "promogg-test"
    assert claims["aud"] == "promogg-admin-test"
    assert claims["sub"] == "usr_123"
    assert claims["session_id"] == "ses_123"
    assert claims["iat"] == int(now.timestamp())
    assert claims["nbf"] == int(now.timestamp())
    assert claims["exp"] == int(now.timestamp()) + 600
    assert claims["jti"] == "jwt_test"
    assert claims["ver"] == constants.JWT_TOKEN_VERSION
    assert claims["roles"] == ["Administrador"]
    assert claims["permissions"] == ["system:admin"]
    assert claims["private_claims"] == {"scope": "experimental"}


def test_jwt_configuracao_padrao(monkeypatch):
    for env_name in constants.ENV_VARS:
        monkeypatch.delenv(env_name, raising=False)
    _cookies, _jwt_provider = _reload_jwt_modules()

    assert settings.JWT_ENABLED is False
    assert settings.JWT_ISSUER == "promogg-api"
    assert settings.JWT_AUDIENCE == "promogg-admin"
    assert settings.JWT_ACCESS_TTL == 900
    assert settings.JWT_REFRESH_TTL == 2_592_000
    assert settings.JWT_ALGORITHM == constants.JWT_ALGORITHM_HS256


def test_cookies_specs_seguros(monkeypatch):
    monkeypatch.setenv(constants.ENV_JWT_REFRESH_TTL, "1200")
    cookies, _jwt_provider = _reload_jwt_modules()

    refresh_cookie = cookies.build_refresh_cookie_spec("refresh-token")
    clear_cookie = cookies.build_clear_refresh_cookie_spec()

    assert refresh_cookie.name == constants.COOKIE_REFRESH_TOKEN
    assert refresh_cookie.value == "refresh-token"
    assert refresh_cookie.httponly is True
    assert refresh_cookie.secure is True
    assert refresh_cookie.samesite == "strict"
    assert refresh_cookie.path == "/api/v1/auth"
    assert refresh_cookie.max_age == 1200
    assert clear_cookie.value == ""
    assert clear_cookie.max_age == 0
    assert clear_cookie.as_response_kwargs()["httponly"] is True


def test_producao_continua_sem_emissao_de_jwt(monkeypatch):
    monkeypatch.setenv(constants.ENV_JWT_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_PRODUCTION)
    _cookies, jwt_provider = _reload_jwt_modules()

    provider = jwt_provider.ExperimentalJWTProvider()

    assert provider.is_enabled() is False
    with pytest.raises(RuntimeError):
        provider.issue_access_credential(subject="usr_1", session_id="ses_1", signing_key="secret")


def test_feature_flag_jwt_desabilitada_impede_emissao(monkeypatch):
    monkeypatch.setenv(constants.ENV_JWT_ENABLED, "false")
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_DEVELOPMENT)
    _cookies, jwt_provider = _reload_jwt_modules()

    provider = jwt_provider.ExperimentalJWTProvider()

    assert provider.is_enabled() is False
    with pytest.raises(RuntimeError):
        provider.issue_access_credential(subject="usr_1", session_id="ses_1", signing_key="secret")


def test_jwt_experimental_emite_somente_quando_chamado_explicitamente(monkeypatch):
    monkeypatch.setenv(constants.ENV_JWT_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_DEVELOPMENT)
    _cookies, jwt_provider = _reload_jwt_modules()

    provider = jwt_provider.ExperimentalJWTProvider()
    credential = provider.issue_access_credential(
        subject="usr_1",
        session_id="ses_1",
        signing_key="secret",
        roles=["Operador"],
        permissions=["workers:run"],
    )

    assert credential.credential_type == "jwt"
    assert credential.value.count(".") == 2
    payload = _decode_payload(credential.value)
    assert payload["sub"] == "usr_1"
    assert payload["session_id"] == "ses_1"
    assert payload["roles"] == ["Operador"]
    assert payload["permissions"] == ["workers:run"]


def test_nenhuma_rota_utiliza_jwt_ou_cookies_experimentais():
    route_files = (
        Path("api_promogg/main.py"),
        Path("api_promogg/routers/auth.py"),
        Path("api_promogg/routers/health.py"),
        Path("api_promogg/routers/ofertas.py"),
    )
    forbidden_markers = (
        "jwt_provider",
        "ExperimentalJWTProvider",
        "issue_access_credential",
        "build_refresh_cookie_spec",
        "set_cookie",
    )

    for path in route_files:
        content = path.read_text(encoding="utf-8")
        for marker in forbidden_markers:
            assert marker not in content, f"{path} nao deve usar {marker}"
