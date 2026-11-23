import logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.exceptions import AppException

logger = logging.getLogger(__name__)
IGNORED_LOC = {"body", "query", "path", "header", "cookie"}


def _error(status: int, errors: list[dict] | None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"errors": errors})


async def app_exception_handler(request: Request, exc: AppException):
    return _error(exc.status_code, [{"field": exc.field, "message": exc.message}])


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        loc = [str(p) for p in err["loc"] if p not in IGNORED_LOC]
        message = err["msg"].removeprefix("Value error, ")
        errors.append({"field": ".".join(loc) or None, "message": message})
    return _error(422, errors)


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    # menangkap 404 route tidak ditemukan, 405, dsb.
    return _error(exc.status_code, [{"field": None, "message": str(exc.detail)}])


async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error")
    return _error(500, [{"field": None, "message": "Internal server error"}])


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
