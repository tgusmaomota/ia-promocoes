"""Inert AI contract stubs for EmpresaGPT Phase 2."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol


class AIError(Exception):
    """Base error for AI provider contract violations."""


@dataclass(frozen=True)
class AIRequest:
    """Prompt request after caller-side sanitization."""

    prompt: str
    context: Mapping[str, str] = field(default_factory=dict)
    provider: str = "ollama"
    model: str | None = None


@dataclass(frozen=True)
class AIResponse:
    """AI response treated as advisory output."""

    text: str
    provider: str
    model: str | None = None
    safe_to_persist: bool = False


class AIContract(Protocol):
    """Contract for local-first AI generation."""

    def generate(self, request: AIRequest) -> AIResponse:
        """Generate advisory text without bypassing business rules."""

