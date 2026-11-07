import json
import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from study_api.domain.chat import AppError

logger = logging.getLogger("study_api")


def response(request: Request, code: str, message: str, status: int) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    return JSONResponse(
        {
            "error": {
                "code": code,
                "message": message,
                "details": {},
                "request_id": request_id,
            }
        },
        status_code=status,
        headers={"X-Request-ID": request_id},
    )


def configure_errors(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error(request: Request, error: AppError) -> JSONResponse:
        return response(request, error.code, error.message, error.status)

    @app.exception_handler(RequestValidationError)
    async def validation(request: Request, _: RequestValidationError) -> JSONResponse:
        return response(
            request,
            "INVALID_INPUT",
            "Verifique os campos e limites da requisição.",
            422,
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException) -> JSONResponse:
        return response(
            request, "HTTP_ERROR", "Recurso indisponível.", error.status_code
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, _: SQLAlchemyError) -> JSONResponse:
        logger.error(
            json.dumps(
                {
                    "event": "database_error",
                    "request_id": getattr(request.state, "request_id", ""),
                }
            )
        )
        return response(
            request, "DATABASE_ERROR", "Falha ao acessar os dados locais.", 503
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, error: Exception) -> JSONResponse:
        logger.error(
            json.dumps(
                {
                    "event": "unexpected_request_error",
                    "request_id": getattr(request.state, "request_id", ""),
                    "error_type": type(error).__name__,
                }
            )
        )
        return response(
            request, "INTERNAL_ERROR", "Falha inesperada ao processar a operação.", 500
        )
