import json

from study_api.domain.chat import AppError, Repository
from study_api.domain.exercises import Attempt, Exercise, grade


class ExerciseService:
    def __init__(self, repo: Repository) -> None:
        self.repo = repo

    def get(self, exercise_id: str) -> Exercise:
        exercise = self.repo.exercise(exercise_id)
        message = self.repo.message(exercise.message_id)
        conversation = self.repo.conversation(message.conversation_id)
        if self.repo.topic(conversation.topic_id).status == "deleted":
            raise AppError(
                "TOPIC_DELETED", "Restaure o tema para consultar o exercício.", 409
            )
        return exercise

    def attempts(self, exercise_id: str) -> list[Attempt]:
        self.get(exercise_id)
        return self.repo.attempts(exercise_id)

    def attempt(self, exercise_id: str, answer: str, request_id: str) -> Attempt:
        exercise = self.get(exercise_id)
        conversation = self.repo.conversation(
            self.repo.message(exercise.message_id).conversation_id
        )
        if self.repo.topic(conversation.topic_id).status != "active":
            raise AppError("TOPIC_ARCHIVED", "Restaure o tema antes de responder.", 409)
        options = json.loads(exercise.options_json)
        if exercise.kind == "multiple_choice" and answer not in [
            o["id"] for o in options
        ]:
            raise AppError("INVALID_ANSWER", "Escolha uma alternativa válida.", 422)
        if exercise.kind == "true_false" and answer not in ("true", "false"):
            raise AppError("INVALID_ANSWER", "Escolha verdadeiro ou falso.", 422)
        return self.repo.save_attempt(grade(exercise, answer, request_id))

    def hint(self, exercise_id: str) -> Exercise:
        self.get(exercise_id)
        return self.repo.reveal_hint(exercise_id)
