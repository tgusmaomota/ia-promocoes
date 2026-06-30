DEFAULT_PERMISSIONS = {
    "offers:read",
    "offers:review",
    "offers:edit",
    "offers:publish",
    "catalog:read",
    "catalog:generate",
    "telegram:publish",
    "site:deploy",
    "workers:read",
    "workers:run",
    "workers:stop",
    "analytics:read",
    "audit:read",
    "users:read",
    "users:manage",
    "roles:manage",
    "secrets:manage",
    "backup:create",
    "backup:restore",
    "system:admin",
}


class PersistentRBACAuthorizer:
    """Autorizador experimental persistente, negando por padrão."""

    def __init__(self, repository, *, enabled: bool | None = None, environment: str | None = None):
        self.repository = repository
        self._enabled = enabled
        self._environment = environment

    def is_enabled(self) -> bool:
        if self._enabled is not None:
            return self._enabled
        from api_promogg.security import constants, feature_flags, settings

        return feature_flags.rbac_enabled() and settings.PROMOGG_ENV == constants.ENVIRONMENT_DEVELOPMENT

    def list_user_permissions(self, user_id: str) -> set[str]:
        if not self._can_authorize_user(user_id):
            return set()
        return {permission.code for permission in self.repository.listar_permissoes_efetivas_usuario(user_id)}

    def has_permission(self, user_id: str, permission: str) -> bool:
        if permission not in DEFAULT_PERMISSIONS:
            return False
        return permission in self.list_user_permissions(user_id)

    def has_any_permission(self, user_id: str, permissions: list[str] | tuple[str, ...] | set[str]) -> bool:
        if not permissions:
            return False
        effective = self.list_user_permissions(user_id)
        return any(permission in effective for permission in permissions if permission in DEFAULT_PERMISSIONS)

    def has_all_permissions(self, user_id: str, permissions: list[str] | tuple[str, ...] | set[str]) -> bool:
        if not permissions:
            return False
        effective = self.list_user_permissions(user_id)
        return all(permission in effective for permission in permissions if permission in DEFAULT_PERMISSIONS) and all(
            permission in DEFAULT_PERMISSIONS for permission in permissions
        )

    def _can_authorize_user(self, user_id: str) -> bool:
        if not user_id or not self.is_enabled():
            return False
        user = self.repository.buscar_usuario_por_id(user_id)
        return bool(user and user.status == "active")


ROLE_PERMISSIONS = {
    "Administrador": DEFAULT_PERMISSIONS,
    "Operador": {
        "offers:read",
        "offers:review",
        "offers:edit",
        "offers:publish",
        "catalog:read",
        "catalog:generate",
        "telegram:publish",
        "site:deploy",
        "workers:read",
        "workers:run",
        "workers:stop",
        "analytics:read",
        "backup:create",
    },
    "Revisor": {
        "offers:read",
        "offers:review",
        "offers:edit",
        "catalog:read",
    },
    "Analista": {
        "offers:read",
        "catalog:read",
        "workers:read",
        "analytics:read",
        "audit:read",
    },
    "Somente leitura": {
        "offers:read",
        "catalog:read",
        "workers:read",
        "analytics:read",
    },
}


def has_permission(role: str, permission: str) -> bool:
    if permission not in DEFAULT_PERMISSIONS:
        return False
    return permission in ROLE_PERMISSIONS.get(role, set())


def roles_have_permission(roles: list[str] | tuple[str, ...] | set[str], permission: str) -> bool:
    return any(has_permission(role, permission) for role in roles)


def permissions_for_roles(roles: list[str] | tuple[str, ...] | set[str]) -> set[str]:
    permissions: set[str] = set()
    for role in roles:
        permissions.update(ROLE_PERMISSIONS.get(role, set()))
    return permissions
