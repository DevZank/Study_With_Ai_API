import asyncio
import json
import logging
from hashlib import sha256

from study_api.domain.chat import (
    AppError,
    Conversation,
    Job,
    Message,
    Provider,
    Repository,
    Topic,
)


class ChatService:
    def __init__(self, repository: Repository, provider: Provider) -> None:
        self.repo = repository
        self.provider = provider
        self.tasks: dict[str, asyncio.Task[None]] = {}

    def list_topics(self, status: str, query: str) -> list[Topic]:
        rows = [
            t
            for t in self.repo.topics()
            if t.status == status and query.casefold() in t.title.casefold()
        ]
        return sorted(rows, key=lambda t: (t.updated_at, t.id), reverse=True)

    def create_topic(self, title: str) -> Topic:
        return self.repo.save_topic(Topic(title))

    def get_topic(self, topic_id: str) -> Topic:
        return self.repo.topic(topic_id)

    def list_conversations(self, topic_id: str) -> list[Conversation]:
        self.topic(topic_id)
        return self.repo.conversations(topic_id)

    def create_conversation(self, topic_id: str, title: str) -> Conversation:
        if self.topic(topic_id).status != "active":
            raise AppError(
                "TOPIC_ARCHIVED", "Restaure o tema antes de criar uma conversa.", 409
            )
        return self.repo.save_conversation(Conversation(topic_id, title))

    def history(self, conversation_id: str) -> list[Message]:
        self.conversation(conversation_id)
        return self.repo.messages(conversation_id)

    def jobs_for(self, conversation_id: str) -> list[Job]:
        self.conversation(conversation_id)
        return [j for j in self.repo.jobs() if j.conversation_id == conversation_id][
            -20:
        ]

    def get_job(self, job_id: str) -> Job:
        return self.repo.job(job_id)

    def get_message(self, message_id: str) -> Message:
        return self.repo.message(message_id)

    async def models(self) -> list[str]:
        return await self.provider.models()

    def topic(self, topic_id: str) -> Topic:
        topic = self.repo.topic(topic_id)
        if topic.status == "deleted":
            raise AppError(
                "TOPIC_DELETED", "Tema na lixeira. Restaure-o antes de continuar.", 409
            )
        return topic

    def conversation(self, conversation_id: str) -> Conversation:
        conversation = self.repo.conversation(conversation_id)
        self.topic(conversation.topic_id)
        return conversation

    def change_topic(
        self, topic_id: str, title: str | None, status: str | None
    ) -> Topic:
        topic = self.repo.topic(topic_id)
        conversations = {c.id for c in self.repo.conversations(topic.id)}
        if any(
            j.status == "running" and j.conversation_id in conversations
            for j in self.repo.jobs()
        ):
            raise AppError(
                "TOPIC_BUSY", "Cancele a geração antes de alterar este tema.", 409
            )
        if title is not None:
            topic.title = title
        if status is not None:
            topic.status = status
        return self.repo.save_topic(topic)

    async def start(
        self, conversation_id: str, content: str, model: str, request_id: str
    ) -> Job:
        conversation = self.conversation(conversation_id)
        if self.topic(conversation.topic_id).status != "active":
            raise AppError(
                "TOPIC_ARCHIVED", "Restaure o tema arquivado antes de enviar.", 409
            )
        fingerprint = sha256(
            (conversation_id + "\0" + content + "\0" + model).encode()
        ).hexdigest()
        for job in self.repo.jobs():
            if job.request_id == request_id:
                if job.request_hash != fingerprint:
                    raise AppError(
                        "IDEMPOTENCY_CONFLICT",
                        "Identificador já usado com outra mensagem.",
                        409,
                    )
                return job
        if any(
            j.status == "running" and j.conversation_id == conversation_id
            for j in self.repo.jobs()
        ):
            raise AppError(
                "GENERATION_ACTIVE", "Aguarde ou cancele a resposta em andamento.", 409
            )
        await self.provider.validate_model(model)
        # A validação local cede a execução: confira novamente antes da transação.
        if self.topic(conversation.topic_id).status != "active":
            raise AppError("TOPIC_ARCHIVED", "Restaure o tema antes de enviar.", 409)
        for existing in self.repo.jobs():
            if existing.request_id == request_id:
                if existing.request_hash != fingerprint:
                    raise AppError(
                        "IDEMPOTENCY_CONFLICT",
                        "Identificador já usado com outra mensagem.",
                        409,
                    )
                return existing
        history = self.repo.messages(conversation_id)
        history = [m for m in history if m.status == "completed"]
        if (
            len(history) >= 30
            or sum(len(m.content) for m in history) + len(content) > 12_000
        ):
            raise AppError(
                "CONTEXT_LIMIT",
                "Esta conversa atingiu o limite inicial de contexto. Crie outra conversa no tema.",
                409,
            )
        user = Message(conversation_id, "user", content)
        assistant = Message(
            conversation_id, "assistant", "", status="running", model_id=model
        )
        job = Job(conversation_id, assistant.id, model, request_id, fingerprint)
        self.repo.create_turn(user, assistant, job)
        prompts = [
            {
                "role": "system",
                "content": "Responda em português brasileiro. Sinalize incerteza e não invente fontes.",
            }
        ]
        prompts += [{"role": m.role, "content": m.content} for m in history + [user]]
        self.tasks[job.id] = asyncio.create_task(
            self._generate(job, assistant, prompts)
        )
        self.tasks[job.id].add_done_callback(self._task_done)
        return job

    @staticmethod
    def _task_done(task: asyncio.Task[None]) -> None:
        if not task.cancelled() and task.exception() is not None:
            logging.getLogger("study_api").error(
                json.dumps(
                    {
                        "event": "generation_task_error",
                        "error_type": type(task.exception()).__name__,
                    }
                )
            )

    async def _generate(
        self, job: Job, message: Message, prompts: list[dict[str, str]]
    ) -> None:
        try:
            async with asyncio.timeout(180):
                async for delta in self.provider.chat(job.model_id, prompts):
                    if len(message.content) + len(delta) > 50_000:
                        raise AppError(
                            "OUTPUT_LIMIT", "A resposta atingiu o limite permitido."
                        )
                    message.content += delta
                    self.repo.save_message(message)
            if not message.content.strip():
                raise AppError(
                    "EMPTY_RESPONSE", "O modelo retornou uma resposta vazia."
                )
            job.status = message.status = "completed"
        except asyncio.CancelledError:
            job.status = message.status = "cancelled"
        except TimeoutError:
            job.status = message.status = "failed"
            job.error_code, job.error_message = (
                "MODEL_TIMEOUT",
                "Tempo máximo de geração excedido.",
            )
        except AppError as error:
            job.status = message.status = "failed"
            job.error_code, job.error_message = error.code, error.message
        finally:
            # Uma falha inesperada também deixa um estado recuperável, sem divulgar a exceção.
            if job.status == "running":
                job.status = message.status = "interrupted"
                job.error_code, job.error_message = (
                    "GENERATION_INTERRUPTED",
                    "Geração interrompida inesperadamente.",
                )
            self.repo.save_job(job, message)
            self.tasks.pop(job.id, None)

    async def cancel(self, job_id: str) -> Job:
        job = self.repo.job(job_id)
        task = self.tasks.get(job_id)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                # O cancelamento pode chegar antes de a tarefa executar seu primeiro passo.
                current = self.repo.job(job_id)
                if current.status == "running":
                    message = self.repo.message(current.message_id)
                    current.status = message.status = "cancelled"
                    self.repo.save_job(current, message)
                self.tasks.pop(job_id, None)
        elif job.status == "running":
            message = self.repo.message(job.message_id)
            job.status = message.status = "interrupted"
            job.error_code, job.error_message = (
                "SERVER_RESTARTED",
                "Geração interrompida pelo reinício.",
            )
            self.repo.save_job(job, message)
        return self.repo.job(job_id)

    def recover(self) -> None:
        for job in self.repo.jobs():
            if job.status == "running":
                message = self.repo.message(job.message_id)
                job.status = message.status = "interrupted"
                job.error_code, job.error_message = (
                    "SERVER_RESTARTED",
                    "Geração interrompida pelo reinício. O texto parcial foi preservado.",
                )
                self.repo.save_job(job, message)

    async def close(self) -> None:
        for job_id in list(self.tasks):
            await self.cancel(job_id)
