import json
import logging
from dataclasses import replace

from pydantic import ValidationError

from study_api.domain.chat import AppError, Job, Message, Provider, Repository
from study_api.domain.content import (
    ExerciseRef,
    GeneratedDocument,
    GeneratedExercise,
    PublicBlock,
    PublicDocument,
    TextBlock,
)
from study_api.domain.exercises import Exercise


async def generate_blocks(
    provider: Provider,
    repo: Repository,
    job: Job,
    message: Message,
    prompts: list[dict[str, str]],
) -> None:
    schema = GeneratedDocument.model_json_schema()
    schema["properties"]["mode"] = {"type": "string", "const": message.mode}
    schema["properties"]["blocks"]["maxItems"] = 4
    if message.response_format == "lesson":
        schema["properties"]["blocks"]["items"] = {
            "anyOf": [
                {"$ref": "#/$defs/TextBlock"},
                {"$ref": "#/$defs/GeneratedExercise"},
            ]
        }
    if message.mode in ("memorize", "practice"):
        name = "FlashcardBlock" if message.mode == "memorize" else "GeneratedExercise"
        schema["properties"]["blocks"]["items"] = {"$ref": "#/$defs/" + name}
        schema["properties"]["blocks"]["maxItems"] = 3
    schema = compact_schema(schema)
    for retry in range(2):
        raw = ""
        async for delta in provider.chat(job.model_id, prompts, schema):
            raw += delta
            if len(raw) > 50_000:
                raise AppError(
                    "OUTPUT_LIMIT",
                    "A resposta excedeu o limite de conteúdo estruturado.",
                )
        try:
            document = GeneratedDocument.model_validate_json(raw)
            if document.mode != message.mode:
                raise ValueError("Modo gerado difere do modo solicitado.")
            if message.response_format == "lesson" and not any(
                isinstance(b, GeneratedExercise) for b in document.blocks
            ):
                raise ValueError(
                    "A unidade exige explicação e pelo menos um quiz ou exercício."
                )
        except (ValidationError, ValueError) as error:
            detail = (
                str(error)
                if not isinstance(error, ValidationError)
                else "; ".join(
                    str(e["loc"]) + ": " + e["msg"]
                    for e in error.errors(
                        include_input=False, include_context=False, include_url=False
                    )[:4]
                )
            )
            logging.getLogger("study_api").warning(
                json.dumps(
                    {
                        "event": "content_validation_failed",
                        "job_id": job.id,
                        "request_id": job.request_id,
                        "retry": retry,
                        "error_types": [
                            e["type"] for e in error.errors(include_input=False)
                        ]
                        if isinstance(error, ValidationError)
                        else ["mode_mismatch"],
                    }
                )
            )
            if retry == 0:
                prompts = prompts + [
                    {
                        "role": "system",
                        "content": "A resposta anterior não passou na validação: "
                        + detail
                        + ". Gere novamente JSON estritamente conforme o schema para mode="
                        + message.mode
                        + ". Não inclua texto fora do JSON.",
                    }
                ]
                continue
            message.content = "Não foi possível organizar a resposta com segurança. Envie a pergunta novamente."
            message.notice = (
                "O conteúdo inválido foi ocultado; nenhum exercício foi salvo."
            )
            raise AppError(
                "INVALID_CONTENT",
                "O modelo não produziu conteúdo válido após uma tentativa de correção.",
                502,
            )
        exercises: list[Exercise] = []
        blocks: list[PublicBlock] = []
        summaries = [document.title]
        for block in document.blocks:
            if isinstance(block, GeneratedExercise):
                exercise = Exercise(
                    message.id,
                    block.kind,
                    block.prompt,
                    json.dumps(
                        [o.model_dump() for o in block.options], ensure_ascii=False
                    ),
                    block.answer_key,
                    block.explanation,
                    json.dumps(block.hints, ensure_ascii=False),
                )
                exercises.append(exercise)
                blocks.append(
                    ExerciseRef(type=block.type, id=block.id, exercise_id=exercise.id)
                )
                summaries.append(block.prompt)
            else:
                blocks.append(block)
                if isinstance(block, TextBlock):
                    summaries.append(block.text)
        public = PublicDocument(
            schema_version="1.0", mode=message.mode, title=document.title, blocks=blocks
        )
        notice = (
            "Conteúdo reorganizado após uma nova tentativa de validação."
            if retry
            else ""
        )
        result = replace(
            message,
            document_json=public.model_dump_json(),
            content="\n\n".join(summaries),
            notice=notice,
            status="completed",
        )
        finished = replace(job, status="completed")
        repo.save_result(finished, result, exercises)
        # Só confirma o estado em memória depois do commit atômico de documento e exercícios.
        message.document_json, message.content, message.notice = (
            result.document_json,
            result.content,
            result.notice,
        )
        job.status = message.status = "completed"
        return


def compact_schema(schema: dict[str, object]) -> dict[str, object]:
    # Definições não alcançáveis aumentam o trabalho da gramática sem ajudar o modelo.
    definitions = schema.pop("$defs", {})
    if not isinstance(definitions, dict):
        return schema
    needed: set[str] = set()

    def visit(value: object) -> None:
        if isinstance(value, dict):
            ref = value.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/$defs/"):
                name = ref.removeprefix("#/$defs/")
                if name not in needed:
                    needed.add(name)
                    visit(definitions.get(name))
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(schema)
    schema["$defs"] = {name: definitions[name] for name in sorted(needed)}
    return schema
