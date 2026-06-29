import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from api_promogg.auth.audit import AuditEvent, sanitize_event
from api_promogg.auth.db import conectar_auth_db
from api_promogg.auth.migrations import inicializar_schema
from api_promogg.auth.models import Permission, RefreshToken, Role, Session, User
from api_promogg.auth.tokens import compare_token, hash_token


def utc_now_iso():
    return datetime.now(UTC).isoformat()


def novo_id(prefixo):
    return f"{prefixo}_{uuid4().hex}"


def inicializar_banco_auth(path: str | Path | None = None):
    conn = conectar_auth_db(path)
    inicializar_schema(conn)
    return conn


class AuthRepository:
    def __init__(self, conn):
        self.conn = conn

    def criar_usuario(self, email: str, password_hash: str, status: str = "pending") -> User:
        if not email or not password_hash:
            raise ValueError("E-mail e password_hash são obrigatórios.")
        user_id = novo_id("usr")
        email_normalizado = email.strip().lower()
        now = utc_now_iso()
        self.conn.execute(
            """
            INSERT INTO users (id, email, password_hash, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, email_normalizado, password_hash, status, now, now),
        )
        self.conn.commit()
        return self.buscar_usuario_por_email(email_normalizado)

    def buscar_usuario_por_email(self, email: str) -> User | None:
        row = self.conn.execute(
            "SELECT id, email, password_hash, status, created_at, updated_at FROM users WHERE email = ?",
            (email.strip().lower(),),
        ).fetchone()
        return _user_from_row(row) if row else None

    def buscar_usuario_por_id(self, user_id: str) -> User | None:
        row = self.conn.execute(
            "SELECT id, email, password_hash, status, created_at, updated_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return _user_from_row(row) if row else None

    def criar_sessao(self, user_id: str, expires_in_minutes: int = 60, ip_hash=None, user_agent_hash=None) -> Session:
        session_id = novo_id("ses")
        now_dt = datetime.now(UTC)
        expires_at = (now_dt + timedelta(minutes=expires_in_minutes)).isoformat()
        self.conn.execute(
            """
            INSERT INTO sessions (id, user_id, status, created_at, last_seen_at, expires_at, ip_hash, user_agent_hash)
            VALUES (?, ?, 'active', ?, ?, ?, ?, ?)
            """,
            (session_id, user_id, now_dt.isoformat(), now_dt.isoformat(), expires_at, ip_hash, user_agent_hash),
        )
        self.conn.commit()
        return self.buscar_sessao(session_id)

    def buscar_sessao(self, session_id: str) -> Session | None:
        row = self.conn.execute(
            """
            SELECT id, user_id, status, created_at, expires_at, revoked_at, revocation_reason
            FROM sessions WHERE id = ?
            """,
            (session_id,),
        ).fetchone()
        return _session_from_row(row) if row else None

    def buscar_refresh_token_por_token(self, token: str) -> RefreshToken | None:
        rows = self.conn.execute(
            """
            SELECT id, session_id, token_hash, family_id, previous_token_id,
                   used_at, expires_at, revoked_at, reuse_detected_at
            FROM refresh_tokens
            """
        ).fetchall()
        for row in rows:
            if compare_token(token, row["token_hash"]):
                return _refresh_from_row(row)
        return None

    def registrar_refresh_token(
        self,
        session_id: str,
        token: str,
        family_id: str | None = None,
        previous_token_id: str | None = None,
        expires_in_days: int = 30,
    ):
        token_id = novo_id("rt")
        family_id = family_id or novo_id("rtf")
        expires_at = (datetime.now(UTC) + timedelta(days=expires_in_days)).isoformat()
        token_hash = hash_token(token)
        self.conn.execute(
            """
            INSERT INTO refresh_tokens (id, session_id, token_hash, family_id, previous_token_id, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (token_id, session_id, token_hash, family_id, previous_token_id, expires_at),
        )
        self.conn.commit()
        return {
            "id": token_id,
            "session_id": session_id,
            "token_hash": token_hash,
            "family_id": family_id,
            "previous_token_id": previous_token_id,
            "expires_at": expires_at,
        }

    def marcar_refresh_token_usado(self, token_id: str):
        now = utc_now_iso()
        self.conn.execute("UPDATE refresh_tokens SET used_at = ? WHERE id = ?", (now, token_id))
        self.conn.commit()

    def marcar_reuso_refresh_token(self, token_id: str):
        now = utc_now_iso()
        row = self.conn.execute("SELECT family_id FROM refresh_tokens WHERE id = ?", (token_id,)).fetchone()
        if not row:
            return
        self.conn.execute("UPDATE refresh_tokens SET reuse_detected_at = ? WHERE id = ?", (now, token_id))
        self.conn.execute(
            "UPDATE refresh_tokens SET revoked_at = ? WHERE family_id = ? AND revoked_at IS NULL",
            (now, row["family_id"]),
        )
        self.conn.commit()

    def revogar_familia_refresh(self, family_id: str):
        now = utc_now_iso()
        self.conn.execute(
            "UPDATE refresh_tokens SET revoked_at = ? WHERE family_id = ? AND revoked_at IS NULL",
            (now, family_id),
        )
        self.conn.commit()

    def revogar_sessao(self, session_id: str, reason: str = "manual"):
        now = utc_now_iso()
        self.conn.execute(
            """
            UPDATE sessions
            SET status = 'revoked', revoked_at = ?, revocation_reason = ?
            WHERE id = ?
            """,
            (now, reason, session_id),
        )
        self.conn.execute(
            "UPDATE refresh_tokens SET revoked_at = ? WHERE session_id = ? AND revoked_at IS NULL",
            (now, session_id),
        )
        self.conn.commit()
        return self.buscar_sessao(session_id)

    def registrar_evento_auditoria(self, event: AuditEvent | dict):
        sanitized = sanitize_event(event)
        metadata = sanitized.get("metadata") or {}
        self.conn.execute(
            """
            INSERT INTO audit_events (
                id, created_at, actor_user_id, actor_session_id, action, permission,
                resource_type, resource_id, result, reason, request_id, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sanitized.get("id") or novo_id("aud"),
                sanitized.get("created_at") or utc_now_iso(),
                sanitized.get("actor_user_id"),
                sanitized.get("actor_session_id"),
                sanitized.get("action"),
                sanitized.get("permission"),
                sanitized.get("resource_type"),
                sanitized.get("resource_id"),
                sanitized.get("result"),
                sanitized.get("reason"),
                sanitized.get("request_id"),
                json.dumps(metadata, ensure_ascii=False, sort_keys=True),
            ),
        )
        self.conn.commit()
        return sanitized

    def listar_papeis(self) -> list[Role]:
        rows = self.conn.execute("SELECT id, name, description, is_system FROM roles ORDER BY name").fetchall()
        return [Role(**dict(row)) for row in rows]

    def listar_permissoes(self) -> list[Permission]:
        rows = self.conn.execute(
            "SELECT id, code, description, risk_level, requires_mfa FROM permissions ORDER BY code"
        ).fetchall()
        return [Permission(**dict(row)) for row in rows]


def _user_from_row(row) -> User:
    return User(**dict(row))


def _session_from_row(row) -> Session:
    return Session(**dict(row))


def _refresh_from_row(row) -> RefreshToken:
    return RefreshToken(**dict(row))
