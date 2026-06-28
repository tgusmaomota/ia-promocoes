import logging
from time import perf_counter
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware


logger = logging.getLogger("api_promogg.requests")

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Permissions-Policy": "accelerometer=(), camera=(), geolocation=(), gyroscope=(), microphone=(), payment=(), usb=()",
    "Cache-Control": "no-store",
}


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid4().hex}"
        request.state.request_id = request_id
        inicio = perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        for header, valor in SECURITY_HEADERS.items():
            response.headers[header] = valor
        duracao_ms = round((perf_counter() - inicio) * 1000, 2)
        logger.info(
            "api_request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duracao_ms,
            },
        )
        return response
