# Backend da Plataforma de Estudos com IA

No Windows, a partir desta pasta, use Python 3.14:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: -r requirements.lock
.\.venv\Scripts\python.exe -m uvicorn study_api.main:app --app-dir src --host 127.0.0.1 --port 8000
```

O healthcheck fica em `http://127.0.0.1:8000/api/v1/health`. Para rodar os testes, use `.\.venv\Scripts\python.exe -m pytest`.

Execute `.\scripts\diagnose.ps1` para diagnosticar o ambiente local. O frontend é executado separadamente e deve usar a API na porta 8000.

Consulte [as regras](AGENTS.md), [as tarefas](TASKS.md), [o planejamento](PLANEJAMENTO_PLATAFORMA_ESTUDOS_IA.md), [as decisões](docs/architecture/0001-foundation.md) e [o contrato HTTP](docs/api/contracts.md).
