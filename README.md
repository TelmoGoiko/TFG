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

## Flujo de generacion por bloques (agent-ready)

- `POST /api/v1/workspaces/{workspace_id}/generated`
- Crea un run de documento y genera bloques markdown.
- Si `MATTIN_GENERATION_AGENT_ID` esta configurado, usa el agente de Mattin y espera un JSON de bloques.
- Si el agente no responde en formato valido, aplica fallback local con plantilla base.

## Chat por bloque con agente

- `POST /api/v1/workspaces/{workspace_id}/generated/{run_id}/blocks/{block_id}/agent-chat`
- Registra mensaje de usuario y respuesta de assistant para el bloque.
- Si el agente devuelve `updated_markdown`, puede auto-aplicarse al bloque (`auto_apply=true`).

## Servidor MCP del backend

- `POST /mcp/v1/id/{app_id}/{server_id}`
- `POST /mcp/v1/{app_slug}/{server_slug}`
- Methods soportados (JSON-RPC):
- `initialize`
- `tools/list`
- `tools/call`
- Tools disponibles:
- `get_document_outline`
- `rewrite_block`
- `review_consistency`

## Notas

- Por defecto el backend espera PostgreSQL en `localhost:5432` con DB `tfg_db`.
- En esta maquina se configuro `.env` a `POSTGRES_PORT=55432` por conflicto de puertos.
- La migracion inicial habilita `vector` y crea tabla `item_embeddings`.
- Si configuras `MCP_SERVER_TOKEN`, el endpoint MCP requiere `Authorization: Bearer <token>` o header `x-mcp-token`.
