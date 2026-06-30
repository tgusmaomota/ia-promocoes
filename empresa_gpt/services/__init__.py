"""Service contracts for EmpresaGPT.

No service is started at import time.
"""

from .contract import ServiceCommand, ServiceContract, ServiceError, ServiceResult

__all__ = [
    "ServiceCommand",
    "ServiceContract",
    "ServiceError",
    "ServiceResult",
]

