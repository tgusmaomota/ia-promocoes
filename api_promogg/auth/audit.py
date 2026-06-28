from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


SENSITIVE_KEYS = {
    "authorization",
    "api_key",
    "apiKey",
    "cookie",
    "password",
    "password_hash",
    "refresh_token",
    "secret",
    "token",
}

MASK = "[REDACTED]"


@dataclass
class AuditEvent:
    action: str
    result: str
    actor_user_id: str | None = None
    actor_session_id: str | None = None
    permission: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    reason: str | None = None
    request_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: f"aud_{uuid4().hex}")
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


def sanitize_value(value: Any):
    if isinstance(value, dict):
        return sanitize_mapping(value)
    if isinstance(value, list):
        return [sanitize_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize_value(item) for item in value)
    return value


def sanitize_mapping(data: dict[str, Any]) -> dict[str, Any]:
    sanitized = {}
    for key, value in data.items():
        if _is_sensitive_key(key):
            sanitized[key] = MASK
        else:
            sanitized[key] = sanitize_value(value)
    return sanitized


def sanitize_event(event: AuditEvent | dict[str, Any]) -> dict[str, Any]:
    data = asdict(event) if isinstance(event, AuditEvent) else dict(event)
    return sanitize_mapping(data)


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return normalized in {item.lower() for item in SENSITIVE_KEYS} or any(
        marker in normalized
        for marker in ("password", "token", "cookie", "authorization", "secret", "api_key")
    )
