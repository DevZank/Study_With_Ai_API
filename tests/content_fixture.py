"""Respostas sintéticas usadas somente para validar contratos e interface."""

import re


def generated(
    mode: str, prompt: str = "Teste", kind: str = "multiple_choice"
) -> dict[str, object]:
    blocks: list[dict[str, object]]
    if mode == "practice":
        blocks = [
            {
                "id": "q1",
                "type": "exercise",
                "kind": kind,
                "prompt": "Quanto é 2 + 2?"
                if kind != "open"
                else "Explique o que é uma célula.",
                "options": [{"id": "a", "text": "3"}, {"id": "b", "text": "4"}]
                if kind == "multiple_choice"
                else [],
                "answer_key": {
                    "multiple_choice": "b",
                    "true_false": "true",
                    "fill_blank": "quatro",
                    "open": "Uma célula é uma unidade estrutural e funcional dos seres vivos.",
                }[kind],
                "explanation": "Referência sintética exclusiva do teste.",
                "hints": [
                    "Pense na soma de duas duplas.",
                    "Conte dois objetos e acrescente outros dois.",
                ],
            }
        ]
    elif mode == "memorize":
        blocks = [
            {
                "id": "f1",
                "type": "flashcard",
                "front": "Qual é a soma de duas duplas?",
                "back": "Quatro.",
            }
        ]
    elif mode == "study":
        blocks = [
            {
                "id": "t1",
                "type": "explanation",
                "text": "Fundamentos e conexões: " + prompt,
            },
            {"id": "m1", "type": "formula", "latex": "2 + 2 = 4"},
            {
                "id": "table1",
                "type": "table",
                "columns": ["Conceito", "Exemplo"],
                "rows": [["Soma", "2 + 2"]],
            },
            {
                "id": "d1",
                "type": "diagram",
                "nodes": ["Parcelas", "Soma"],
                "edges": [{"source": 0, "target": 1, "label": "produzem"}],
            },
        ]
    else:
        blocks = [
            {
                "id": "t1",
                "type": "explanation",
                "text": "Conteúdo de teste para " + prompt + " — concluído.",
            }
        ]
    return {
        "schema_version": "1.0",
        "mode": mode,
        "title": "Resposta de teste · " + mode,
        "blocks": blocks,
    }


def prompt_mode(messages: list[dict[str, str]]) -> str:
    match = re.search(r"mode=(study|memorize|learn|practice)", messages[0]["content"])
    return match[1] if match else "learn"
