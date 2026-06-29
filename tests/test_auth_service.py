import json
from pathlib import Path

import pytest

from api_promogg.auth.repository import AuthRepository, inicializar_banco_auth
from api_promogg.auth.service import AuthError, ExperimentalAuthService, GENERIC_LOGIN_ERROR


@pytest.fixture()
def auth_service(tmp_path):
    conn = inicializar_banco_auth(tmp_path / "auth_service.auth.sqlite")
    return ExperimentalAuthService(AuthRepository(conn)), conn, tmp_path / "auth_service.auth.sqlite"


def test_cria_usuario_experimental_sem_expor_hash(auth_service):
    service, conn, _db_path = auth_service
    user = service.criar_usuario_experimental("User@Example.com", "senha-forte")

    assert user.email == "user@example.com"
    assert not hasattr(user, "password_hash")
    row = conn.execute("SELECT password_hash FROM users WHERE id = ?", (user.id,)).fetchone()
    assert row["password_hash"].startswith("$argon2id$")


def test_senha_correta_autentica_e_cria_sessao(auth_service):
    service, conn, _db_path = auth_service
    service.criar_usuario_experimental("user@example.com", "senha-correta")

    result = service.autenticar_credenciais("user@example.com", "senha-correta")

    assert result.authenticated
    assert result.session.session_id.startswith("ses_")
    assert result.session.refresh_token
    assert not hasattr(result.session.user, "password_hash")
    assert conn.execute("SELECT 1 FROM sessions WHERE id = ?", (result.session.session_id,)).fetchone()


def test_senha_incorreta_falha_com_erro_generico(auth_service):
    service, _conn, _db_path = auth_service
    service.criar_usuario_experimental("user@example.com", "senha-correta")

    with pytest.raises(AuthError) as exc:
        service.autenticar_credenciais("user@example.com", "errada")

    assert exc.value.message == GENERIC_LOGIN_ERROR


def test_email_inexistente_falha_com_erro_generico(auth_service):
    service, _conn, _db_path = auth_service

    with pytest.raises(AuthError) as exc:
        service.autenticar_credenciais("ninguem@example.com", "qualquer")

    assert exc.value.message == GENERIC_LOGIN_ERROR


def test_usuario_inativo_ou_bloqueado_nao_autentica(auth_service):
    service, _conn, _db_path = auth_service
    service.criar_usuario_experimental("inactive@example.com", "senha", status="disabled")
    service.criar_usuario_experimental("locked@example.com", "senha", status="locked")

    for email in ("inactive@example.com", "locked@example.com"):
        with pytest.raises(AuthError) as exc:
            service.autenticar_credenciais(email, "senha")
        assert exc.value.message == GENERIC_LOGIN_ERROR


def test_refresh_token_retorna_uma_vez_e_fica_apenas_hash(auth_service):
    service, conn, db_path = auth_service
    service.criar_usuario_experimental("user@example.com", "senha-correta")
    result = service.autenticar_credenciais("user@example.com", "senha-correta")

    refresh_token = result.session.refresh_token
    rows = conn.execute("SELECT token_hash FROM refresh_tokens").fetchall()
    assert len(rows) == 1
    assert rows[0]["token_hash"].startswith("sha256:")
    assert refresh_token not in rows[0]["token_hash"]
    assert refresh_token.encode("utf-8") not in db_path.read_bytes()


def test_rotacao_de_refresh_funciona(auth_service):
    service, conn, _db_path = auth_service
    service.criar_usuario_experimental("user@example.com", "senha-correta")
    auth = service.autenticar_credenciais("user@example.com", "senha-correta")

    refresh = service.rotacionar_refresh_token(auth.session.refresh_token)

    assert refresh.status == "rotated"
    assert refresh.session_id == auth.session.session_id
    assert refresh.refresh_token
    assert refresh.refresh_token != auth.session.refresh_token
    assert conn.execute("SELECT COUNT(*) AS total FROM refresh_tokens").fetchone()["total"] == 2


def test_reuso_de_refresh_antigo_revoga_sessao(auth_service):
    service, conn, _db_path = auth_service
    service.criar_usuario_experimental("user@example.com", "senha-correta")
    auth = service.autenticar_credenciais("user@example.com", "senha-correta")
    service.rotacionar_refresh_token(auth.session.refresh_token)

    reused = service.rotacionar_refresh_token(auth.session.refresh_token)

    assert reused.status == "reused"
    session = conn.execute("SELECT status, revocation_reason FROM sessions WHERE id = ?", (auth.session.session_id,)).fetchone()
    assert session["status"] == "revoked"
    assert session["revocation_reason"] == "refresh_reuse"


def test_logout_revoga_sessao(auth_service):
    service, conn, _db_path = auth_service
    service.criar_usuario_experimental("user@example.com", "senha-correta")
    auth = service.autenticar_credenciais("user@example.com", "senha-correta")

    assert service.logout(auth.session.session_id)
    session = conn.execute("SELECT status, revocation_reason FROM sessions WHERE id = ?", (auth.session.session_id,)).fetchone()
    assert session["status"] == "revoked"
    assert session["revocation_reason"] == "logout"


def test_auditoria_registra_eventos_sanitizados(auth_service):
    service, conn, db_path = auth_service
    service.criar_usuario_experimental("user@example.com", "senha-correta")
    with pytest.raises(AuthError):
        service.autenticar_credenciais("user@example.com", "senha-incorreta")

    rows = conn.execute("SELECT action, metadata_json FROM audit_events ORDER BY created_at").fetchall()
    assert {row["action"] for row in rows} >= {"auth.user.created", "auth.login.failure"}
    metadados = [json.loads(row["metadata_json"]) for row in rows]
    assert any(item.get("password") == "[REDACTED]" for item in metadados)
    assert b"senha-incorreta" not in db_path.read_bytes()
    assert b"senha-correta" not in db_path.read_bytes()


def test_service_nao_toca_banco_operacional(auth_service):
    service, _conn, _db_path = auth_service
    operational_db = Path("banco.db")
    before_mtime = operational_db.stat().st_mtime_ns if operational_db.exists() else None

    service.criar_usuario_experimental("user@example.com", "senha-correta")
    service.autenticar_credenciais("user@example.com", "senha-correta")

    after_mtime = operational_db.stat().st_mtime_ns if operational_db.exists() else None
    assert before_mtime == after_mtime
