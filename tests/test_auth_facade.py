import importlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from api_promogg.auth.credentials import AccessCredential, RefreshCredential
from api_promogg.security import constants, feature_flags, settings


@dataclass
class FakeCredentialProvider:
    enabled: bool = True
    is_enabled_calls: int = 0
    access_calls: int = 0
    refresh_calls: int = 0

    def is_enabled(self) -> bool:
        self.is_enabled_calls += 1
        return self.enabled

    def issue_access_credential(self, *, subject: str, session_id: str, **kwargs) -> AccessCredential:
        self.access_calls += 1
        now = datetime.now(UTC)
        return AccessCredential(
            value=f"access-{self.access_calls}",
            credential_type="fake_access",
            subject=subject,
            issued_at=now,
            expires_at=now + timedelta(minutes=15),
            not_before=now,
            token_id=f"acc_{self.access_calls}",
            claims={"session_id": session_id, **kwargs},
        )

    def issue_refresh_credential(self, *, subject: str, session_id: str, **kwargs) -> RefreshCredential:
        self.refresh_calls += 1
        now = datetime.now(UTC)
        return RefreshCredential(
            value=f"refresh-{self.refresh_calls}",
            credential_type="fake_refresh",
            subject=subject,
            issued_at=now,
            expires_at=now + timedelta(days=30),
            token_id=f"ref_{self.refresh_calls}",
            cookie_name="fake_refresh_cookie",
            metadata={"session_id": session_id, **kwargs},
        )


def _reload_facade():
    importlib.reload(settings)
    importlib.reload(feature_flags)
    from api_promogg.auth import auth_facade

    importlib.reload(auth_facade)
    return auth_facade


def _enable_all_for_development(monkeypatch):
    monkeypatch.setenv(constants.ENV_AUTH_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_AUTH_EXPERIMENTAL_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_JWT_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_DEVELOPMENT)


def test_facade_emite_apenas_em_development(monkeypatch):
    _enable_all_for_development(monkeypatch)
    auth_facade = _reload_facade()
    provider = FakeCredentialProvider()
    facade = auth_facade.AuthCredentialFacade(provider)

    bundle = facade.issue_credentials(subject="usr_1", session_id="ses_1", signing_key="secret")

    assert bundle.access.subject == "usr_1"
    assert bundle.refresh.subject == "usr_1"
    assert provider.is_enabled_calls == 1
    assert provider.access_calls == 1
    assert provider.refresh_calls == 1


def test_facade_producao_nunca_emite(monkeypatch):
    monkeypatch.setenv(constants.ENV_AUTH_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_AUTH_EXPERIMENTAL_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_JWT_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_PRODUCTION)
    auth_facade = _reload_facade()
    provider = FakeCredentialProvider()
    facade = auth_facade.AuthCredentialFacade(provider)

    with pytest.raises(auth_facade.AuthFacadeError) as exc:
        facade.issue_credentials(subject="usr_1", session_id="ses_1", signing_key="secret")

    assert exc.value.code == "AUTH_ENV_NOT_ALLOWED"
    assert provider.is_enabled_calls == 0
    assert provider.access_calls == 0
    assert provider.refresh_calls == 0


@pytest.mark.parametrize(
    ("env_name", "env_value", "expected_code"),
    [
        (constants.ENV_AUTH_ENABLED, "false", "AUTH_DISABLED"),
        (constants.ENV_AUTH_EXPERIMENTAL_ENABLED, "false", "AUTH_EXPERIMENTAL_DISABLED"),
        (constants.ENV_JWT_ENABLED, "false", "JWT_DISABLED"),
    ],
)
def test_facade_nao_chama_provider_quando_flags_bloqueiam(monkeypatch, env_name, env_value, expected_code):
    _enable_all_for_development(monkeypatch)
    monkeypatch.setenv(env_name, env_value)
    auth_facade = _reload_facade()
    provider = FakeCredentialProvider()
    facade = auth_facade.AuthCredentialFacade(provider)

    with pytest.raises(auth_facade.AuthFacadeError) as exc:
        facade.issue_credentials(subject="usr_1", session_id="ses_1", signing_key="secret")

    assert exc.value.code == expected_code
    assert provider.is_enabled_calls == 0
    assert provider.access_calls == 0
    assert provider.refresh_calls == 0


def test_facade_renovacao_revoga_refresh_antigo(monkeypatch):
    _enable_all_for_development(monkeypatch)
    auth_facade = _reload_facade()
    provider = FakeCredentialProvider()
    facade = auth_facade.AuthCredentialFacade(provider)
    bundle = facade.issue_credentials(subject="usr_1", session_id="ses_1", signing_key="secret")

    renewed = facade.renew_credentials(
        refresh_credential=bundle.refresh,
        session_id="ses_1",
        signing_key="secret",
    )

    assert renewed.access.value == "access-2"
    assert renewed.refresh.value == "refresh-2"
    assert not facade.validate_refresh_credential(bundle.refresh)
    assert facade.validate_refresh_credential(renewed.refresh)
    assert provider.access_calls == 2
    assert provider.refresh_calls == 2


def test_facade_revogacao_e_validacao(monkeypatch):
    _enable_all_for_development(monkeypatch)
    auth_facade = _reload_facade()
    provider = FakeCredentialProvider()
    facade = auth_facade.AuthCredentialFacade(provider)
    bundle = facade.issue_credentials(subject="usr_1", session_id="ses_1", signing_key="secret")

    assert facade.validate_access_credential(bundle.access)
    assert facade.validate_refresh_credential(bundle.refresh)

    assert facade.revoke(bundle.access.token_id)
    assert facade.revoke(bundle.refresh.token_id)
    assert not facade.validate_access_credential(bundle.access)
    assert not facade.validate_refresh_credential(bundle.refresh)


def test_servico_interno_emite_credenciais_apenas_via_facade(monkeypatch, tmp_path):
    _enable_all_for_development(monkeypatch)
    monkeypatch.setenv("PROMOGG_AUTH_DB_PATH", str(tmp_path / "auth_facade.sqlite"))
    auth_facade = _reload_facade()

    from api_promogg.auth.service import criar_experimental_auth_service

    provider = FakeCredentialProvider()
    facade = auth_facade.AuthCredentialFacade(provider)
    service = criar_experimental_auth_service()
    service.criar_usuario_experimental("user@example.com", "senha-correta")
    auth_result = service.autenticar_credenciais("user@example.com", "senha-correta")

    bundle = service.emitir_credenciais_experimentais(auth_result.session, facade, signing_key="secret")

    assert bundle.access.subject == auth_result.session.user.id
    assert bundle.refresh.metadata["session_id"] == auth_result.session.session_id
    assert provider.access_calls == 1
    assert provider.refresh_calls == 1


def test_apenas_router_auth_experimental_usa_auth_facade_jwt_ou_cookies():
    route_files = (
        Path("api_promogg/main.py"),
        Path("api_promogg/routers/health.py"),
        Path("api_promogg/routers/ofertas.py"),
    )
    forbidden_markers = (
        "auth_facade",
        "AuthCredentialFacade",
        "issue_credentials",
        "ExperimentalJWTProvider",
        "set_cookie",
        "build_refresh_cookie_spec",
    )

    for path in route_files:
        content = path.read_text(encoding="utf-8")
        for marker in forbidden_markers:
            assert marker not in content, f"{path} nao deve usar {marker}"

    auth_content = Path("api_promogg/routers/auth.py").read_text(encoding="utf-8")
    assert "AuthCredentialFacade" in auth_content
    assert "ExperimentalJWTProvider" in auth_content
    assert "set_cookie" in auth_content
