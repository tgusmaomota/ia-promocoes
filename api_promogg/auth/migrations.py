from api_promogg.auth.rbac import DEFAULT_PERMISSIONS, ROLE_PERMISSIONS


SCHEMA_VERSION = 1


PERMISSION_METADATA = {
    "offers:read": ("Ler ofertas.", "low", 0),
    "offers:review": ("Aprovar ou rejeitar ofertas.", "high", 0),
    "offers:edit": ("Editar ofertas.", "high", 0),
    "offers:publish": ("Publicar ofertas em canais públicos.", "high", 1),
    "catalog:read": ("Ler catálogo.", "low", 0),
    "catalog:generate": ("Gerar ou preparar catálogo.", "high", 0),
    "telegram:publish": ("Publicar no Telegram.", "high", 1),
    "site:deploy": ("Publicar/deployar site.", "high", 1),
    "workers:read": ("Ler status de workers.", "low", 0),
    "workers:run": ("Iniciar workers.", "high", 1),
    "workers:stop": ("Parar workers.", "high", 1),
    "analytics:read": ("Ler analytics.", "medium", 0),
    "audit:read": ("Ler auditoria.", "high", 1),
    "users:read": ("Consultar usuários.", "medium", 1),
    "users:manage": ("Gerenciar usuários.", "critical", 1),
    "roles:manage": ("Gerenciar papéis.", "critical", 1),
    "secrets:manage": ("Gerenciar segredos.", "critical", 1),
    "backup:create": ("Criar backup.", "medium", 0),
    "backup:restore": ("Restaurar backup.", "critical", 1),
    "system:admin": ("Administrar sistema.", "critical", 1),
}


ROLE_DESCRIPTIONS = {
    "Administrador": "Governa segurança, usuários, papéis, secrets e operações críticas.",
    "Operador": "Executa rotina operacional e publicação controlada.",
    "Revisor": "Avalia, aprova, rejeita e edita ofertas dentro da curadoria.",
    "Analista": "Consulta métricas, auditoria e saúde do sistema.",
    "Somente leitura": "Visualiza dados sanitizados sem executar mudanças.",
}


def inicializar_schema(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            disabled_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);

        CREATE TABLE IF NOT EXISTS roles (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL,
            is_system INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS permissions (
            id TEXT PRIMARY KEY,
            code TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            requires_mfa INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_permissions_risk ON permissions(risk_level);

        CREATE TABLE IF NOT EXISTS role_permissions (
            role_id TEXT NOT NULL,
            permission_id TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (role_id, permission_id),
            FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
            FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS user_roles (
            user_id TEXT NOT NULL,
            role_id TEXT NOT NULL,
            granted_by TEXT,
            granted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            revoked_at TEXT,
            PRIMARY KEY (user_id, role_id, granted_at),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_user_roles_user ON user_roles(user_id);
        CREATE INDEX IF NOT EXISTS idx_user_roles_role ON user_roles(role_id);

        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TEXT,
            expires_at TEXT NOT NULL,
            revoked_at TEXT,
            revocation_reason TEXT,
            ip_hash TEXT,
            user_agent_hash TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_sessions_user_status ON sessions(user_id, status);
        CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);

        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            family_id TEXT NOT NULL,
            previous_token_id TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            used_at TEXT,
            expires_at TEXT NOT NULL,
            revoked_at TEXT,
            reuse_detected_at TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
            FOREIGN KEY (previous_token_id) REFERENCES refresh_tokens(id)
        );
        CREATE INDEX IF NOT EXISTS idx_refresh_session ON refresh_tokens(session_id);
        CREATE INDEX IF NOT EXISTS idx_refresh_family ON refresh_tokens(family_id);
        CREATE INDEX IF NOT EXISTS idx_refresh_expires ON refresh_tokens(expires_at);

        CREATE TABLE IF NOT EXISTS audit_events (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            actor_user_id TEXT,
            actor_session_id TEXT,
            action TEXT NOT NULL,
            permission TEXT,
            resource_type TEXT,
            resource_id TEXT,
            result TEXT NOT NULL,
            reason TEXT,
            request_id TEXT,
            ip_hash TEXT,
            user_agent_hash TEXT,
            metadata_json TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_events(created_at);
        CREATE INDEX IF NOT EXISTS idx_audit_actor_created ON audit_events(actor_user_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_audit_action_created ON audit_events(action, created_at);
        CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_events(resource_type, resource_id);

        INSERT OR IGNORE INTO schema_migrations (version) VALUES (1);
        """
    )
    seed_roles_permissions(conn)
    conn.commit()


def seed_roles_permissions(conn):
    for code in sorted(DEFAULT_PERMISSIONS):
        description, risk_level, requires_mfa = PERMISSION_METADATA[code]
        conn.execute(
            """
            INSERT OR IGNORE INTO permissions (id, code, description, risk_level, requires_mfa)
            VALUES (?, ?, ?, ?, ?)
            """,
            (f"perm:{code}", code, description, risk_level, requires_mfa),
        )

    for role_name, permissions in ROLE_PERMISSIONS.items():
        conn.execute(
            """
            INSERT OR IGNORE INTO roles (id, name, description, is_system)
            VALUES (?, ?, ?, 1)
            """,
            (f"role:{role_name}", role_name, ROLE_DESCRIPTIONS[role_name]),
        )
        for permission in sorted(permissions):
            conn.execute(
                """
                INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
                VALUES (?, ?)
                """,
                (f"role:{role_name}", f"perm:{permission}"),
            )
