import asyncio
from collections.abc import AsyncIterator

import httpx
import pytest

from study_api.domain.chat import AppError
from study_api.infrastructure.ollama import OllamaProvider


@pytest.mark.parametrize(
    "body,code",
    [
        ('{"message":{"content":"parcial"},"done":false}\n', "STREAM_INTERRUPTED"),
        ('{"error":"private upstream error"}\n', "MODEL_FAILED"),
        ("not json\n", "INVALID_MODEL_RESPONSE"),
        (
            '{"message":{"content":"parcial"},"done":true,"done_reason":"length"}\n',
            "OUTPUT_LIMIT",
        ),
    ],
)
def test_invalid_stream(body: str, code: str) -> None:
    async def scenario() -> None:
        transport = httpx.MockTransport(lambda _: httpx.Response(200, content=body))
        async with httpx.AsyncClient(
            transport=transport, base_url="http://127.0.0.1:11434"
        ) as client:
            with pytest.raises(AppError) as error:
                async for _ in OllamaProvider(client).chat("local:test", []):
                    pass
            assert error.value.code == code
            assert "private upstream" not in error.value.message

    asyncio.run(scenario())


def test_no_cloud_and_unavailable() -> None:
    async def scenario() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/tags":
                return httpx.Response(
                    200,
                    json={
                        "models": [
                            {"name": "alias", "size": 100},
                            {"name": "model:cloud", "size": 100},
                        ]
                    },
                )
            return httpx.Response(
                200,
                json={
                    "remote_host": "https://example.com",
                    "capabilities": ["completion"],
                },
            )

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434"
        ) as client:
            provider = OllamaProvider(client)
            assert await provider.models() == ["alias"]
            with pytest.raises(AppError, match="somente modelos locais"):
                await provider.validate_model("alias")
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: httpx.Response(503)),
            base_url="http://127.0.0.1:11434",
        ) as client:
            with pytest.raises(AppError, match="Ollama indisponível"):
                await OllamaProvider(client).models()

    asyncio.run(scenario())


class SlowStream(httpx.AsyncByteStream):
    def __init__(self) -> None:
        self.closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield b'{"message":{"content":"partial"},"done":false}\n'
        await asyncio.sleep(10)

    async def aclose(self) -> None:
        self.closed = True


def test_cancel_closes_http_stream() -> None:
    async def scenario() -> None:
        stream = SlowStream()
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, stream=stream)),
            base_url="http://127.0.0.1:11434",
        ) as client:

            async def consume() -> None:
                async for _ in OllamaProvider(client).chat("local:test", []):
                    pass

            task = asyncio.create_task(consume())
            await asyncio.sleep(0.02)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert stream.closed

    asyncio.run(scenario())
