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

## 0) Configuraciones en Mattin
El proyecto depende de Mattin AI, así que una vez arrancado (https://github.com/lksnext-ai-lab/ai-core-tools/), leer Configs_Mattin.md para configurar lo necesario.

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

## Docker dev (todo en un compose)

```bash
docker compose up --build
```

- Backend: http://localhost:8010
- Frontend: http://localhost:5173

Si no tienes `backend/.env`, copia `backend/.env.example`.

Para aplicar migraciones manualmente:

```bash
docker compose exec backend python -m alembic upgrade head
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

## Agentes para relaciones e impacto

Para habilitar deteccion de relaciones y sugerencias de impacto con `call_agent`, define en `backend/.env`:

- `MATTIN_BLOCK_RELATIONSHIP_AGENT_ID=<agent_id>`
- `MATTIN_BLOCK_IMPACT_AGENT_ID=<agent_id>`

## Servidor MCP del backend

- Configuracion del cliente mcp: 
{"tfg-docs-tools": {"transport": "streamable_http", "url": "http://host.docker.internal:8010/mcp/v1/id/1/1"}}
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
