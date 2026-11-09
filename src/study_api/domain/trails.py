from typing import Literal, Protocol, TypeVar

from pydantic import Field

from study_api.domain.chat import LOCAL_PROFILE_ID, new_id, now
from study_api.domain.content import SafeModel, Short


class ModulePlan(SafeModel):
    title: Short
    objectives: list[Short] = Field(min_length=1, max_length=6)
    criteria: list[Short] = Field(min_length=1, max_length=4)
    estimated_minutes: int = Field(ge=5, le=180)
    lesson_titles: list[Short] = Field(min_length=1, max_length=6)


class GeneratedPlan(SafeModel):
    schema_version: Literal["1.0"]
    title: Short
    prerequisites: list[Short] = Field(max_length=6)
    modules: list[ModulePlan] = Field(min_length=1, max_length=8)


class GeneratedSummary(SafeModel):
    concepts: list[Short] = Field(min_length=1, max_length=6)
    conclusions: list[Short] = Field(min_length=1, max_length=6)
    next_steps: list[Short] = Field(min_length=1, max_length=4)


class Stored(SafeModel):
    id: str = Field(default_factory=new_id)
    owner_id: str = LOCAL_PROFILE_ID
    created_at: str = Field(default_factory=now)
    updated_at: str = Field(default_factory=now)


class Trail(Stored):
    topic_id: str
    title: str
    objective: str
    prior_knowledge: str
    preferences: str
    prerequisites: list[str]
    version: int = 1


class Module(Stored):
    trail_id: str
    position: int
    plan: ModulePlan
    archived: bool = False
    granularity: Literal["module", "lesson"] = "module"


class Unit(Stored):
    module_id: str
    position: int
    title: str


class ContentVersion(Stored):
    unit_id: str
    number: int
    message_id: str
    model_id: str
    plan_version: int
    context: str


class LearningSummary(Stored):
    version_id: str
    content: GeneratedSummary
    difficulties: str
    objective_attempts: int
    matching_answers: int
    mastery_estimate: None = None


class TrailJob(Stored):
    kind: Literal["plan", "unit", "summary"]
    target_id: str
    trail_id: str = ""
    model_id: str
    request_id: str
    fingerprint: str
    status: Literal["running", "completed", "failed", "cancelled", "interrupted"] = (
        "running"
    )
    result_id: str = ""
    error_code: str = ""
    error_message: str = ""
    child_job_id: str = ""
    cached: bool = False


RecordType = Trail | Module | Unit | ContentVersion | LearningSummary | TrailJob
R = TypeVar("R", bound=Stored)


class TrailRepository(Protocol):
    def get(self, cls: type[R], record_id: str) -> R: ...
    def all(self, cls: type[R], parent: tuple[str, str] | None = None) -> list[R]: ...
    def commit(
        self, records: list[Stored], guard: tuple[str, int] | None = None
    ) -> None: ...


def granularity(plan: ModulePlan) -> Literal["module", "lesson"]:
    return (
        "lesson"
        if plan.estimated_minutes > 25 or len(plan.objectives) > 3
        else "module"
    )


def outline(module: Module) -> list[Unit]:
    titles = (
        module.plan.lesson_titles
        if module.granularity == "lesson"
        else [module.plan.title]
    )
    return [
        Unit(module_id=module.id, title=title, position=i)
        for i, title in enumerate(titles)
    ]
