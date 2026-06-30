"""Storage contracts for EmpresaGPT.

No database connection is opened at import time.
"""

from .contract import RepositoryContract, StorageError, StorageQuery, StorageResult

__all__ = [
    "RepositoryContract",
    "StorageError",
    "StorageQuery",
    "StorageResult",
]

