"""Provedor determinístico exclusivo dos testes E2E; nunca usado pela aplicação."""

import asyncio
import json
import os
from collections.abc import AsyncIterator
from pathlib import Path

import uvicorn
from alembic.config import Config
from content_fixture import generated, prompt_mode

from alembic import command
from study_api.domain.chat import AppError
from study_api.main import create_app


class E2EProvider:
    async def models(self) -> list[str]:
        return ["e2e:local"]

    async def validate_model(self, model: str) -> None:
        if model != "e2e:local":
            raise AppError("MODEL_UNAVAILABLE", "Modelo de teste indisponível.", 422)

    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        response_schema: dict[str, object] | None = None,
    ) -> AsyncIterator[str]:
        if response_schema is not None:
            prompt = next(
                m["content"] for m in reversed(messages) if m["role"] == "user"
            )
            if "inválido" in prompt.lower():
                yield '{"answer_key":"SEGREDO_NAO_EXIBIR"'
                return
            raw = json.dumps(
                generated(
                    prompt_mode(messages),
                    prompt,
                    "open" if "aberta" in prompt.lower() else "multiple_choice",
                ),
                ensure_ascii=False,
            )
            yield raw[:20]
            if "cancelar" in prompt.lower():
                await asyncio.sleep(30)
            if "falha" in prompt.lower():
                raise AppError(
                    "STREAM_INTERRUPTED", "Falha simulada somente no teste.", 502
                )
            await asyncio.sleep(0.4)
            yield raw[20:]
            return
        yield "Conteúdo de teste para " + messages[-1]["content"]
        if "cancelar" in messages[-1]["content"].lower():
            await asyncio.sleep(30)
        if "falha" in messages[-1]["content"].lower():
            raise AppError(
                "STREAM_INTERRUPTED", "Falha simulada somente no teste.", 502
            )
        await asyncio.sleep(0.4)
        yield " — concluído."


if __name__ == "__main__":
    if not os.environ.get("STUDY_DB_PATH"):
        raise RuntimeError("Defina um banco temporário exclusivo para o teste.")
    root = Path(__file__).resolve().parents[1]
    command.upgrade(Config(str(root / "alembic.ini")), "head")
    uvicorn.run(
        create_app(provider=E2EProvider()),
        host="127.0.0.1",
        port=int(os.environ.get("STUDY_API_PORT", "8000")),
        access_log=False,
    )
