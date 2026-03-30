# TFG Telmo - FastAPI + React + PostgreSQL (pgvector)

Monorepo base para TFG con:

- Backend: FastAPI + SQLAlchemy + Alembic + Poetry
- Frontend: React (Vite)
- DB: PostgreSQL con extension `pgvector` via Docker Compose

## Estructura

- `backend/`: API y migraciones
- `frontend/`: app React
- `docker-compose.yml`: PostgreSQL + pgvector
- `.vscode/launch.json`: debug de FastAPI

## 1) Levantar base de datos

```bash
docker compose up -d
```

## Arranque en un solo comando (Windows PowerShell)

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev-up.ps1
```

Para ejecutar solo setup (DB + migraciones, sin lanzar servers):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev-up.ps1 -SkipServers
```

## 2) Backend

```bash
cd backend
poetry install
cp .env.example .env
.venv/Scripts/python.exe -m alembic upgrade head
poetry run uvicorn app.main:app --reload --port 8010
```

## 3) Frontend

```bash
cd frontend
npm install
npm run dev
```

## Endpoints iniciales

- `GET /health`
- `GET /api/v1/items`
- `POST /api/v1/items`

## Notas

- Por defecto el backend espera PostgreSQL en `localhost:5432` con DB `tfg_db`.
- En esta maquina se configuro `.env` a `POSTGRES_PORT=55432` por conflicto de puertos.
- La migracion inicial habilita `vector` y crea tabla `item_embeddings`.
