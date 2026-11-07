import os
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import Response
from starlette.middleware.trustedhost import TrustedHostMiddleware

from study_api.application.chat import ChatService
from study_api.core.errors import configure_errors, response
from study_api.domain.chat import Provider
from study_api.infrastructure.db.database import database_path, engine_for
from study_api.infrastructure.db.repository import SqliteRepository
from study_api.infrastructure.ollama import OllamaProvider
from study_api.presentation.exercises import router as exercises_router
from study_api.presentation.health import router as health_router
from study_api.presentation.routes import router


def create_app(path: Path | None = None, provider: Provider | None = None) -> FastAPI:
    frontend_port = int(os.environ.get("STUDY_WEB_PORT", "5173"))
    if not 0 < frontend_port <= 65535:
        raise ValueError("Porta local inválida.")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = engine_for(path or database_path())
        async with httpx.AsyncClient(
            base_url="http://127.0.0.1:11434",
            trust_env=False,
            timeout=httpx.Timeout(90, connect=5),
            follow_redirects=False,
        ) as client:
            service = ChatService(
                SqliteRepository(engine), provider or OllamaProvider(client)
            )
            app.state.service = service
            service.recover()
            try:
                yield
            finally:
                await service.close()
                engine.dispose()

    app = FastAPI(
        title="Plataforma de Estudos com IA", version="0.1.0", lifespan=lifespan
    )
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "test"]
    )
    configure_errors(app)

    @app.middleware("http")
    async def local_boundary(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.request_id = str(uuid4())
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin and origin not in {
                f"http://127.0.0.1:{frontend_port}",
                f"http://localhost:{frontend_port}",
                "http://127.0.0.1:5173",
                "http://localhost:5173",
                "http://127.0.0.1:8000",
                "http://localhost:8000",
            }:
                return response(
                    request, "ORIGIN_BLOCKED", "Origem não autorizada.", 403
                )
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 32_768:
                    return response(
                        request,
                        "PAYLOAD_TOO_LARGE",
                        "Requisição excede o limite permitido.",
                        413,
                    )
            request._body = bytes(body)
        result = await call_next(request)
        result.headers["X-Request-ID"] = request.state.request_id
        result.headers["X-Content-Type-Options"] = "nosniff"
        return result

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(router, prefix="/api/v1")
    app.include_router(exercises_router, prefix="/api/v1")
    return app


app = create_app()
