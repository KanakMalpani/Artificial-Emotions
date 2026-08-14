"""Exception → stable JSON envelope mapping.

Every error the API emits uses ``{"error": {"code", "message", "details"}}``.
Codes are public contract (see ``artificial_emotions.errors``).
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from artificial_emotions.errors import (
    ERR_AUTH_REQUIRED,
    ERR_INTERNAL,
    ERR_VALIDATION,
    CuriosityError,
    classify_value_error,
    error_payload,
)

__all__ = ["register_error_handlers"]


def _jsonable_validation_errors(errors: list[Any]) -> list[Any]:
    """Pydantic v2 may put Exception instances in ``ctx.error`` — those are not JSON."""
    out: list[Any] = []
    for err in errors:
        if not isinstance(err, dict):
            out.append(err)
            continue
        item = dict(err)
        ctx = item.get("ctx")
        if isinstance(ctx, dict):
            item["ctx"] = {
                key: (str(val) if isinstance(val, BaseException) else val)
                for key, val in ctx.items()
            }
        out.append(item)
    return out


def _http_error_response(exc: CuriosityError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content={"error": exc.to_dict(), "detail": exc.message},
    )


def register_error_handlers(app: FastAPI) -> None:
    """Attach the shared exception handlers to ``app``."""

    @app.exception_handler(CuriosityError)
    async def curiosity_error_handler(_request: Request, exc: CuriosityError) -> JSONResponse:
        return _http_error_response(exc)

    @app.exception_handler(ValueError)
    async def value_error_handler(_request: Request, exc: ValueError) -> JSONResponse:
        return _http_error_response(classify_value_error(exc))

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_payload(
                ERR_VALIDATION,
                "Request validation failed",
                details={"errors": _jsonable_validation_errors(exc.errors())},
            ),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict) and "error" in detail:
            return JSONResponse(status_code=exc.status_code, content=detail)
        message = detail if isinstance(detail, str) else str(detail)
        code = ERR_AUTH_REQUIRED if exc.status_code == 401 else ERR_VALIDATION
        if exc.status_code >= 500:
            code = ERR_INTERNAL
        body = error_payload(code, message)
        body["detail"] = message
        return JSONResponse(status_code=exc.status_code, content=body)
