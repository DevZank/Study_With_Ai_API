param([string]$Python = "")

$ErrorActionPreference = "Stop"
if (-not $Python) {
    $Python = Join-Path $PSScriptRoot "../.venv/Scripts/python.exe"
}

& $Python --version
if ($LASTEXITCODE) { throw "Falha ao executar o Python selecionado." }
& $Python -m pip check
if ($LASTEXITCODE) { throw "Dependências Python incompatíveis." }

if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    & nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
}
if (Get-Command ollama -ErrorAction SilentlyContinue) { & ollama --version }
try {
    $result = Invoke-RestMethod "http://127.0.0.1:11434/api/version" -TimeoutSec 3
    Write-Output "Serviço Ollama local respondeu: $($result.version)"
} catch {
    Write-Output "Serviço Ollama indisponível no endereço local padrão."
}
