import json
from collections.abc import AsyncIterator

import httpx
from pydantic import BaseModel, Field, ValidationError

from study_api.domain.chat import AppError


class ModelInfo(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    size: int = 0
    remote_model: str = ""
    remote_host: str = ""


class ModelList(BaseModel):
    models: list[ModelInfo]


class ModelDetails(BaseModel):
    remote_model: str = ""
    remote_host: str = ""
    capabilities: list[str] = []


class DeltaMessage(BaseModel):
    content: str = Field(default="", max_length=100_000)


class ChatChunk(BaseModel):
    message: DeltaMessage | None = None
    done: bool = False
    done_reason: str = ""
    error: str | None = None


class OllamaProvider:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def models(self) -> list[str]:
        try:
            response = await self.client.get("/api/tags", timeout=5)
            response.raise_for_status()
            entries = ModelList.model_validate(response.json()).models
            return [
                m.name
                for m in entries
                if m.size > 0
                and not m.remote_host
                and not m.remote_model
                and "cloud" not in m.name.lower()
            ]
        except (httpx.HTTPError, ValidationError, ValueError) as error:
            raise AppError(
                "OLLAMA_UNAVAILABLE",
                "Ollama indisponível ou resposta inválida. Inicie o serviço local.",
                503,
            ) from error

    async def validate_model(self, model: str) -> None:
        if model not in await self.models():
            raise AppError(
                "MODEL_UNAVAILABLE", "Escolha um modelo instalado localmente.", 422
            )
        try:
            response = await self.client.post(
                "/api/show", json={"model": model}, timeout=10
            )
            response.raise_for_status()
            details = ModelDetails.model_validate(response.json())
        except (httpx.HTTPError, ValidationError, ValueError) as error:
            raise AppError(
                "MODEL_UNAVAILABLE", "Não foi possível verificar o modelo local.", 503
            ) from error
        if details.remote_host or details.remote_model:
            raise AppError(
                "EXTERNAL_MODEL_BLOCKED",
                "Este marco permite somente modelos locais.",
                422,
            )
        if "completion" not in details.capabilities:
            raise AppError(
                "MODEL_UNSUPPORTED", "O modelo não declara suporte a conversas.", 422
            )

    async def chat(
        self, model: str, messages: list[dict[str, str]]
    ) -> AsyncIterator[str]:
        try:
            async with self.client.stream(
                "POST",
                "/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": True,
                    "think": False,
                    "options": {"num_ctx": 4096, "num_predict": 1024},
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if len(line) > 200_000:
                        raise AppError(
                            "INVALID_MODEL_RESPONSE",
                            "Resposta do modelo excedeu o limite.",
                            502,
                        )
                    chunk = ChatChunk.model_validate_json(line)
                    if chunk.error:
                        raise AppError(
                            "MODEL_FAILED",
                            "O modelo interrompeu a geração. O conteúdo parcial foi preservado.",
                            502,
                        )
                    if chunk.message and chunk.message.content:
                        yield chunk.message.content
                    if chunk.done:
                        if chunk.done_reason == "length":
                            raise AppError(
                                "OUTPUT_LIMIT",
                                "O modelo atingiu o limite de geração. A resposta parcial foi preservada.",
                                502,
                            )
                        return
            raise AppError(
                "STREAM_INTERRUPTED",
                "A conexão terminou sem confirmar a resposta completa.",
                502,
            )
        except httpx.TimeoutException as error:
            raise AppError(
                "MODEL_TIMEOUT",
                "O modelo excedeu o tempo de resposta. O conteúdo parcial foi preservado.",
                504,
            ) from error
        except (httpx.HTTPError, ValidationError, json.JSONDecodeError) as error:
            raise AppError(
                "INVALID_MODEL_RESPONSE",
                "Falha de comunicação ou resposta inválida do Ollama.",
                502,
            ) from error
