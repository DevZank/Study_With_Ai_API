import asyncio
import json
from collections.abc import Awaitable, Callable
from hashlib import sha256
from typing import Literal

from study_api.application.chat import ChatService
from study_api.domain.chat import AppError, Provider
from study_api.domain.trails import (
    ContentVersion,
    LearningSummary,
    Module,
    ModulePlan,
    Stored,
    Trail,
    TrailJob,
    TrailRepository,
    Unit,
    granularity,
    outline,
)


class TrailService:
    def __init__(
        self, repo: TrailRepository, chat: ChatService, provider: Provider
    ) -> None:
        self.repo, self.chat, self.provider = repo, chat, provider
        self.tasks: dict[str, asyncio.Task[None]] = {}

    def trail(self, trail_id: str, write: bool = False) -> Trail:
        trail = self.repo.get(Trail, trail_id)
        topic = self.chat.topic(trail.topic_id)
        if write and topic.status != "active":
            raise AppError(
                "TOPIC_ARCHIVED", "Restaure o tema antes de alterar a trilha.", 409
            )
        return trail

    def modules(self, trail_id: str) -> list[Module]:
        self.trail(trail_id)
        return sorted(
            self.repo.all(Module, ("trail_id", trail_id)), key=lambda m: m.position
        )

    def units(self, module_id: str) -> list[Unit]:
        module = self.repo.get(Module, module_id)
        self.trail(module.trail_id)
        return sorted(
            self.repo.all(Unit, ("module_id", module_id)), key=lambda u: u.position
        )

    def versions(self, unit_id: str) -> list[ContentVersion]:
        unit = self.repo.get(Unit, unit_id)
        self.trail(self.repo.get(Module, unit.module_id).trail_id)
        return sorted(
            self.repo.all(ContentVersion, ("unit_id", unit_id)), key=lambda v: v.number
        )

    def summaries(self, version_id: str) -> list[LearningSummary]:
        version = self.repo.get(ContentVersion, version_id)
        self.versions(version.unit_id)
        return self.repo.all(LearningSummary, ("version_id", version_id))

    def editable(self, trail_id: str, expected: int) -> Trail:
        trail = self.trail(trail_id, True)
        if trail.version != expected:
            raise AppError(
                "STALE_PLAN", "O plano mudou. Atualize antes de salvar.", 409
            )
        if any(
            j.trail_id == trail_id and j.status == "running"
            for j in self.repo.all(TrailJob)
        ):
            raise AppError(
                "TRAIL_BUSY", "Aguarde ou cancele a operação antes de editar.", 409
            )
        return trail

    def edit(
        self,
        trail_id: str,
        expected: int,
        title: str | None = None,
        module_id: str | None = None,
        plan: ModulePlan | None = None,
        archived: bool | None = None,
        order: list[str] | None = None,
    ) -> Trail:
        trail = self.editable(trail_id, expected)
        records: list[Stored] = []
        if title is not None:
            trail.title = title
        if order is not None:
            active = [m for m in self.modules(trail_id) if not m.archived]
            if len(set(order)) != len(order) or set(order) != {m.id for m in active}:
                raise AppError(
                    "INVALID_ORDER", "Envie todos os módulos ativos uma única vez.", 422
                )
            for m in active:
                m.position = order.index(m.id)
                records.append(m)
        elif plan is not None or module_id is not None:
            if module_id:
                module = self.repo.get(Module, module_id)
                if module.trail_id != trail_id:
                    raise AppError("NOT_FOUND", "Módulo não pertence à trilha.", 404)
                if plan is not None:
                    # A estrutura de unidades existentes é preservada; a revisão indica conteúdo antigo.
                    module.plan = plan
                if archived is not None:
                    if (
                        not archived
                        and module.archived
                        and len([m for m in self.modules(trail_id) if not m.archived])
                        >= 8
                    ):
                        raise AppError(
                            "MODULE_LIMIT", "Limite de oito módulos ativos.", 422
                        )
                    if not archived and module.archived:
                        module.position = (
                            max(
                                (m.position for m in self.modules(trail_id)), default=-1
                            )
                            + 1
                        )
                    module.archived = archived
            else:
                if (
                    len([m for m in self.modules(trail_id) if not m.archived]) >= 8
                    or plan is None
                ):
                    raise AppError(
                        "MODULE_LIMIT", "Limite de oito módulos ativos.", 422
                    )
                module = Module(
                    trail_id=trail_id,
                    position=len(self.modules(trail_id)),
                    plan=plan,
                    granularity=granularity(plan),
                )
                records.extend([module, *outline(module)])
            if module not in records:
                records.append(module)
        trail.version += 1
        self.repo.commit([trail, *records], guard=(trail.id, expected))
        return trail

    def context(self, unit_id: str) -> str:
        unit = self.repo.get(Unit, unit_id)
        module = self.repo.get(Module, unit.module_id)
        trail = self.trail(module.trail_id)
        selected: list[dict[str, object]] = []
        for previous_module in self.modules(trail.id):
            if previous_module.archived:
                continue
            for previous in self.units(previous_module.id):
                if (previous_module.position, previous.position) >= (
                    module.position,
                    unit.position,
                ):
                    continue
                versions = self.versions(previous.id)
                summaries = self.summaries(versions[-1].id) if versions else []
                if summaries:
                    s = summaries[-1]
                    selected.append(
                        {
                            "summary_id": s.id,
                            "concepts": s.content.concepts,
                            "conclusions": s.content.conclusions,
                            "difficulties": s.difficulties,
                            "next_steps": s.content.next_steps,
                        }
                    )
        eligible = len(selected)
        selected = selected[-3:]
        while selected and len(json.dumps(selected, ensure_ascii=False)) > 4500:
            selected.pop(0)
        return json.dumps(
            {
                "schema_version": "1.0",
                "previous_summaries": selected,
                "omitted_summaries": max(0, eligible - len(selected)),
            },
            ensure_ascii=False,
        )

    def completed_count(self, trail_id: str) -> int:
        count = 0
        for m in self.modules(trail_id):
            if m.archived:
                continue
            for u in self.units(m.id):
                versions = self.versions(u.id)
                if versions and self.summaries(versions[-1].id):
                    count += 1
        return count

    async def launch(
        self,
        kind: Literal["plan", "unit", "summary"],
        target: str,
        model: str,
        request_id: str,
        payload: str,
        run: Callable[[TrailJob], Awaitable[None]],
        trail_id: str = "",
    ) -> TrailJob:
        fingerprint = sha256((kind + target + model + payload).encode()).hexdigest()

        def previous() -> TrailJob | None:
            for j in self.repo.all(TrailJob):
                if j.request_id == request_id:
                    if j.fingerprint != fingerprint:
                        raise AppError(
                            "IDEMPOTENCY_CONFLICT",
                            "Identificador já usado com outra operação.",
                            409,
                        )
                    return j
            return None

        prior = previous()
        if prior:
            return prior
        await self.provider.validate_model(model)
        prior = previous()
        if prior:
            return prior
        if len(self.tasks) >= 2:
            raise AppError(
                "TRAIL_CAPACITY", "Há duas operações em andamento. Aguarde.", 409
            )
        job = TrailJob(
            kind=kind,
            target_id=target,
            model_id=model,
            request_id=request_id,
            fingerprint=fingerprint,
            trail_id=trail_id,
        )
        self.repo.commit([job])
        task = asyncio.create_task(self._run(job, run))
        self.tasks[job.id] = task
        task.add_done_callback(self.chat._task_done)
        return job

    async def _run(
        self, job: TrailJob, run: Callable[[TrailJob], Awaitable[None]]
    ) -> None:
        try:
            async with asyncio.timeout(200):
                await run(job)
            job.status = "completed"
        except asyncio.CancelledError:
            if job.child_job_id:
                await self.chat.cancel(job.child_job_id)
            job.status = "cancelled"
        except TimeoutError:
            if job.child_job_id:
                await self.chat.cancel(job.child_job_id)
            job.status, job.error_code, job.error_message = (
                "failed",
                "TRAIL_TIMEOUT",
                "Tempo máximo excedido; dados anteriores preservados.",
            )
        except AppError as error:
            job.status, job.error_code, job.error_message = (
                "failed",
                error.code,
                error.message,
            )
        finally:
            if job.status == "running":
                job.status, job.error_code, job.error_message = (
                    "interrupted",
                    "TRAIL_INTERRUPTED",
                    "Operação interrompida inesperadamente.",
                )
            self.repo.commit([job])
            self.tasks.pop(job.id, None)

    async def cancel(self, job_id: str) -> TrailJob:
        job = self.repo.get(TrailJob, job_id)
        task = self.tasks.get(job.id)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                job.status = "cancelled"
                self.repo.commit([job])
                self.tasks.pop(job.id, None)
        return self.repo.get(TrailJob, job_id)

    def recover(self) -> None:
        for job in self.repo.all(TrailJob):
            if job.status == "running":
                job.status, job.error_code, job.error_message = (
                    "interrupted",
                    "SERVER_RESTARTED",
                    "Operação interrompida pelo reinício.",
                )
                self.repo.commit([job])

    async def close(self) -> None:
        for job_id in list(self.tasks):
            await self.cancel(job_id)
