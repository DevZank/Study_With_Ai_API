import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from study_api.application import trail_generation
from study_api.application.trail_service import TrailService
from study_api.domain.chat import AppError
from study_api.domain.trails import (
    ContentVersion,
    LearningSummary,
    Module,
    ModulePlan,
    Trail,
    TrailJob,
    Unit,
)
from study_api.presentation.schemas import Input, MessageView, Prompt, Title

router = APIRouter()


def service(request: Request) -> TrailService:
    value: TrailService = request.app.state.trails
    return value


S = Annotated[TrailService, Depends(service)]


class PlanInput(Input):
    topic_id: UUID
    objective: Prompt
    prior_knowledge: Annotated[str, Field(max_length=1000)] = ""
    preferences: Annotated[str, Field(max_length=1000)] = ""
    module_count: int = Field(default=5, ge=1, le=8)
    model_id: Annotated[str, Field(min_length=1, max_length=200)]
    request_id: UUID


class EditInput(Input):
    expected_version: int = Field(ge=1)
    title: Title


class ModuleInput(Input):
    expected_version: int = Field(ge=1)
    plan: ModulePlan


class ModulePatch(Input):
    expected_version: int = Field(ge=1)
    plan: ModulePlan | None = None
    archived: bool | None = None


class OrderInput(Input):
    expected_version: int = Field(ge=1)
    module_ids: list[UUID] = Field(min_length=1, max_length=8)


class GenerateInput(Input):
    model_id: Annotated[str, Field(min_length=1, max_length=200)]
    request_id: UUID
    unit_id: UUID | None = None
    granularity: Literal["auto"] = "auto"
    force_regenerate: bool = False


class CompleteInput(Input):
    version_id: UUID
    difficulties: Annotated[str, Field(max_length=1000)] = ""
    model_id: Annotated[str, Field(min_length=1, max_length=200)]
    request_id: UUID


class UnitView(BaseModel):
    unit: Unit
    versions: list[ContentVersion]
    summaries: list[LearningSummary]


class ModuleView(BaseModel):
    module: Module
    units: list[UnitView]


class TrailView(BaseModel):
    trail: Trail
    modules: list[ModuleView]
    completed_units: int
    total_units: int


class VersionView(BaseModel):
    version: ContentVersion
    message: MessageView
    summaries: list[LearningSummary]
    stale: bool


def view(s: TrailService, trail_id: str) -> TrailView:
    trail = s.trail(trail_id)
    modules = []
    total = 0
    for module in s.modules(trail_id):
        units = []
        for unit in s.units(module.id):
            versions = s.versions(unit.id)
            units.append(
                UnitView(
                    unit=unit,
                    versions=versions,
                    summaries=s.summaries(versions[-1].id) if versions else [],
                )
            )
        if not module.archived:
            total += len(units)
        modules.append(ModuleView(module=module, units=units))
    return TrailView(
        trail=trail,
        modules=modules,
        completed_units=s.completed_count(trail_id),
        total_units=total,
    )


@router.post("/trails/plan", status_code=202)
async def plan(body: PlanInput, s: S) -> TrailJob:
    return await trail_generation.plan(
        s,
        str(body.topic_id),
        body.objective,
        body.prior_knowledge,
        body.preferences,
        body.module_count,
        body.model_id,
        str(body.request_id),
    )


@router.get("/topics/{topic_id}/trails")
async def list_trails(
    topic_id: UUID,
    s: S,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    cursor: str | None = None,
) -> dict[str, object]:
    s.chat.topic(str(topic_id))
    rows = s.repo.all(Trail, ("topic_id", str(topic_id)))
    start = 0
    if cursor:
        indices = [i for i, t in enumerate(rows) if t.id == cursor]
        if not indices:
            raise AppError("INVALID_CURSOR", "Cursor inválido.", 422)
        start = indices[0] + 1
    items = rows[start : start + limit]
    return {
        "items": items,
        "next_cursor": items[-1].id if items and start + limit < len(rows) else None,
    }


@router.get("/trails/{trail_id}")
async def trail(trail_id: UUID, s: S) -> TrailView:
    return view(s, str(trail_id))


@router.patch("/trails/{trail_id}")
async def edit(trail_id: UUID, body: EditInput, s: S) -> TrailView:
    s.edit(str(trail_id), body.expected_version, title=body.title)
    return view(s, str(trail_id))


