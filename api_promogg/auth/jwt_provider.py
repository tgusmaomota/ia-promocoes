"""Provider JWT experimental e interno.

Campos documentados do access token:

- issuer (`iss`): emissor configurado em `JWT_ISSUER`;
- audience (`aud`): audiencia configurada em `JWT_AUDIENCE`;
- subject (`sub`): usuario/autenticado dono da credencial;
- issued_at (`iat`): timestamp UTC de emissao;
- expires_at (`exp`): timestamp UTC de expiracao;
- not_before (`nbf`): timestamp UTC minimo para uso;
- token_id (`jti`): identificador unico da credencial;
- algoritmo permitido: `HS256`;
- versao do token (`ver`): versao logica dos contratos de claims;
- claims privadas: `session_id`, `roles`, `permissions` e metadados `private_claims`.

Este modulo nao emite tokens automaticamente e nao e usado por rotas nesta fase.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from api_promogg.auth.credentials import AccessCredential, CredentialProvider, RefreshCredential
from api_promogg.auth.tokens import generate_opaque_token
from api_promogg.security import constants, settings


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _json_b64url(data: dict) -> str:
    return _b64url(json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def _timestamp(dt: datetime) -> int:
    return int(dt.timestamp())


class ExperimentalJWTProvider(CredentialProvider):
    credential_type = "jwt"
    refresh_credential_type = "opaque_refresh"

    def __init__(
        self,
        *,
        issuer: str | None = None,
        audience: str | None = None,
        algorithm: str | None = None,
        access_ttl_seconds: int | None = None,
        refresh_ttl_seconds: int | None = None,
    ):
        self.issuer = issuer or settings.JWT_ISSUER
        self.audience = audience or settings.JWT_AUDIENCE
        self.algorithm = algorithm or settings.JWT_ALGORITHM
        self.access_ttl_seconds = access_ttl_seconds or settings.JWT_ACCESS_TTL
        self.refresh_ttl_seconds = refresh_ttl_seconds or settings.JWT_REFRESH_TTL
        if self.algorithm not in constants.JWT_ALLOWED_ALGORITHMS:
            raise ValueError(f"Algoritmo JWT nao permitido: {self.algorithm!r}")

    def is_enabled(self) -> bool:
        return settings.JWT_ENABLED and settings.PROMOGG_ENV == constants.ENVIRONMENT_DEVELOPMENT

    def build_access_claims(
        self,
        *,
        subject: str,
        session_id: str,
        roles: list[str] | tuple[str, ...] | None = None,
        permissions: list[str] | tuple[str, ...] | None = None,
        private_claims: dict | None = None,
        now: datetime | None = None,
        token_id: str | None = None,
    ) -> dict:
        issued_at = now or datetime.now(UTC)
        not_before = issued_at
        expires_at = issued_at + timedelta(seconds=self.access_ttl_seconds)
        claims = {
            "iss": self.issuer,
            "aud": self.audience,
            "sub": subject,
            "iat": _timestamp(issued_at),
            "exp": _timestamp(expires_at),
            "nbf": _timestamp(not_before),
            "jti": token_id or f"jwt_{uuid4().hex}",
            "ver": constants.JWT_TOKEN_VERSION,
            "session_id": session_id,
            "roles": list(roles or ()),
            "permissions": list(permissions or ()),
        }
        if private_claims:
            claims["private_claims"] = dict(private_claims)
        return claims

    def issue_access_credential(
        self,
        *,
        subject: str,
        session_id: str,
        signing_key: str,
        roles: list[str] | tuple[str, ...] | None = None,
        permissions: list[str] | tuple[str, ...] | None = None,
        private_claims: dict | None = None,
    ) -> AccessCredential:
        if not self.is_enabled():
            raise RuntimeError("JWT experimental desabilitado.")
        if not signing_key:
            raise ValueError("signing_key obrigatorio para emitir JWT experimental.")

        now = datetime.now(UTC)
        claims = self.build_access_claims(
            subject=subject,
            session_id=session_id,
            roles=roles,
            permissions=permissions,
            private_claims=private_claims,
            now=now,
        )
        token = encode_hs256_jwt(claims, signing_key=signing_key, algorithm=self.algorithm)
        return AccessCredential(
            value=token,
            credential_type=self.credential_type,
            subject=subject,
            issued_at=datetime.fromtimestamp(claims["iat"], UTC),
            expires_at=datetime.fromtimestamp(claims["exp"], UTC),
            not_before=datetime.fromtimestamp(claims["nbf"], UTC),
            token_id=claims["jti"],
            claims=claims,
        )

    def issue_refresh_credential(self, *, subject: str, session_id: str, **kwargs) -> RefreshCredential:
        if not self.is_enabled():
            raise RuntimeError("Credencial refresh experimental desabilitada.")
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=self.refresh_ttl_seconds)
        return RefreshCredential(
            value=generate_opaque_token(),
            credential_type=self.refresh_credential_type,
            subject=subject,
            issued_at=now,
            expires_at=expires_at,
            token_id=f"rt_{uuid4().hex}",
            cookie_name=constants.COOKIE_REFRESH_TOKEN,
            metadata={"session_id": session_id},
        )


def encode_hs256_jwt(claims: dict, *, signing_key: str, algorithm: str = constants.JWT_ALGORITHM_HS256) -> str:
    if algorithm != constants.JWT_ALGORITHM_HS256:
        raise ValueError(f"Algoritmo JWT nao permitido: {algorithm!r}")
    if not signing_key:
        raise ValueError("signing_key obrigatorio.")

    header = {"alg": algorithm, "typ": "JWT"}
    header_part = _json_b64url(header)
    payload_part = _json_b64url(claims)
    signing_input = f"{header_part}.{payload_part}".encode("ascii")
    signature = hmac.new(signing_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_part}.{payload_part}.{_b64url(signature)}"
