# ScaleCraft

ScaleCraft converts plain-English product requirements into a production-friendly planning bundle:

1. Structured system requirements spec
2. Distributed architecture graph
3. Realistic load-test scenarios
4. Generated `k6` and `Locust` scripts
5. Bottleneck and scaling-risk report

## Stack

- Backend: FastAPI + Pydantic
- Frontend: React + TypeScript + Vite
- Graph modeling: NetworkX
- Script export: k6 and Locust
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
- `LoadProfileGenerator`: traffic model, concurrency, spikes, request mix, ramp plan
- `ScriptGenerator`: shared generation flow with `k6` and `Locust` exporters
- `RiskAnalyzer`: bottlenecks, resilience gaps, and scaling recommendations

The parser supports a provider abstraction for LLM-backed parsing, but all downstream generators stay deterministic and testable.

## API Endpoints

- `POST /parse`
- `POST /architecture`
- `POST /load-profile`
- `POST /generate-script`
- `POST /analyze-risks`
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
- Architecture and risk generation are intentionally deterministic for repeatability.
- The frontend includes example prompts and placeholder mock outputs to keep the UI usable before the first request completes.
