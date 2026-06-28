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
