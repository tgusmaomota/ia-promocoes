"""Helpers para especificacao de cookies seguros.

As funcoes deste modulo nao escrevem cookies em respostas HTTP. Elas retornam
contratos reutilizaveis para uma integracao futura.
"""

from __future__ import annotations

from dataclasses import dataclass

from api_promogg.security import constants, settings


@dataclass(frozen=True)
class CookieSpec:
    name: str
    value: str
    httponly: bool
    secure: bool
    samesite: str
    path: str
    max_age: int

    def as_response_kwargs(self) -> dict:
        return {
            "key": self.name,
            "value": self.value,
            "httponly": self.httponly,
            "secure": self.secure,
            "samesite": self.samesite,
            "path": self.path,
            "max_age": self.max_age,
        }


def build_refresh_cookie_spec(
    refresh_token: str,
    *,
    max_age: int | None = None,
    secure: bool = True,
    samesite: str = "strict",
    path: str = "/api/v1/auth",
    name: str = constants.COOKIE_REFRESH_TOKEN,
) -> CookieSpec:
    if not refresh_token:
        raise ValueError("refresh_token obrigatorio.")
    return CookieSpec(
        name=name,
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path=path,
        max_age=max_age if max_age is not None else settings.JWT_REFRESH_TTL,
    )


def build_clear_refresh_cookie_spec(
    *,
    secure: bool = True,
    samesite: str = "strict",
    path: str = "/api/v1/auth",
    name: str = constants.COOKIE_REFRESH_TOKEN,
) -> CookieSpec:
    return CookieSpec(
        name=name,
        value="",
        httponly=True,
        secure=secure,
        samesite=samesite,
        path=path,
        max_age=0,
    )


def build_csrf_cookie_spec(
    csrf_token: str,
    *,
    max_age: int | None = None,
    secure: bool = True,
    samesite: str = "strict",
    path: str = "/api/v1/auth",
    name: str | None = None,
) -> CookieSpec:
    if not csrf_token:
        raise ValueError("csrf_token obrigatorio.")
    return CookieSpec(
        name=name or settings.CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=secure,
        samesite=samesite,
        path=path,
        max_age=max_age if max_age is not None else settings.CSRF_TOKEN_TTL,
    )
