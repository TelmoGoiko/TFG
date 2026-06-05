# TFG Telmo - FastAPI + React + PostgreSQL (pgvector)

Base monorepo for the TFG project with:

- Backend: FastAPI + SQLAlchemy + Alembic + Poetry
- Frontend: React (Vite)
- DB: PostgreSQL with the `pgvector` extension via Docker Compose

## Structure

- `backend/`: API and migrations
- `frontend/`: React app
- `docker-compose.yml`: PostgreSQL + pgvector
- `.vscode/launch.json`: FastAPI debug configuration

## 0) Mattin configuration

This project depends on Mattin AI. After starting Mattin (https://github.com/lksnext-ai-lab/ai-core-tools/), read `Configs_Mattin.md` and complete the required configuration.

## 1) Requirements

- Docker and Docker Compose to run the database or the full stack in containers.
- Python 3.11 and Poetry if you want to run the backend locally.
- Node.js and npm if you want to run the frontend locally.

Before starting with Docker or locally, copy `backend/.env.example` to `backend/.env`.

## 2) Recommended startup with Docker

This flow starts backend, frontend, and database inside containers. If you use this option, you do not need to run `poetry run uvicorn ...` on your machine.

```bash
docker compose up --build -d
docker compose exec backend python -m alembic upgrade head
```

- Backend: http://localhost:8010
- Frontend: http://localhost:5173

## 3) Database only with Docker

```bash
docker compose up -d db
```

Use this flow if you want to run the backend and frontend locally while reusing PostgreSQL in Docker.

## 4) Backend locally

`backend/poetry.toml` sets `virtualenvs.in-project = true`, so Poetry creates the environment in `backend/.venv`.

### macOS / Linux

```bash
cd backend
poetry install --no-root
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload --port 8010
```

### Windows PowerShell

```powershell
cd backend
poetry install --no-root
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload --port 8010
```

`poetry install --no-root` is used because the backend package declares its own `README.md` in `pyproject.toml`, and that file does not currently exist inside `backend`.

## 5) Frontend locally

```bash
cd frontend
npm install
npm run dev
```

## 6) One-command startup (Windows PowerShell)

This script starts the database with Docker, applies migrations, and opens backend and frontend in separate PowerShell windows.

Prerequisites:

- `backend/.env` must already exist.
- You must have run `cd backend; poetry install --no-root` at least once to create `backend/.venv`.
- You must have run `cd frontend; npm install` at least once.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev-up.ps1
```

To run only the setup step (DB + migrations, without starting servers):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev-up.ps1 -SkipServers
```

## Main endpoints

- `GET /health`
- API base: `/api/v1`

- Workspaces:
	- `GET /api/v1/workspaces?owner_id=<owner_id>`
	- `POST /api/v1/workspaces`
	- `GET /api/v1/workspaces/{workspace_id}`
	- `DELETE /api/v1/workspaces/{workspace_id}`

- Workspace files:
	- `GET /api/v1/workspaces/{workspace_id}/files`
	- `POST /api/v1/workspaces/{workspace_id}/files` (multipart upload)
	- `GET /api/v1/workspaces/{workspace_id}/files/{file_id}/download`
	- `DELETE /api/v1/workspaces/{workspace_id}/files/{file_id}`

- Generated runs & blocks (document generation):
	- `GET /api/v1/workspaces/{workspace_id}/generated`
	- `POST /api/v1/workspaces/{workspace_id}/generated` (create generation run)
	- `GET /api/v1/workspaces/{workspace_id}/generated/{run_id}`
	- `DELETE /api/v1/workspaces/{workspace_id}/generated/{run_id}`
	- `GET /api/v1/workspaces/{workspace_id}/generated/{run_id}/blocks`
	- `POST /api/v1/workspaces/{workspace_id}/generated/{run_id}/blocks`
	- `GET|PATCH|DELETE /api/v1/workspaces/{workspace_id}/generated/{run_id}/blocks/{block_id}`
	- Block relationships: `GET/POST/DELETE /api/v1/workspaces/{workspace_id}/generated/{run_id}/blocks/{block_id}/relationships`

## Block-based generation flow (agent-ready)

- `POST /api/v1/workspaces/{workspace_id}/generated`
- Creates a document run and generates Markdown blocks.
- If `MATTIN_DOCUMENT_WRITER_AGENT_ID` or `MATTIN_DOCUMENT_SPLITTER_AGENT_ID` is configured, it uses the Mattin agents and expects a JSON response with blocks.
- If the agent does not return a valid format, it falls back to a local base template.

## Block chat with agent

- `POST /api/v1/workspaces/{workspace_id}/generated/{run_id}/blocks/{block_id}/agent-chat`
- Stores the user message and assistant response for the block.

## Agents for relationships and impact

To enable relationship detection and impact suggestions with `call_agent`, define these values in `backend/.env`:

- `MATTIN_BLOCK_RELATIONSHIP_AGENT_ID=<agent_id>`
- `MATTIN_BLOCK_IMPACT_AGENT_ID=<agent_id>`

## Backend MCP server

- MCP client configuration:
{"tfg-docs-tools": {"transport": "streamable_http", "url": "http://host.docker.internal:8010/mcp/v1/id/1/1"}}
- `POST /mcp/v1/id/{app_id}/{server_id}`
- `POST /mcp/v1/{app_slug}/{server_slug}`
- Supported methods (JSON-RPC):
- `initialize`
- `tools/list`
- `tools/call`
- Available tools:
- `get_document_outline`
- `rewrite_block`
- `review_consistency`

## Notes

- By default, the backend expects PostgreSQL on `localhost:5432` with database `tfg_db`.
- On this machine, `.env` was configured with `POSTGRES_PORT=55432` because of a port conflict.
- The initial migration enables `vector` and creates the `item_embeddings` table.
- In Docker, the backend uses `db:5432` internally even if you publish a different port on the host.
- If you configure `MCP_SERVER_TOKEN`, the MCP endpoint requires `Authorization: Bearer <token>` or the `x-mcp-token` header.
