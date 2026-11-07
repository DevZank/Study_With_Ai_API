import asyncio
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from test_chat import TestProvider

from study_api.main import create_app


class BrokenProvider(TestProvider):
    async def models(self) -> list[str]:
        raise RuntimeError("conteúdo privado que não deve sair na resposta ou log")


def test_unexpected_error_is_safe(
    database: Path, caplog: pytest.LogCaptureFixture
) -> None:
    async def scenario() -> None:
        app = create_app(database, BrokenProvider())
        async with (
            app.router.lifespan_context(app),
            AsyncClient(
                transport=ASGITransport(app=app, raise_app_exceptions=False),
                base_url="http://test",
            ) as client,
        ):
            response = await client.get("/api/v1/ai/models")
            assert response.status_code == 500
            assert response.json()["error"]["code"] == "INTERNAL_ERROR"
            assert response.headers["X-Request-ID"]
            assert "conteúdo privado" not in response.text
        assert "conteúdo privado" not in caplog.text
        assert "unexpected_request_error" in caplog.text

    asyncio.run(scenario())
