from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    id: str
    email: str
    password_hash: str
    status: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Session:
    id: str
    user_id: str
    status: str
    created_at: str
    expires_at: str
    revoked_at: str | None = None
    revocation_reason: str | None = None


@dataclass(frozen=True)
class Role:
    id: str
    name: str
    description: str
    is_system: int


@dataclass(frozen=True)
class Permission:
    id: str
    code: str
    description: str
    risk_level: str
    requires_mfa: int


@dataclass(frozen=True)
class RefreshToken:
    id: str
    session_id: str
    token_hash: str
    family_id: str
    previous_token_id: str | None
    used_at: str | None
    expires_at: str
    revoked_at: str | None
    reuse_detected_at: str | None
