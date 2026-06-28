from pathlib import Path

from api_promogg.auth.audit import AuditEvent, MASK
from api_promogg.auth.password import hash_password
from api_promogg.auth.repository import AuthRepository, inicializar_banco_auth
from api_promogg.auth.tokens import generate_opaque_token


def test_auth_persistence_experimental_em_banco_temporario(tmp_path):
    auth_db = tmp_path / "auth_teste.auth.sqlite"
    operational_db = Path("banco.db")
    before_mtime = operational_db.stat().st_mtime_ns if operational_db.exists() else None

    conn = inicializar_banco_auth(auth_db)
    repo = AuthRepository(conn)

    assert auth_db.exists()
    tabelas = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }
    assert {
        "users",
        "roles",
        "permissions",
        "user_roles",
        "sessions",
        "refresh_tokens",
        "audit_events",
    }.issubset(tabelas)

    senha_pura = "senha-super-secreta"
    password_hash = hash_password(senha_pura)
    user = repo.criar_usuario("Admin@Example.com", password_hash, status="active")
    assert user.email == "admin@example.com"
    assert user.password_hash.startswith("$argon2id$")

    raw_db = auth_db.read_bytes()
    assert senha_pura.encode("utf-8") not in raw_db

    session = repo.criar_sessao(user.id, expires_in_minutes=15, ip_hash="ip_hash", user_agent_hash="ua_hash")
    assert session.status == "active"

    refresh_token = generate_opaque_token()
    refresh = repo.registrar_refresh_token(session.id, refresh_token)
    assert refresh["token_hash"].startswith("sha256:")
    assert refresh_token not in refresh["token_hash"]
    assert refresh_token.encode("utf-8") not in auth_db.read_bytes()

    revoked = repo.revogar_sessao(session.id, reason="teste")
    assert revoked.status == "revoked"
    assert revoked.revocation_reason == "teste"

    event = AuditEvent(
        action="auth.login.failure",
        result="failure",
        actor_user_id=user.id,
        actor_session_id=session.id,
        metadata={"password": "nao-logar", "token": "nao-logar", "safe": "ok"},
    )
    sanitized = repo.registrar_evento_auditoria(event)
    assert sanitized["metadata"]["password"] == MASK
    assert sanitized["metadata"]["token"] == MASK
    assert b"nao-logar" not in auth_db.read_bytes()

    roles = repo.listar_papeis()
    permissions = repo.listar_permissoes()
    assert "Administrador" in {role.name for role in roles}
    assert "Somente leitura" in {role.name for role in roles}
    assert "offers:read" in {permission.code for permission in permissions}
    assert "system:admin" in {permission.code for permission in permissions}

    assert not conn.execute("SELECT 1 FROM users WHERE email LIKE '%admin@promogg%'").fetchone()

    after_mtime = operational_db.stat().st_mtime_ns if operational_db.exists() else None
    assert before_mtime == after_mtime
