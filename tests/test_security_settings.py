import importlib

from api_promogg.security import constants


def _reload_security_modules():
    from api_promogg.security import feature_flags, settings, validators

    importlib.reload(settings)
    importlib.reload(feature_flags)
    importlib.reload(validators)
    return settings, feature_flags, validators


def test_security_settings_valores_padrao(monkeypatch):
    for env_name in constants.ENV_VARS:
        monkeypatch.delenv(env_name, raising=False)

    settings, _feature_flags, _validators = _reload_security_modules()

    assert settings.AUTH_ENABLED is False
    assert settings.AUTH_EXPERIMENTAL_ENABLED is False
    assert settings.PROMOGG_ENV == constants.ENVIRONMENT_PRODUCTION
    assert settings.MFA_ENABLED is False
    assert settings.JWT_ENABLED is False
    assert settings.JWT_ISSUER == "promogg-api"
    assert settings.JWT_AUDIENCE == "promogg-admin"
    assert settings.JWT_ACCESS_TTL == 900
    assert settings.JWT_REFRESH_TTL == 2_592_000
    assert settings.JWT_ALGORITHM == constants.JWT_ALGORITHM_HS256
    assert settings.RBAC_ENABLED is False
    assert settings.AUDIT_ENABLED is True
    assert settings.MAX_LOGIN_ATTEMPTS == 5
    assert settings.LOCKOUT_MINUTES == 15
    assert settings.ACCESS_TOKEN_TTL == 900
    assert settings.REFRESH_TOKEN_TTL == 2_592_000
    assert settings.PASSWORD_MIN_LENGTH == 12
    assert settings.PASSWORD_REQUIRE_COMPLEXITY is True
    assert "https://promogg.com.br" in settings.CORS_ALLOWED_ORIGINS
    assert "localhost" in settings.ALLOWED_HOSTS


def test_security_settings_le_variaveis_de_ambiente(monkeypatch):
    monkeypatch.setenv(constants.ENV_AUTH_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_AUTH_EXPERIMENTAL_ENABLED, "1")
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_DEVELOPMENT)
    monkeypatch.setenv(constants.ENV_MFA_ENABLED, "yes")
    monkeypatch.setenv(constants.ENV_JWT_ENABLED, "on")
    monkeypatch.setenv(constants.ENV_JWT_ISSUER, "promogg-test")
    monkeypatch.setenv(constants.ENV_JWT_AUDIENCE, "promogg-admin-test")
    monkeypatch.setenv(constants.ENV_JWT_ACCESS_TTL, "300")
    monkeypatch.setenv(constants.ENV_JWT_REFRESH_TTL, "7200")
    monkeypatch.setenv(constants.ENV_JWT_ALGORITHM, constants.JWT_ALGORITHM_HS256)
    monkeypatch.setenv(constants.ENV_RBAC_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_AUDIT_ENABLED, "false")
    monkeypatch.setenv(constants.ENV_MAX_LOGIN_ATTEMPTS, "7")
    monkeypatch.setenv(constants.ENV_LOCKOUT_MINUTES, "30")
    monkeypatch.setenv(constants.ENV_ACCESS_TOKEN_TTL, "600")
    monkeypatch.setenv(constants.ENV_REFRESH_TOKEN_TTL, "86400")
    monkeypatch.setenv(constants.ENV_PASSWORD_MIN_LENGTH, "14")
    monkeypatch.setenv(constants.ENV_PASSWORD_REQUIRE_COMPLEXITY, "false")
    monkeypatch.setenv(constants.ENV_CORS_ALLOWED_ORIGINS, "https://admin.promogg.com.br, http://localhost:3000")
    monkeypatch.setenv(constants.ENV_ALLOWED_HOSTS, "admin.promogg.com.br, localhost")

    settings, _feature_flags, _validators = _reload_security_modules()

    assert settings.AUTH_ENABLED is True
    assert settings.AUTH_EXPERIMENTAL_ENABLED is True
    assert settings.PROMOGG_ENV == constants.ENVIRONMENT_DEVELOPMENT
    assert settings.MFA_ENABLED is True
    assert settings.JWT_ENABLED is True
    assert settings.JWT_ISSUER == "promogg-test"
    assert settings.JWT_AUDIENCE == "promogg-admin-test"
    assert settings.JWT_ACCESS_TTL == 300
    assert settings.JWT_REFRESH_TTL == 7200
    assert settings.JWT_ALGORITHM == constants.JWT_ALGORITHM_HS256
    assert settings.RBAC_ENABLED is True
    assert settings.AUDIT_ENABLED is False
    assert settings.MAX_LOGIN_ATTEMPTS == 7
    assert settings.LOCKOUT_MINUTES == 30
    assert settings.ACCESS_TOKEN_TTL == 600
    assert settings.REFRESH_TOKEN_TTL == 86_400
    assert settings.PASSWORD_MIN_LENGTH == 14
    assert settings.PASSWORD_REQUIRE_COMPLEXITY is False
    assert settings.CORS_ALLOWED_ORIGINS == ("https://admin.promogg.com.br", "http://localhost:3000")
    assert settings.ALLOWED_HOSTS == ("admin.promogg.com.br", "localhost")


