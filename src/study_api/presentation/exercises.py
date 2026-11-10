import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from study_api.application.exercises import ExerciseService
from study_api.application.progress import ProgressService
from study_api.presentation.routes import Service
from study_api.presentation.schemas import AttemptInput, AttemptView, ExerciseView

router = APIRouter()


def service(s: Service) -> ExerciseService:
    return ExerciseService(s.repo)


Exercises = Annotated[ExerciseService, Depends(service)]


def view(exercise_id: str, s: ExerciseService) -> ExerciseView:
    exercise = s.get(exercise_id)
    attempts = s.attempts(exercise_id)
    hints = json.loads(exercise.hints_json)
    return ExerciseView(
        id=exercise.id,
        message_id=exercise.message_id,
        kind=exercise.kind,
        prompt=exercise.prompt,
        options=json.loads(exercise.options_json),
        hints=hints[: exercise.hints_revealed],
        hints_remaining=max(0, len(hints) - exercise.hints_revealed),
        solution=exercise.answer_key if attempts else None,
        explanation=exercise.explanation if attempts else None,
    )


@router.get("/exercises/{exercise_id}")
async def exercise(exercise_id: UUID, s: Exercises) -> ExerciseView:
    return view(str(exercise_id), s)


@router.post("/exercises/{exercise_id}/hints")
async def hint(exercise_id: UUID, s: Exercises) -> ExerciseView:
    s.hint(str(exercise_id))
    return view(str(exercise_id), s)


@router.get("/exercises/{exercise_id}/attempts")
async def attempts(exercise_id: UUID, s: Exercises) -> list[AttemptView]:
    return [AttemptView.model_validate(a) for a in s.attempts(str(exercise_id))]


@router.post("/exercises/{exercise_id}/attempts", status_code=201)
async def attempt(
    exercise_id: UUID, body: AttemptInput, s: Exercises, request: Request
) -> AttemptView:
    saved = s.attempt(str(exercise_id), body.response, str(body.request_id))
    exercise = s.get(str(exercise_id))
    conversation = s.repo.conversation(
        s.repo.message(exercise.message_id).conversation_id
    )
    progress: ProgressService | None = getattr(request.app.state, "progress", None)
    if progress is not None:
        progress.sync_topic(conversation.topic_id)
    return AttemptView.model_validate(saved)
