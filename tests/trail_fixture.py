"""Planos e resumos sintéticos, usados exclusivamente em testes."""

from content_fixture import generated

from study_api.domain.content import GeneratedDocument


def plan_payload(count: int = 5) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "title": "Trilha de teste",
        "prerequisites": ["Operações básicas"],
        "modules": [
            {
                "title": f"Etapa {i + 1}",
                "objectives": [f"Compreender conceito {i + 1}"],
                "criteria": ["Responder uma questão e registrar dificuldades."],
                "estimated_minutes": 60 if i == 1 else 20,
                "lesson_titles": [f"Aula {i + 1}.1", f"Aula {i + 1}.2"],
            }
            for i in range(count)
        ],
    }


def summary_payload() -> dict[str, object]:
    return {
        "concepts": ["Soma"],
        "conclusions": ["Somas combinam quantidades."],
        "next_steps": ["Revisar o exemplo e continuar quando desejar."],
    }


def lesson_payload() -> dict[str, object]:
    value = generated("study", "Explicação da unidade")
    blocks = [b.model_dump() for b in GeneratedDocument.model_validate(value).blocks]
    exercise = generated("practice")

    question = GeneratedDocument.model_validate(exercise).blocks[0].model_dump()
    value["blocks"] = [blocks[0], question]
    return value
