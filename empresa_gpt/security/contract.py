"""Inert security contract stubs for EmpresaGPT Phase 2."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol


class SecurityError(Exception):
    """Base error for security contract violations."""


@dataclass(frozen=True)
class AuditEvent:
    """Sanitized audit event contract."""

    actor_id: str | None
    action: str
    resource: str
    result: str
    context: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SecurityDecision:
    """Authorization decision with deny-by-default semantics."""

    allowed: bool = False
    reason: str = "disabled_by_default"


class SecurityContract(Protocol):
    """Contract for authorization and sanitized audit."""

    def authorize(self, actor_id: str | None, action: str, resource: str) -> SecurityDecision:
        """Return an authorization decision without side effects."""

    def sanitize_audit_event(self, event: AuditEvent) -> AuditEvent:
        """Return an audit event safe for logs or storage."""