@router.post("/trails/{trail_id}/modules", status_code=201)
async def add_module(trail_id: UUID, body: ModuleInput, s: S) -> TrailView:
    s.edit(str(trail_id), body.expected_version, plan=body.plan)
    return view(s, str(trail_id))


@router.patch("/modules/{module_id}")
async def edit_module(module_id: UUID, body: ModulePatch, s: S) -> TrailView:
    if body.plan is None and body.archived is None:
        raise AppError("EMPTY_PATCH", "Informe os campos a alterar.", 422)
    module = s.repo.get(Module, str(module_id))
    s.edit(
        module.trail_id,
        body.expected_version,
        module_id=module.id,
        plan=body.plan,
        archived=body.archived,
    )
    return view(s, module.trail_id)


@router.patch("/trails/{trail_id}/modules/order")
async def order(trail_id: UUID, body: OrderInput, s: S) -> TrailView:
    s.edit(
        str(trail_id), body.expected_version, order=[str(i) for i in body.module_ids]
    )
    return view(s, str(trail_id))


@router.get("/modules/{module_id}/lessons")
async def units(module_id: UUID, s: S) -> list[Unit]:
    return s.units(str(module_id))


@router.post("/modules/{module_id}/generate", status_code=202)
async def generate(module_id: UUID, body: GenerateInput, s: S) -> TrailJob:
    return await trail_generation.generate(
        s,
        str(module_id),
        str(body.unit_id) if body.unit_id else None,
        body.force_regenerate,
        body.model_id,
        str(body.request_id),
    )


@router.get("/units/{unit_id}/versions/{version_id}")
async def version(unit_id: UUID, version_id: UUID, s: S) -> VersionView:
    versions = s.versions(str(unit_id))
    version = next((v for v in versions if v.id == str(version_id)), None)
    if version is None:
        raise AppError("NOT_FOUND", "Versão não encontrada.", 404)
    module = s.repo.get(Module, s.repo.get(Unit, str(unit_id)).module_id)
    trail = s.trail(module.trail_id)
    return VersionView(
        version=version,
        message=MessageView.model_validate(s.chat.get_message(version.message_id)),
        summaries=s.summaries(version.id),
        stale=version.plan_version != trail.version
        or version.context != s.context(str(unit_id)),
    )


@router.post("/units/{unit_id}/complete", status_code=202)
async def complete(unit_id: UUID, body: CompleteInput, s: S) -> TrailJob:
    return await trail_generation.complete(
        s,
        str(unit_id),
        str(body.version_id),
        body.difficulties,
        body.model_id,
        str(body.request_id),
    )


@router.get("/trails/{trail_id}/jobs")
async def jobs(trail_id: UUID, s: S) -> list[TrailJob]:
    s.trail(str(trail_id))
    return [j for j in s.repo.all(TrailJob) if j.trail_id == str(trail_id)][-30:]


@router.get("/topics/{topic_id}/trail-jobs")
async def topic_jobs(topic_id: UUID, s: S) -> list[TrailJob]:
    s.chat.topic(str(topic_id))
    ids = {t.id for t in s.repo.all(Trail, ("topic_id", str(topic_id)))}
    return [
        j
        for j in s.repo.all(TrailJob)
        if j.trail_id in ids or (j.kind == "plan" and j.target_id == str(topic_id))
    ][-30:]


@router.get("/trail-jobs/{job_id}")
async def job(job_id: UUID, s: S) -> TrailJob:
    return s.repo.get(TrailJob, str(job_id))


@router.post("/trail-jobs/{job_id}/cancel")
async def cancel(job_id: UUID, s: S) -> TrailJob:
    return await s.cancel(str(job_id))


@router.get("/trail-jobs/{job_id}/events")
async def events(job_id: UUID, s: S, request: Request) -> StreamingResponse:
    s.repo.get(TrailJob, str(job_id))

    async def stream() -> AsyncIterator[str]:
        previous = ""
        while not await request.is_disconnected():
            current = s.repo.get(TrailJob, str(job_id))
            data = current.model_dump_json()
            if data != previous:
                name = (
                    "job.started"
                    if current.status == "running"
                    else "job." + current.status
                )
                yield (
                    "event: "
                    + name
                    + "\ndata: "
                    + json.dumps({"job": current.model_dump()}, ensure_ascii=False)
                    + "\n\n"
                )
                previous = data
            else:
                yield ": aguardando\n\n"
            if current.status != "running":
                break
            await asyncio.sleep(0.2)

    return StreamingResponse(
        stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"}
    )
