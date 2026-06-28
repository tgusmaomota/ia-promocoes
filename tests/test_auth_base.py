from api_promogg.auth.audit import MASK, AuditEvent, sanitize_event
from api_promogg.auth.password import hash_password, verify_password
from api_promogg.auth.rbac import has_permission, permissions_for_roles, roles_have_permission
from api_promogg.auth.tokens import (
    InMemoryRefreshTokenStore,
    compare_token,
    generate_opaque_token,
    hash_token,
)


def test_password_hash_e_verify():
    password_hash = hash_password("senha-forte-de-teste")
    assert password_hash.startswith("$argon2id$")
    assert "senha-forte-de-teste" not in password_hash
    assert verify_password("senha-forte-de-teste", password_hash)


def test_password_incorreta_falha():
    password_hash = hash_password("senha-correta")
    assert not verify_password("senha-incorreta", password_hash)


def test_token_opaco_e_unico():
    token_a = generate_opaque_token()
    token_b = generate_opaque_token()
    assert token_a != token_b
    assert len(token_a) >= 40


def test_hash_de_token_nao_expoe_token_original():
    token = generate_opaque_token()
    token_hash = hash_token(token)
    assert token not in token_hash
    assert token_hash.startswith("sha256:")


def test_comparacao_segura_de_token():
    token = generate_opaque_token()
    token_hash = hash_token(token)
    assert compare_token(token, token_hash)
    assert not compare_token(generate_opaque_token(), token_hash)


def test_refresh_reuse_e_detectado():
    store = InMemoryRefreshTokenStore()
    token, record = store.issue_initial()
    rotated = store.rotate(token)
    assert rotated.status == "rotated"
    assert rotated.token
    assert rotated.record.previous_token_id == record.id

    reused = store.rotate(token)
    assert reused.status == "reused"
    assert reused.record.reuse_detected_at is not None
    assert all(item.revoked_at is not None for item in store.records if item.family_id == record.family_id)


def test_rbac_permite_e_nega_corretamente():
    assert has_permission("Administrador", "system:admin")
    assert has_permission("Operador", "workers:run")
    assert has_permission("Revisor", "offers:review")
    assert not has_permission("Somente leitura", "offers:edit")
    assert not has_permission("Analista", "secrets:manage")
    assert not has_permission("Desconhecido", "offers:read")


def test_rbac_multiplos_papeis():
    assert roles_have_permission(["Somente leitura", "Revisor"], "offers:review")
    assert not roles_have_permission(["Somente leitura", "Analista"], "roles:manage")
    assert "analytics:read" in permissions_for_roles(["Analista"])


def test_auditoria_mascara_campos_sensiveis():
    event = AuditEvent(
        action="auth.login.failure",
        result="failure",
        metadata={
            "email": "admin@example.com",
            "password": "segredo",
            "headers": {
                "Authorization": "Bearer token",
                "cookie": "refresh=abc",
            },
            "nested": {
                "api_key": "abc",
                "refresh_token": "def",
                "safe": "ok",
            },
        },
    )
    sanitized = sanitize_event(event)
    assert sanitized["metadata"]["email"] == "admin@example.com"
    assert sanitized["metadata"]["password"] == MASK
    assert sanitized["metadata"]["headers"]["Authorization"] == MASK
    assert sanitized["metadata"]["headers"]["cookie"] == MASK
    assert sanitized["metadata"]["nested"]["api_key"] == MASK
    assert sanitized["metadata"]["nested"]["refresh_token"] == MASK
    assert sanitized["metadata"]["nested"]["safe"] == "ok"
