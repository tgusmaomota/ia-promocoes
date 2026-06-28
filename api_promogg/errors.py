from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    def __init__(self, code, message, status_code=400):
        self.code = code
        self.message = message
        self.status_code = status_code


class NotFoundError(ApiError):
    def __init__(self, message="Recurso não encontrado."):
        super().__init__("NOT_FOUND", message, 404)


class ValidationApiError(ApiError):
    def __init__(self, message="Dados inválidos."):
        super().__init__("VALIDATION_ERROR", message, 400)


def request_id_from(request: Request):
    return getattr(request.state, "request_id", "req_unknown")


def error_payload(code, message, request_id):
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
        }
    }


async def api_error_handler(request: Request, exc: ApiError):
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(exc.code, exc.message, request_id_from(request)),
    )


async def unhandled_error_handler(request: Request, _exc: Exception):
    return JSONResponse(
        status_code=500,
        content=error_payload("INTERNAL_ERROR", "Erro interno.", request_id_from(request)),
    )


async def validation_error_handler(request: Request, _exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content=error_payload("VALIDATION_ERROR", "Dados inválidos.", request_id_from(request)),
    )


async def http_error_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return JSONResponse(
            status_code=404,
            content=error_payload("NOT_FOUND", "Recurso não encontrado.", request_id_from(request)),
        )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload("HTTP_ERROR", "Erro na requisição.", request_id_from(request)),
    )
