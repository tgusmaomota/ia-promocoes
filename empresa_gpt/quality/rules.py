"""Official Quality Engine rules for EmpresaGPT."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

REQUIRED_ROOT_DOCUMENTS = (
    "EMPRESAGPT_MASTER_PLAN.md",
    "ARQUITETURA_EMPRESAGPT.md",
    "ROADMAP_EMPRESAGPT.md",
    "PADROES_DESENVOLVIMENTO.md",
    "MODELO_DE_MODULOS.md",
    "PRINCIPIOS_DE_SEGURANCA.md",
    "GUIA_DE_CONTRIBUICAO.md",
)

REQUIRED_ADRS = (
    "empresa_gpt/docs/ADR-0001-core-sem-dependencia-do-promogg.md",
    "empresa_gpt/docs/ADR-0002-ollama-como-ia-local-prioritaria.md",
    "empresa_gpt/docs/ADR-0003-seguranca-e-auditoria-sanitizada.md",
    "empresa_gpt/docs/ADR-0004-produtos-como-modulos.md",
    "empresa_gpt/docs/ADR-0005-servicos-desligados-por-padrao.md",
)

REQUIRED_MANUAL_DOCUMENTS = (
    "empresa_gpt/docs/MANUAL_OFICIAL_EMPRESAGPT.md",
    "empresa_gpt/docs/RFC-0000-template.md",
    "empresa_gpt/docs/PLAYBOOK-operacao-segura.md",
    "empresa_gpt/docs/CHECKLIST-producao.md",
    "empresa_gpt/docs/GUIA-revisao-de-codigo.md",
    "empresa_gpt/docs/CONVENCOES-ia.md",
    "empresa_gpt/docs/CRITERIOS-novas-funcionalidades.md",
)

REQUIRED_CONTRACTS = (
    "empresa_gpt/core/config/contract.py",
    "empresa_gpt/security/contract.py",
    "empresa_gpt/ai/contract.py",
    "empresa_gpt/storage/contract.py",
    "empresa_gpt/analytics/contract.py",
    "empresa_gpt/monitoring/contract.py",
    "empresa_gpt/services/contract.py",
)

REQUIRED_CONTRACT_PACKAGES = (
    "empresa_gpt.core.config",
    "empresa_gpt.security",
    "empresa_gpt.ai",
    "empresa_gpt.storage",
    "empresa_gpt.analytics",
    "empresa_gpt.monitoring",
    "empresa_gpt.services",
)

QUALITY_AREAS = (
    "core",
    "ai",
    "analytics",
    "security",
    "storage",
    "services",
    "monitoring",
    "deployment",
    "integrations",
    "shared",
    "docs",
    "quality",
)

README_REQUIRED_TERMS = (
    "respons",
    "entrada",
    "saida",
    "erro",
    "seguran",
    "uso futuro",
)

BANNED_PROMOGG_IMPORT_ROOTS = (
    "ia_promocoes",
    "banco",
    "gerar_site",
    "gerar_site_publico",
    "painel",
    "painel_remoto",
    "supervisor_promogg",
    "mercadolivre_api",
    "meli_oauth",
    "coletor_mercadolivre",
    "coletor_mercadolivre_api",
    "gerador_afiliados_oficial",
    "gerador_link_mercadolivre",
    "agente_afiliado",
    "publicador_telegram",
    "agente_telegram",
)

BANNED_CORE_IMPORT_ROOTS = BANNED_PROMOGG_IMPORT_ROOTS + (
    "playwright",
    "streamlit",
)

PROMOGG_ESSENTIAL_COMMANDS = (
    "modo-estavel",
    "modo-economico",
    "status-servicos",
    "auditar-seguranca-publicacao",
    "validar",
    "checklist-divulgacao",
    "supervisor",
    "painel-remoto",
)

SENSITIVE_FILENAMES = (
    ".env",
    "banco.db",
    "promocoes.db",
    "auth_dev.db",
    "perfil_mercadolivre",
    "perfil_mercadolivre_backup",
    "venv",
)

SENSITIVE_SUFFIXES = (
    ".sqlite",
    ".sqlite3",
    ".db",
)

SENSITIVE_TEXT_PATTERNS = (
    "telegram_bot_token",
    "telegram_token",
    "client_secret",
    "refresh_token",
    "access_token",
    "cookie",
    "set-cookie",
    "authorization: bearer",
    "secret_key",
    "api_key",
    "password=",
)

ALLOWED_SENSITIVE_TEXT_FILES = (
    ".env.example",
    "PRINCIPIOS_DE_SEGURANCA.md",
    "RELATORIO_EMPRESAGPT_QUALITY_ENGINE.md",
    "RELATORIO_EMPRESAGPT_QUALITY_ENGINE.json",
)

GIT_ALLOWED_REPORTS = (
    "RELATORIO_ARQUITETURA_EMPRESAGPT.md",
    "RELATORIO_EMPRESAGPT_FASE2_CONTRATOS.md",
    "RELATORIO_EMPRESAGPT_QUALITY_ENGINE.md",
    "RELATORIO_EMPRESAGPT_QUALITY_ENGINE.json",
)

MAX_REVIEW_FILE_BYTES = 1_500_000

