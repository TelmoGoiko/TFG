param(
    [switch]$SkipServers
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$rootEnv = Join-Path $root ".env"
$rootEnvExample = Join-Path $root ".env.example"
$backendDir = Join-Path $root "backend"
$backendEnv = Join-Path $backendDir ".env"
$backendEnvExample = Join-Path $backendDir ".env.example"
$backendPython = Join-Path $backendDir ".venv/Scripts/python.exe"

if (-not (Test-Path $rootEnv) -and (Test-Path $rootEnvExample)) {
    Copy-Item $rootEnvExample $rootEnv
}

if (-not (Test-Path $backendEnv) -and (Test-Path $backendEnvExample)) {
    Copy-Item $backendEnvExample $backendEnv
}

if (-not (Test-Path $backendPython)) {
    throw "No se encontro backend/.venv. Ejecuta primero: cd backend; python -m poetry install"
}

Push-Location $root
docker compose up -d
Pop-Location

Push-Location $backendDir
& $backendPython -m alembic upgrade head
Pop-Location

if ($SkipServers) {
    Write-Host "Setup completado: DB arriba y migraciones aplicadas."
    exit 0
}

$backendCmd = "Push-Location '$backendDir'; ./.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload; Pop-Location"
$frontendDir = Join-Path $root "frontend"
$frontendCmd = "Push-Location '$frontendDir'; npm run dev; Pop-Location"

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd | Out-Null
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd | Out-Null

Write-Host "Servicios arrancados:"
Write-Host "- Backend: http://127.0.0.1:8010"
Write-Host "- Frontend: revisa la URL que imprima Vite"
