"""Metric model surface for EGOC."""

from __future__ import annotations

from .models import Metric

STANDARD_METRIC_NAMES = (
    "products_online",
    "services_online",
    "availability",
    "average_response_time",
    "quality_score",
    "health_score",
    "resource_usage",
)


def metric_placeholder(name: str, unit: str = "") -> Metric:
    """Return an explicit zero metric for architecture tests."""

    return Metric(name=name, value=0.0, unit=unit)

