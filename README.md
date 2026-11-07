# Backend da Plataforma de Estudos com IA

No Windows, a partir desta pasta, use Python 3.14:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: -r requirements.lock
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn study_api.main:app --app-dir src --host 127.0.0.1 --port 8000 --no-access-log
```

O healthcheck fica em `http://127.0.0.1:8000/api/v1/health`. Para rodar os testes, use `.\.venv\Scripts\python.exe -m pytest`.

Para atualizar uma instalação do Marco 1: encerre a API, copie a pasta de dados inteira para um local seguro fora do repositório e só então aplique `python -m alembic upgrade head` pelo ambiente virtual. A revisão 0002 é aditiva e preserva o histórico. Não substitua ou apague o banco. A aplicação usa uma única instância por banco; o downgrade destrutivo permanece bloqueado.

O Marco 2 acrescenta modos persistidos, documentos de blocos validados e exercícios com tentativas e dicas. Questões abertas não recebem nota automática; o gabarito das objetivas é gerado por IA e pode estar incorreto.

Para validar o Marco 2 com o modelo local selecionado, defina `STUDY_TEST_OLLAMA_MODEL` e execute `python -m pytest tests/test_real_content.py -q -s` pelo ambiente virtual. São usadas somente perguntas sintéticas e um banco temporário. Para exportar o contrato público, execute `python scripts/export_content_schema.py`; concilie a cópia do frontend explicitamente.

Execute `.\scripts\diagnose.ps1` para diagnosticar o ambiente local. O frontend é executado separadamente e deve usar a API na porta 8000.

Execute somente uma instância/worker da API por banco. Os dados ficam em `data/study.sqlite3`, ignorado pelo Git. Para outro caminho, defina `STUDY_DB_PATH` antes de migrar e iniciar. Não remova o banco para atualizar. Antes de futuras migrações em dados de uso real, pare a API e faça backup dos arquivos SQLite e seus arquivos auxiliares; valide a restauração antes de prosseguir.

Em outro terminal, inicie o Ollama local, quando necessário, com `ollama serve`. Se o aplicativo Ollama já estiver aberto, não inicie outro serviço. Não é necessário Ollama para gerenciar temas e consultar o histórico. Nenhum modelo é baixado automaticamente.

## Qualidade e validação

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy src tests
.\.venv\Scripts\python.exe -m pytest
```

O teste real é opcional: defina `STUDY_TEST_OLLAMA_MODEL` com um modelo instalado e execute `python -m pytest tests/test_real_ollama.py -q` pelo ambiente virtual. Ele envia apenas perguntas sintéticas ao Ollama local e usa um banco temporário. A execução normal da suíte não chama modelos reais.

Para o E2E determinístico do frontend, inicie exclusivamente em ambiente de teste:

```powershell
$env:PYTHONPATH = "src"
$env:STUDY_DB_PATH = Join-Path $env:TEMP ("study-e2e-" + [guid]::NewGuid() + ".sqlite3")
.\.venv\Scripts\python.exe tests/e2e_server.py
```

Esse servidor usa um provedor determinístico de teste e a porta 8000. Não execute simultaneamente com a API de produção na mesma porta. Encerrar os testes não remove automaticamente o banco temporário.

Consulte [as regras](AGENTS.md), [as tarefas](TASKS.md), [o planejamento](PLANEJAMENTO_PLATAFORMA_ESTUDOS_IA.md), [as decisões](docs/architecture/0001-foundation.md) e [o contrato HTTP](docs/api/contracts.md).
