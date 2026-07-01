"""Official Quality Engine rules for EmpresaGPT."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

REQUIRED_ROOT_DOCUMENTS = (
    "EMPRESAGPT_MASTER_PLAN.md",
    "EMPRESAGPT_OPERATIONS_CENTER.md",
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
    "empresa_gpt/docs/PRODUCT_INTELLIGENCE_ENGINE.md",
    "empresa_gpt/docs/PROMOGG_DESIGN_SYSTEM.md",
)

REQUIRED_CONTRACTS = (
    "empresa_gpt/core/config/contract.py",
    "empresa_gpt/security/contract.py",
    "empresa_gpt/ai/contract.py",
    "empresa_gpt/storage/contract.py",
    "empresa_gpt/analytics/contract.py",
    "empresa_gpt/monitoring/contract.py",
    "empresa_gpt/services/contract.py",
    "empresa_gpt/product_intelligence/contracts.py",
    "empresa_gpt/product_intelligence/models.py",
    "empresa_gpt/operations/contracts.py",
    "empresa_gpt/operations/models.py",
)

REQUIRED_CONTRACT_PACKAGES = (
    "empresa_gpt.core.config",
    "empresa_gpt.security",
    "empresa_gpt.ai",
    "empresa_gpt.storage",
    "empresa_gpt.analytics",
    "empresa_gpt.monitoring",
    "empresa_gpt.services",
    "empresa_gpt.product_intelligence",
    "empresa_gpt.operations",
)

QUALITY_AREAS = (
    "core",
    "ai",
    "analytics",
    "security",
    "storage",
    "services",
    "product_intelligence",
    "operations",
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

PROMOGG_HOME_REQUIRED_SIGNALS = (
    ("Hero Banner", ("hero", "banner")),
    ("Ofertas em destaque", ("ofertas em destaque", "ofertas do dia", "oferta do dia")),
    ("Destaques", ("destaque", "destaques")),
    ("Mais clicadas", ("mais clicadas", "mais vistos")),
    ("Mais recentes", ("mais recentes", "recentes")),
    ("Categorias populares", ("categorias populares", "categorias")),
    ("Recomendacoes", ("recomend",)),
    ("Busca inteligente", ("busca", "search")),
    ("Menor preco historico", ("menor preco", "historico")),
)

PROMOGG_SEO_REQUIRED_SIGNALS = (
    ("Open Graph", ("og:", "property=\"og")),
    ("Schema.org", ("schema.org", "application/ld+json")),
    ("Canonical", ("rel=\"canonical\"",)),
    ("Meta Description", ("name=\"description\"",)),
    ("Title", ("<title",)),
    ("Twitter Cards", ("twitter:", "twitter:card")),
)

PROMOGG_V2_IMPLEMENTATION_SIGNALS = {
    "Hero implementado": (
        ("index", "hero-search"),
        ("index", "hero-metrics"),
        ("index", "ofertas verificadas"),
        ("index", "ofertas-destaque"),
    ),
    "Cards Premium implementados": (
        ("index", "premium-card"),
        ("index", "premium-facts"),
        ("style", ".premium-card"),
        ("script", "intelligence-slots"),
    ),
    "Estados vazios implementados": (
        ("script", "exibirskeleton"),
        ("script", "skeleton-card"),
        ("script", "empty-state"),
        ("script", "nenhuma oferta encontrada"),
    ),
    "Responsividade basica": (
        ("style", "@media (max-width: 1080px)"),
        ("style", "@media (max-width: 760px)"),
        ("style", ".hero-search"),
        ("style", ".category-grid"),
    ),
    "SEO basico V2": (
        ("index", "property=\"og:"),
        ("index", "twitter:card"),
        ("index", "rel=\"canonical\""),
        ("index", "name=\"description\""),
        ("index", "application/ld+json"),
    ),
}

PROMOGG_EXPERIENCE_REQUIRED_DOCUMENTS = (
    "PROMOGG_UX_AUDIT.md",
    "empresa_gpt/docs/PROMOGG_DESIGN_SYSTEM.md",
)

PROMOGG_EXPERIENCE_PLAN_TERMS = {
    "Design System documentado": ("tipografia", "espacamento", "cards", "botoes", "badges", "skeleton", "paginacao", "navegacao"),
    "Cards Premium planejados": ("imagem grande", "preco atual", "menor preco", "score da ia", "ultima atualizacao", "estado de disponibilidade"),
    "Home completa planejada": ("hero banner", "busca", "categorias", "ofertas do dia", "destaques", "mais recentes", "menor preco historico", "mais clicadas", "recomendacoes", "rodape institucional"),
    "Painel de Confianca planejado": ("historico de preco", "origem", "transparencia", "politica de afiliados", "explicacao da ia", "nivel de confianca"),
}

EGOC_REQUIRED_FILES = (
    "empresa_gpt/operations/README.md",
    "empresa_gpt/operations/__init__.py",
    "empresa_gpt/operations/dashboard.py",
    "empresa_gpt/operations/contracts.py",
    "empresa_gpt/operations/health.py",
    "empresa_gpt/operations/services.py",
    "empresa_gpt/operations/alerts.py",
    "empresa_gpt/operations/metrics.py",
    "empresa_gpt/operations/risk.py",
    "empresa_gpt/operations/status.py",
    "empresa_gpt/operations/backup.py",
    "empresa_gpt/operations/audit.py",
    "empresa_gpt/operations/report.py",
    "empresa_gpt/operations/models.py",
    "EMPRESAGPT_OPERATIONS_CENTER.md",
)

EGOC_REQUIRED_CONTRACTS = (
    "ProductHealthContract",
    "ProductStatusContract",
    "ServiceContract",
    "RiskContract",
    "BackupContract",
    "AuditContract",
    "AlertContract",
    "MetricsContract",
)

EGOC_REQUIRED_MODELS = (
    "Product",
    "Service",
    "Metric",
    "Health",
    "Risk",
    "Audit",
    "Backup",
    "Alert",
)

EGOC_DASHBOARD_TERMS = (
    "EmpresaGPT",
    "Produtos",
    "Saude",
    "Servicos",
    "Backups",
    "Alertas",
    "Auditorias",
    "Qualidade",
    "Riscos",
    "Uso de recursos",
)
