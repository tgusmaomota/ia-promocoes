"""Analytics contracts for EmpresaGPT.

No event is emitted at import time.
"""

from .contract import AnalyticsContract, AnalyticsError, AnalyticsEvent, AnalyticsReport

__all__ = [
    "AnalyticsContract",
    "AnalyticsError",
    "AnalyticsEvent",
    "AnalyticsReport",
]

