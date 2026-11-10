"""Rotas HTTP para flashcards, revisão FSRS, métricas pedagógicas e gamificação."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from study_api.application.progress import ProgressService
from study_api.domain.progress import (
    Flashcard,
    ProgressPreference,
    Rating,
    ReviewEvent,
    ReviewState,
    parse_utc,
    retrievability_at,
)
from study_api.presentation.schemas import Input, Prompt

router = APIRouter()


def service(request: Request) -> ProgressService:
    value: ProgressService = request.app.state.progress
    return value


S = Annotated[ProgressService, Depends(service)]


class FlashcardCreateInput(Input):
    front: Prompt
    back: Prompt
    concept_name: Annotated[str, Field(max_length=160)] = ""
    operation_id: UUID
    created_at: Annotated[str | None, Field(max_length=64)] = None


class FlashcardImportInput(Input):
    block_id: Annotated[str, Field(min_length=1, max_length=40)]
    concept_name: Annotated[str, Field(max_length=160)] = ""
    operation_id: UUID


class FlashcardPatchInput(Input):
    front: Prompt
    back: Prompt
    concept_name: Annotated[str, Field(max_length=160)] = ""
    archived: bool = False
    expected_version: int = Field(ge=1)
    operation_id: UUID


class ReviewGradeInput(Input):
    rating: Rating
    request_id: UUID
    reviewed_at: Annotated[str | None, Field(max_length=64)] = None


class PreferenceInput(Input):
    hide_gamification: bool


class FlashcardView(BaseModel):
    card: Flashcard
    review_state: ReviewState
    estimated_retention: float | None = None
    due: bool = True


class ReviewGradeView(BaseModel):
    card: Flashcard
    review_state: ReviewState
    event: ReviewEvent


def _card_view(
    card: Flashcard, state: ReviewState, ref_time: str | None = None
) -> FlashcardView:
    effective = ref_time or state.updated_at
    due = not card.archived and parse_utc(state.due_at) <= parse_utc(effective)
    return FlashcardView(
        card=card,
        review_state=state,
        estimated_retention=retrievability_at(state, effective),
        due=due,
    )


@router.get("/topics/{topic_id}/flashcards")
async def list_flashcards(
    topic_id: UUID,
    s: S,
    include_archived: bool = False,
    at: Annotated[str | None, Query(max_length=64)] = None,
) -> list[FlashcardView]:
    rows = s.list_flashcards(str(topic_id), include_archived, at)
    return [
        FlashcardView(
            card=card,
            review_state=state,
            estimated_retention=retention,
            due=due,
        )
        for card, state, retention, due in rows
    ]


@router.post("/topics/{topic_id}/flashcards", status_code=201)
async def create_flashcard(
    topic_id: UUID, body: FlashcardCreateInput, s: S
) -> FlashcardView:
    card, state = s.create_flashcard(
        str(topic_id),
        body.front,
        body.back,
        body.concept_name,
        str(body.operation_id),
        created_at=body.created_at,
    )
    return _card_view(card, state, body.created_at)


@router.post("/messages/{message_id}/flashcards", status_code=201)
async def import_flashcard(
    message_id: UUID, body: FlashcardImportInput, s: S
) -> FlashcardView:
    card, state = s.import_from_message(
        str(message_id),
        body.block_id,
        body.concept_name,
        str(body.operation_id),
    )
    return _card_view(card, state)


@router.patch("/flashcards/{flashcard_id}")
async def edit_flashcard(
    flashcard_id: UUID, body: FlashcardPatchInput, s: S
) -> FlashcardView:
    card, state = s.edit_flashcard(
        str(flashcard_id),
        body.front,
        body.back,
        body.concept_name,
        body.archived,
        body.expected_version,
        str(body.operation_id),
    )
    return _card_view(card, state)


@router.get("/flashcards/{flashcard_id}/history")
async def flashcard_history(flashcard_id: UUID, s: S) -> list[ReviewEvent]:
    return s.review_history(str(flashcard_id))


@router.get("/reviews/due")
async def due_reviews(
    s: S,
    topic_id: UUID | None = None,
    at: Annotated[str | None, Query(max_length=64)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[FlashcardView]:
    rows = s.due_reviews(
        str(topic_id) if topic_id else None,
        at_time=at,
        limit=limit,
    )
    return [
        FlashcardView(
            card=card,
            review_state=state,
            estimated_retention=retention,
            due=True,
        )
        for card, state, retention in rows
    ]


@router.post("/reviews/{flashcard_id}/grade")
async def grade_review(
    flashcard_id: UUID, body: ReviewGradeInput, s: S
) -> ReviewGradeView:
    card, state, event = s.grade_review(
        str(flashcard_id),
        body.rating,
        str(body.request_id),
        body.reviewed_at,
    )
    return ReviewGradeView(card=card, review_state=state, event=event)


@router.get("/progress/topics/{topic_id}")
async def topic_progress(
    topic_id: UUID,
    s: S,
    at: Annotated[str | None, Query(max_length=64)] = None,
) -> dict[str, object]:
    return s.topic_progress(str(topic_id), at_time=at)


@router.get("/progress/overview")
async def overview(
    s: S,
    at: Annotated[str | None, Query(max_length=64)] = None,
) -> dict[str, object]:
    return s.overview(at_time=at)


@router.patch("/progress/preferences")
async def update_preferences(body: PreferenceInput, s: S) -> ProgressPreference:
    return s.set_preference(body.hide_gamification)