def test_feature_flags_usam_settings(monkeypatch):
    monkeypatch.setenv(constants.ENV_AUTH_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_AUTH_EXPERIMENTAL_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_RBAC_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_MFA_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_JWT_ENABLED, "true")

    _settings, feature_flags, _validators = _reload_security_modules()

    assert feature_flags.auth_enabled()
    assert feature_flags.auth_experimental_enabled()
    assert feature_flags.rbac_enabled()
    assert feature_flags.mfa_enabled()
    assert feature_flags.jwt_enabled()


def test_validadores_reutilizaveis(monkeypatch):
    monkeypatch.setenv(constants.ENV_PASSWORD_MIN_LENGTH, "12")
    monkeypatch.setenv(constants.ENV_PASSWORD_REQUIRE_COMPLEXITY, "true")
    monkeypatch.setenv(constants.ENV_CORS_ALLOWED_ORIGINS, "https://admin.promogg.com.br")
    monkeypatch.setenv(constants.ENV_ALLOWED_HOSTS, "admin.promogg.com.br,localhost")
    _settings, _feature_flags, validators = _reload_security_modules()

    assert validators.normalize_email(" User@Example.COM ") == "user@example.com"
    assert validators.validate_email("user@example.com")
    assert not validators.validate_email("user@@example.com")
    assert validators.validate_password("SenhaForte!123")
    assert not validators.validate_password("senha-fraca")
    assert validators.validate_password("senha-fraca", min_length=6, require_complexity=False)
    assert validators.validate_username("operador_01")
    assert not validators.validate_username("ab")
    assert validators.validate_cors_origin("https://admin.promogg.com.br")
    assert not validators.validate_cors_origin("https://evil.example")
    assert validators.validate_allowed_host("admin.promogg.com.br:443")
    assert validators.validate_allowed_host("localhost")
    assert not validators.validate_allowed_host("evil.example")
    assert validators.validate_request_id("req_teste_2c")
    assert not validators.validate_request_id("req invalido")
    assert validators.validate_max_input_size("abc", 3)
    assert not validators.validate_max_input_size("abcd", 3)


def test_constantes_centralizadas():
    assert constants.PERMISSION_OFFERS_READ in constants.PERMISSIONS
    assert constants.ROLE_ADMIN in constants.ROLES
    assert constants.ERROR_AUTH_DISABLED in constants.ERROR_CODES
    assert constants.AUDIT_AUTH_LOGIN_SUCCESS in constants.AUDIT_EVENTS
    assert constants.HEADER_REQUEST_ID in constants.HTTP_HEADERS
    assert constants.COOKIE_REFRESH_TOKEN in constants.COOKIE_NAMES
    assert constants.ENV_AUTH_ENABLED in constants.ENV_VARS
    assert constants.ENVIRONMENT_DEVELOPMENT in constants.ENVIRONMENTS
    assert constants.ENV_JWT_ISSUER in constants.ENV_VARS
    assert constants.JWT_ALGORITHM_HS256 in constants.JWT_ALLOWED_ALGORITHMS
