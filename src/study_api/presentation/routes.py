import asyncio
from collections.abc import AsyncIterator
from hashlib import sha256
from typing import Annotated, TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from study_api.application.chat import ChatService
from study_api.domain.chat import AppError
from study_api.presentation.schemas import (
    ConversationView,
    JobView,
    MessageInput,
    MessageView,
    ModelsView,
    Page,
    StreamView,
    TopicInput,
    TopicPatch,
    TopicView,
)

router = APIRouter()


def service(request: Request) -> ChatService:
    value: ChatService = request.app.state.service
    return value


Service = Annotated[ChatService, Depends(service)]
Limit = Annotated[int, Query(ge=1, le=100)]
Cursor = Annotated[str | None, Query(max_length=36)]
T = TypeVar("T", TopicView, ConversationView, MessageView)


def page[T: (TopicView, ConversationView, MessageView)](
    items: list[T], limit: int, cursor: str | None
) -> Page[T]:
    start = 0
    if cursor:
        positions = [i for i, item in enumerate(items) if item.id == cursor]
        if not positions:
            raise AppError("INVALID_CURSOR", "Cursor inválido.", 422)
        start = positions[0] + 1
    chunk = items[start : start + limit]
    return Page(
        items=chunk,
        next_cursor=chunk[-1].id if chunk and start + limit < len(items) else None,
    )


@router.get("/topics")
async def topics(
    s: Service,
    limit: Limit = 100,
    cursor: Cursor = None,
    status: Annotated[str, Query(pattern="^(active|archived|deleted)$")] = "active",
    q: Annotated[str, Query(max_length=120)] = "",
) -> Page[TopicView]:
    rows = s.list_topics(status, q)
    return page([TopicView.model_validate(t) for t in rows], limit, cursor)


@router.post("/topics", status_code=201)
async def create_topic(body: TopicInput, s: Service) -> TopicView:
    return TopicView.model_validate(s.create_topic(body.title))


@router.get("/topics/{topic_id}")
async def topic(topic_id: UUID, s: Service) -> TopicView:
    return TopicView.model_validate(s.get_topic(str(topic_id)))


@router.patch("/topics/{topic_id}")
async def change_topic(topic_id: UUID, body: TopicPatch, s: Service) -> TopicView:
    if not body.model_fields_set or any(
        getattr(body, key) is None for key in body.model_fields_set
    ):
        raise AppError("EMPTY_PATCH", "Informe título ou estado válidos.", 422)
    return TopicView.model_validate(
        s.change_topic(str(topic_id), body.title, body.status)
    )


@router.delete("/topics/{topic_id}")
async def delete_topic(topic_id: UUID, s: Service) -> TopicView:
    return TopicView.model_validate(s.change_topic(str(topic_id), None, "deleted"))


@router.get("/topics/{topic_id}/conversations")
async def conversations(
    topic_id: UUID, s: Service, limit: Limit = 100, cursor: Cursor = None
) -> Page[ConversationView]:
    return page(
        [
            ConversationView.model_validate(c)
            for c in s.list_conversations(str(topic_id))
        ],
        limit,
        cursor,
    )


@router.post("/topics/{topic_id}/conversations", status_code=201)
async def create_conversation(
    topic_id: UUID, s: Service, body: TopicInput
) -> ConversationView:
    return ConversationView.model_validate(
        s.create_conversation(str(topic_id), body.title)
    )


@router.get("/conversations/{conversation_id}/messages")
async def messages(
    conversation_id: UUID, s: Service, limit: Limit = 100, cursor: Cursor = None
) -> Page[MessageView]:
    return page(
        [MessageView.model_validate(m) for m in s.history(str(conversation_id))],
        limit,
        cursor,
    )


@router.post("/conversations/{conversation_id}/messages", status_code=202)
async def send_message(
    conversation_id: UUID, body: MessageInput, s: Service
) -> JobView:
    return JobView.model_validate(
        await s.start(
            str(conversation_id), body.content, body.model_id, str(body.request_id)
        )
    )


@router.get("/conversations/{conversation_id}/jobs")
async def conversation_jobs(conversation_id: UUID, s: Service) -> list[JobView]:
    return [JobView.model_validate(j) for j in s.jobs_for(str(conversation_id))]


@router.get("/ai/models")
async def models(s: Service) -> ModelsView:
    return ModelsView(models=await s.models())


@router.get("/jobs/{job_id}")
async def job(job_id: UUID, s: Service) -> JobView:
    return JobView.model_validate(s.get_job(str(job_id)))


@router.post("/jobs/{job_id}/cancel")
async def cancel(job_id: UUID, s: Service) -> JobView:
    return JobView.model_validate(await s.cancel(str(job_id)))


@router.get("/jobs/{job_id}/events")
async def events(job_id: UUID, s: Service, request: Request) -> StreamingResponse:
    s.get_job(str(job_id))

    async def stream() -> AsyncIterator[str]:
        previous = ""
        while not await request.is_disconnected():
            current = s.get_job(str(job_id))
            message = s.get_message(current.message_id)
            fingerprint = sha256(
                (current.status + message.content).encode()
            ).hexdigest()[:20]
            if fingerprint != previous:
                name = (
                    ("job.started" if not previous else "generation.delta")
                    if current.status == "running"
                    else "job." + current.status
                )
                data = StreamView(
                    event_id=fingerprint,
                    job_id=current.id,
                    job=JobView.model_validate(current),
                    message=MessageView.model_validate(message),
                )
                yield f"id: {fingerprint}\nevent: {name}\ndata: {data.model_dump_json()}\n\n"
                previous = fingerprint
            else:
                yield ": aguardando\n\n"
            if current.status != "running":
                break
            await asyncio.sleep(0.2)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
