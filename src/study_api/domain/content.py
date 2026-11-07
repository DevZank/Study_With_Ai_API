from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Mode = Literal["study", "memorize", "learn", "practice"]
Text = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
]
Short = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)
]
BlockId = Annotated[str, StringConstraints(pattern=r"^[a-zA-Z0-9_-]{1,40}$")]


class SafeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Block(SafeModel):
    id: BlockId


class TextBlock(Block):
    type: Literal[
        "text",
        "explanation",
        "example",
        "hint",
        "summary",
        "curiosity",
        "check_question",
    ]
    text: Text


class CodeBlock(Block):
    type: Literal["code"]
    language: Short
    code: Text


class FormulaBlock(Block):
    type: Literal["formula"]
    latex: Annotated[str, StringConstraints(min_length=1, max_length=1000)]


class TableBlock(Block):
    type: Literal["table", "comparison"]
    columns: list[Short] = Field(min_length=1, max_length=8)
    rows: list[list[Short]] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def rectangular(self) -> Self:
        if any(len(row) != len(self.columns) for row in self.rows):
            raise ValueError("Tabela com quantidade de células inconsistente.")
        return self


class FlashcardBlock(Block):
    type: Literal["flashcard"]
    front: Text
    back: Text


class TimelineItem(SafeModel):
    label: Short
    text: Text


class TimelineBlock(Block):
    type: Literal["timeline"]
    items: list[TimelineItem] = Field(min_length=1, max_length=12)


class Edge(SafeModel):
    source: int = Field(ge=0, le=7)
    target: int = Field(ge=0, le=7)
    label: Short


class DiagramBlock(Block):
    type: Literal["diagram"]
    nodes: list[Short] = Field(min_length=1, max_length=8)
    edges: list[Edge] = Field(max_length=12)

    @model_validator(mode="after")
    def valid_edges(self) -> Self:
        if any(
            e.source >= len(self.nodes) or e.target >= len(self.nodes)
            for e in self.edges
        ):
            raise ValueError("Diagrama referencia nó inexistente.")
        return self


class SourceBlock(Block):
    type: Literal["source"]
    text: Literal["Conhecimento do modelo; nenhuma fonte externa foi consultada."]


class Choice(SafeModel):
    id: Annotated[str, StringConstraints(pattern=r"^[a-f]$")]
    text: Text


class GeneratedExercise(Block):
    type: Literal["quiz", "exercise"]
    kind: Literal["multiple_choice", "true_false", "fill_blank", "open"]
    prompt: Text
    options: list[Choice] = Field(max_length=6)
    answer_key: Text
    explanation: Text
    hints: list[Text] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def valid_answer(self) -> Self:
        ids = [o.id for o in self.options]
        if self.kind == "multiple_choice":
            if len(ids) < 2 or len(ids) != len(set(ids)) or self.answer_key not in ids:
                raise ValueError("Gabarito não corresponde a uma alternativa única.")
        elif self.options:
            raise ValueError("Somente múltipla escolha possui alternativas.")
        if self.kind == "true_false" and self.answer_key not in ("true", "false"):
            raise ValueError("Gabarito booleano inválido.")
        return self


class ExerciseRef(Block):
    type: Literal["quiz", "exercise"]
    exercise_id: str


CommonBlock = (
    TextBlock
    | CodeBlock
    | FormulaBlock
    | TableBlock
    | FlashcardBlock
    | TimelineBlock
    | DiagramBlock
    | SourceBlock
)
GeneratedBlock = Annotated[CommonBlock | GeneratedExercise, Field(discriminator="type")]
PublicBlock = Annotated[CommonBlock | ExerciseRef, Field(discriminator="type")]


class GeneratedDocument(SafeModel):
    schema_version: Literal["1.0"]
    mode: Mode
    title: Short
    blocks: list[GeneratedBlock] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def invariants(self) -> Self:
        ids = [b.id for b in self.blocks]
        if len(ids) != len(set(ids)):
            raise ValueError("IDs de blocos repetidos.")
        if sum(isinstance(b, GeneratedExercise) for b in self.blocks) > 3:
            raise ValueError("Limite de exercícios por resposta excedido.")
        if self.mode == "practice" and not any(
            isinstance(b, GeneratedExercise) for b in self.blocks
        ):
            raise ValueError("Praticar exige pelo menos um exercício.")
        if self.mode == "memorize" and not any(
            isinstance(b, FlashcardBlock) for b in self.blocks
        ):
            raise ValueError("Memorizar exige recuperação ativa.")
        if self.mode == "study" and not any(
            isinstance(b, TextBlock) and b.type == "explanation" for b in self.blocks
        ):
            raise ValueError("Estudar exige explicação.")
        if self.mode == "learn" and len(self.blocks) > 4:
            raise ValueError("Aprender deve ser breve.")
        return self


class PublicDocument(SafeModel):
    schema_version: Literal["1.0"]
    mode: Mode
    title: Short
    blocks: list[PublicBlock] = Field(min_length=1, max_length=12)
