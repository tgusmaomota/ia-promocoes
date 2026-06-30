"""Contratos passivos para protecao de sessao e session fixation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from api_promogg.security import settings


@dataclass(frozen=True)
class SessionRotationPlan:
    old_session_id: str
    new_session_id: str
    rotated_at: datetime
    old_session_invalidated: bool
    reason: str


@dataclass(frozen=True)
class SessionTimeoutPolicy:
    idle_timeout_seconds: int
    absolute_timeout_seconds: int
    rotation_enabled: bool


def generate_session_id() -> str:
    return f"ses_{uuid4().hex}"


def build_session_timeout_policy(
    *,
    idle_timeout_seconds: int | None = None,
    absolute_timeout_seconds: int | None = None,
    rotation_enabled: bool | None = None,
) -> SessionTimeoutPolicy:
    idle = idle_timeout_seconds if idle_timeout_seconds is not None else settings.SESSION_IDLE_TIMEOUT
    absolute = absolute_timeout_seconds if absolute_timeout_seconds is not None else settings.SESSION_ABSOLUTE_TIMEOUT
    if idle <= 0 or absolute <= 0:
        raise ValueError("Timeouts de sessao devem ser positivos.")
    if idle > absolute:
        raise ValueError("Idle timeout nao pode ser maior que absolute timeout.")
    return SessionTimeoutPolicy(
        idle_timeout_seconds=idle,
        absolute_timeout_seconds=absolute,
        rotation_enabled=settings.SESSION_ROTATION_ENABLED if rotation_enabled is None else rotation_enabled,
    )


def plan_session_rotation(old_session_id: str, *, reason: str = "post_login") -> SessionRotationPlan:
    if not old_session_id:
        raise ValueError("old_session_id obrigatorio.")
    new_session_id = generate_session_id()
    while new_session_id == old_session_id:
        new_session_id = generate_session_id()
    return SessionRotationPlan(
        old_session_id=old_session_id,
        new_session_id=new_session_id,
        rotated_at=datetime.now(UTC),
        old_session_invalidated=True,
        reason=reason,
    )


def regenerate_session(old_session_id: str, *, reason: str = "regenerate") -> SessionRotationPlan:
    return plan_session_rotation(old_session_id, reason=reason)


def prevents_session_fixation(plan: SessionRotationPlan) -> bool:
    return bool(
        plan.old_session_id
        and plan.new_session_id
        and plan.old_session_id != plan.new_session_id
        and plan.old_session_invalidated
    )


def is_session_idle_expired(last_seen_at: datetime, *, now: datetime | None = None, policy: SessionTimeoutPolicy | None = None) -> bool:
    effective_policy = policy or build_session_timeout_policy()
    effective_now = now or datetime.now(UTC)
    return effective_now >= last_seen_at + timedelta(seconds=effective_policy.idle_timeout_seconds)


def is_session_absolute_expired(created_at: datetime, *, now: datetime | None = None, policy: SessionTimeoutPolicy | None = None) -> bool:
    effective_policy = policy or build_session_timeout_policy()
    effective_now = now or datetime.now(UTC)
    return effective_now >= created_at + timedelta(seconds=effective_policy.absolute_timeout_seconds)
