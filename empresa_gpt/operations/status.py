"""Product status composition contracts for EGOC."""

from __future__ import annotations

from .models import DeploymentStatus, Product, ProductAvailability


def unknown_product(name: str, version: str = "0.0.0") -> Product:
    """Return a product-neutral unknown status snapshot."""

    return Product(
        name=name,
        version=version,
        status=ProductAvailability.UNKNOWN,
        availability=ProductAvailability.UNKNOWN,
        deployment_status=DeploymentStatus.UNKNOWN,
    )

