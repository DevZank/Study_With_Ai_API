from fastapi import FastAPI

from study_api.presentation.health import router

app = FastAPI(title="Plataforma de Estudos com IA", version="0.0.0")
app.include_router(router, prefix="/api/v1")
