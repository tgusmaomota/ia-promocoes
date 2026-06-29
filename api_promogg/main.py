from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from api_promogg.config import ALLOWED_ORIGINS, API_PREFIX, APP_TITLE, validar_allowed_origins
from api_promogg.errors import (
    ApiError,
    api_error_handler,
    http_error_handler,
    unhandled_error_handler,
    validation_error_handler,
)
from api_promogg.middleware import RequestIDMiddleware
from api_promogg.routers import auth, health, ofertas


validar_allowed_origins(ALLOWED_ORIGINS)

app = FastAPI(
    title=APP_TITLE,
    version="0.1.0",
    docs_url=f"{API_PREFIX}/docs",
    redoc_url=f"{API_PREFIX}/redoc",
    openapi_url=f"{API_PREFIX}/openapi.json",
)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Content-Type", "X-Request-ID", "Authorization"],
)

app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(StarletteHTTPException, http_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)

app.include_router(health.router, prefix=API_PREFIX)
app.include_router(ofertas.router, prefix=API_PREFIX)
app.include_router(auth.router, prefix=API_PREFIX)
