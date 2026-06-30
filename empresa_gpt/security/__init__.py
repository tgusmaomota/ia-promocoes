"""Security contracts for EmpresaGPT.

This package does not enable auth, RBAC, cookies, or sessions at import time.
"""

from .contract import AuditEvent, SecurityContract, SecurityDecision, SecurityError

__all__ = [
    "AuditEvent",
    "SecurityContract",
    "SecurityDecision",
    "SecurityError",
]

