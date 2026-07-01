from pathlib import Path

from empresa_gpt.operations import (
    Alert,
    Audit,
    Backup,
    Health,
    Metric,
    Product,
    ProductAvailability,
    Risk,
    Service,
)
from empresa_gpt.operations.contracts import (
    AlertContract,
    AuditContract,
    BackupContract,
    MetricsContract,
    ProductHealthContract,
    ProductStatusContract,
    RiskContract,
    ServiceContract,
)
from empresa_gpt.operations.dashboard import EGOC_DASHBOARD_TREE
from empresa_gpt.quality.engine import QualityEngine


def test_operations_models_are_product_neutral():
    product = Product(
        name="Produto Exemplo",
        version="0.1.0",
        status=ProductAvailability.UNKNOWN,
        services=(Service(name="Site"),),
        metrics=(Metric(name="availability", value=0.0, unit="%"),),
    )

    assert product.name == "Produto Exemplo"
    assert product.status == ProductAvailability.UNKNOWN
    assert product.services[0].name == "Site"


def test_operations_contracts_are_importable():
    contracts = (
        ProductHealthContract,
        ProductStatusContract,
        ServiceContract,
        RiskContract,
        BackupContract,
        AuditContract,
        AlertContract,
        MetricsContract,
    )
    models = (Health, Risk, Audit, Backup, Alert)

    assert all(contract.__name__.endswith("Contract") for contract in contracts)
    assert all(model.__name__ for model in models)


def test_operations_dashboard_tree_has_required_sections():
    products = EGOC_DASHBOARD_TREE.children[0]
    sections = {section.name for section in products.children}

    assert EGOC_DASHBOARD_TREE.name == "EmpresaGPT"
    assert products.name == "Produtos"
    assert {"Saude", "Servicos", "Backups", "Alertas", "Auditorias", "Qualidade", "Riscos", "Uso de recursos"} <= sections


def test_quality_engine_reports_egoc_area():
    report = QualityEngine(root=Path.cwd()).run(write_report=False)

    assert any(result.area == "EGOC" for result in report.results)

