# ScaleCraft

ScaleCraft converts a plain-English product requirement into an architecture planning bundle:

1. Structured system requirements spec
2. Distributed architecture graph

The current MVP focuses on the core path only: `requirement -> architecture`.

## Stack

- Backend: FastAPI + Pydantic
- Frontend: React + TypeScript + Vite
- Graph modeling: NetworkX
- LLM abstraction: provider-agnostic interface with OpenAI support first

## Repository Layout

```text
backend/   FastAPI app, schemas, services, tests
frontend/  React SPA with typed API client
docs/      Screenshot placeholders and supporting docs assets
```

## Backend Design

The backend is split into small service classes with typed request and response schemas:

- `RequirementParser`: natural language to structured requirement spec
- `ArchitectureGenerator`: services, databases, cache, queue, scaling notes, graph edges

The parser supports a provider abstraction for LLM-backed parsing, while the architecture generator stays deterministic and testable.

## API Endpoints

- `POST /parse`
- `POST /architecture`
- `GET /health`

## Local Setup

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

To enable OpenAI parsing, install the extra and provide `OPENAI_API_KEY`:

```bash
pip install -e .[dev,openai]
```

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Frontend default URL: `http://localhost:5173`

## Tests

```bash
cd backend
pytest
```

## Example Prompts

- Multi-region ecommerce marketplace with checkout and notifications
- B2B analytics SaaS with dashboard traffic and asynchronous exports
- Creator platform with uploads, feed reads, search, and launch-day spikes

## Screenshots

Add screenshots to `docs/screenshots/`.

- `docs/screenshots/home.png`
- `docs/screenshots/generated-results.png`

Placeholder section:

```text
[ Home screen screenshot goes here ]
[ Generated artifacts screenshot goes here ]
```

## Notes

- Core services avoid demo-only branches and rely on typed intermediate models.
- Architecture generation is intentionally deterministic for repeatability.
- The frontend is intentionally small: one input, one parsed summary, and one architecture result.
