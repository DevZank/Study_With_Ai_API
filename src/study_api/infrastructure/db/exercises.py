from dataclasses import asdict

from sqlalchemy import Engine, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from study_api.domain.chat import LOCAL_PROFILE_ID, AppError
from study_api.domain.exercises import Attempt, Exercise
from study_api.infrastructure.db.models import AttemptRow, ExerciseRow


class ExerciseStore:
    engine: Engine

    def exercise(self, exercise_id: str) -> Exercise:
        with Session(self.engine) as session:
            row = session.get(ExerciseRow, exercise_id)
            if row is None or row.owner_id != LOCAL_PROFILE_ID:
                raise AppError("NOT_FOUND", "Exercício não encontrado.", 404)
            return Exercise(
                **{key: getattr(row, key) for key in Exercise.__dataclass_fields__}
            )

    def attempts(self, exercise_id: str) -> list[Attempt]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(AttemptRow)
                .where(
                    AttemptRow.exercise_id == exercise_id,
                    AttemptRow.owner_id == LOCAL_PROFILE_ID,
                )
                .order_by(AttemptRow.created_at, AttemptRow.id)
            )
            return [
                Attempt(
                    **{key: getattr(row, key) for key in Attempt.__dataclass_fields__}
                )
                for row in rows
            ]

    def save_attempt(self, attempt: Attempt) -> Attempt:
        try:
            with Session(self.engine) as session, session.begin():
                previous = session.scalar(
                    select(AttemptRow).where(
                        AttemptRow.request_id == attempt.request_id
                    )
                )
                if previous:
                    if (
                        previous.exercise_id != attempt.exercise_id
                        or previous.response != attempt.response
                        or previous.owner_id != attempt.owner_id
                    ):
                        raise AppError(
                            "IDEMPOTENCY_CONFLICT",
                            "Identificador já usado em outra tentativa.",
                            409,
                        )
                    return Attempt(
                        **{
                            key: getattr(previous, key)
                            for key in Attempt.__dataclass_fields__
                        }
                    )
                session.add(AttemptRow(**asdict(attempt)))
        except IntegrityError as error:
            raise AppError(
                "ATTEMPT_CONFLICT", "Tentativa duplicada. Atualize o exercício.", 409
            ) from error
        return attempt

    def reveal_hint(self, exercise_id: str) -> Exercise:
        self.exercise(exercise_id)
        with Session(self.engine) as session, session.begin():
            session.execute(
                update(ExerciseRow)
                .where(
                    ExerciseRow.id == exercise_id,
                    ExerciseRow.owner_id == LOCAL_PROFILE_ID,
                    ExerciseRow.hints_revealed < 3,
                )
                .values(hints_revealed=ExerciseRow.hints_revealed + 1)
            )
        return self.exercise(exercise_id)
