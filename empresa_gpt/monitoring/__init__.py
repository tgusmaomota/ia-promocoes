"""Monitoring contracts for EmpresaGPT.

No loop, process, or alert is started at import time.
"""

from .contract import HealthCheck, HealthStatus, MonitoringContract, MonitoringError

__all__ = [
    "HealthCheck",
    "HealthStatus",
    "MonitoringContract",
    "MonitoringError",
]

