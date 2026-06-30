import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api_promogg.auth.password import hash_password
from api_promogg.auth.rbac import PersistentRBACAuthorizer
from api_promogg.auth.repository import AuthRepository, inicializar_banco_auth
from api_promogg.security import constants, feature_flags, settings


@pytest.fixture(autouse=True)
def reload_security_after_test():
    yield
    importlib.reload(settings)
    importlib.reload(feature_flags)


def _repo(tmp_path):
    conn = inicializar_banco_auth(tmp_path / "rbac_experimental.sqlite")
    return AuthRepository(conn)


def _criar_usuario(repo, email="user@example.com", status="active"):
    return repo.criar_usuario(email, hash_password("senha-forte"), status=status)


def test_usuario_sem_papel_nao_tem_permissao(tmp_path):
    repo = _repo(tmp_path)
    user = _criar_usuario(repo)
    authorizer = PersistentRBACAuthorizer(repo, enabled=True)

    assert authorizer.list_user_permissions(user.id) == set()
    assert not authorizer.has_permission(user.id, "offers:read")


def test_revisor_pode_revisar_ofertas(tmp_path):
    repo = _repo(tmp_path)
    user = _criar_usuario(repo)
    assert repo.atribuir_papel_usuario(user.id, "Revisor")
    authorizer = PersistentRBACAuthorizer(repo, enabled=True)

    assert "Revisor" in {role.name for role in repo.listar_papeis_usuario(user.id)}
    assert authorizer.has_permission(user.id, "offers:review")
    assert authorizer.has_all_permissions(user.id, {"offers:read", "offers:review"})


def test_somente_leitura_nao_pode_publicar(tmp_path):
    repo = _repo(tmp_path)
    user = _criar_usuario(repo)
    assert repo.atribuir_papel_usuario(user.id, "Somente leitura")
    authorizer = PersistentRBACAuthorizer(repo, enabled=True)

    assert authorizer.has_permission(user.id, "offers:read")
    assert not authorizer.has_permission(user.id, "offers:publish")
    assert not authorizer.has_any_permission(user.id, {"offers:publish", "site:deploy"})


def test_administrador_tem_permissoes_administrativas(tmp_path):
    repo = _repo(tmp_path)
    user = _criar_usuario(repo)
    assert repo.atribuir_papel_usuario(user.id, "Administrador")
    authorizer = PersistentRBACAuthorizer(repo, enabled=True)

    assert authorizer.has_permission(user.id, "system:admin")
    assert authorizer.has_permission(user.id, "roles:manage")
    assert authorizer.has_permission(user.id, "secrets:manage")


def test_permissao_inexistente_e_papel_removido_negam(tmp_path):
    repo = _repo(tmp_path)
    user = _criar_usuario(repo)
    assert repo.atribuir_papel_usuario(user.id, "Revisor")
    authorizer = PersistentRBACAuthorizer(repo, enabled=True)

    assert not authorizer.has_permission(user.id, "permissao:inexistente")
    assert repo.remover_papel_usuario(user.id, "Revisor")
    assert not authorizer.has_permission(user.id, "offers:review")


def test_usuario_inativo_ou_bloqueado_nega(tmp_path):
    repo = _repo(tmp_path)
    disabled = _criar_usuario(repo, "disabled@example.com", status="disabled")
    locked = _criar_usuario(repo, "locked@example.com", status="locked")
    repo.atribuir_papel_usuario(disabled.id, "Administrador")
    repo.atribuir_papel_usuario(locked.id, "Administrador")
    authorizer = PersistentRBACAuthorizer(repo, enabled=True)

    assert not authorizer.has_permission(disabled.id, "system:admin")
    assert not authorizer.has_permission(locked.id, "system:admin")


def test_producao_continua_sem_rbac_ativo(monkeypatch, tmp_path):
    repo = _repo(tmp_path)
    user = _criar_usuario(repo)
    repo.atribuir_papel_usuario(user.id, "Administrador")
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_PRODUCTION)
    monkeypatch.setenv(constants.ENV_RBAC_ENABLED, "true")
    importlib.reload(settings)
    importlib.reload(feature_flags)
    authorizer = PersistentRBACAuthorizer(repo)

    assert not authorizer.has_permission(user.id, "system:admin")


def test_rbac_exige_auth_experimental_ligada(monkeypatch, tmp_path):
    repo = _repo(tmp_path)
    user = _criar_usuario(repo)
    repo.atribuir_papel_usuario(user.id, "Administrador")
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_DEVELOPMENT)
    monkeypatch.setenv(constants.ENV_RBAC_ENABLED, "true")
    monkeypatch.setenv(constants.ENV_AUTH_EXPERIMENTAL_ENABLED, "false")
    importlib.reload(settings)
    importlib.reload(feature_flags)
    authorizer = PersistentRBACAuthorizer(repo)

    assert not authorizer.has_permission(user.id, "system:admin")


def test_rotas_read_only_seguem_publicas(monkeypatch):
    monkeypatch.setenv(constants.ENV_PROMOGG_ENV, constants.ENVIRONMENT_DEVELOPMENT)
    monkeypatch.setenv(constants.ENV_RBAC_ENABLED, "true")
    importlib.reload(settings)
    importlib.reload(feature_flags)

    from api_promogg import main as main_module

    main_module = importlib.reload(main_module)
    client = TestClient(main_module.app)

    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/ofertas").status_code == 200
    assert client.get("/api/v1/categorias").status_code == 200


def test_rbac_persistente_nao_toca_banco_operacional(tmp_path):
    operational_db = Path("banco.db")
    before_mtime = operational_db.stat().st_mtime_ns if operational_db.exists() else None
    repo = _repo(tmp_path)
    user = _criar_usuario(repo)
    repo.garantir_seeds_papeis_permissoes()
    repo.atribuir_papel_usuario(user.id, "Revisor")
    PersistentRBACAuthorizer(repo, enabled=True).has_permission(user.id, "offers:review")

    after_mtime = operational_db.stat().st_mtime_ns if operational_db.exists() else None
    assert before_mtime == after_mtime
