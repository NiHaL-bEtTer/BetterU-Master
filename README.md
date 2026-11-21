<div align="center">

# BetterU

### Your nutrition, fitness, and wellness companion

Track food against your targets, train with a plan built for you, and ask
**Alden**, a coach whose answers come from USDA data and trusted health sources.

<p>
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-Vite-61DAFB?style=for-the-badge&logo=react&logoColor=111827" alt="React + Vite">
  <img src="https://img.shields.io/badge/Postgres-pgvector-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="Postgres + pgvector">
</p>

</div>

---

## ✨ Features

| Screen | What it does |
| --- | --- |
| **Onboarding** | Goal, body stats (metric or imperial), activity, diet, allergies, equipment → instant daily targets with a "how we worked this out" breakdown |
| **Today** | Calorie ring, macro bars, meals, today's training, and a nudge from Alden |
| **Log** | Search ~13,600 USDA foods (typo-tolerant), recent foods, favourites, barcode lookup (Open Food Facts), real portion sizes |
| **Alden** | Streaming chat with tool calling: exact nutrition lookups, meal totals, one-tap "Log meal" buttons, cited sources, recipe videos, 👍/👎 feedback |
| **Train** | AI-built plan from 870+ exercises filtered to your equipment, set logging, "beat last time", rest timer |
| **Progress** | Weight trend (7-day average) and an adaptive maintenance estimate from your own data |
| **Me** | Edit profile, download all your data, delete your account |

Safety built in: calorie floors and capped deficits, no deficits for under-18s,
allergy-aware suggestions, and Alden never logs anything without the user's tap.

## 🧭 How it works

```text
Browser (React PWA, /app)  ──►  FastAPI (/api)  ──►  Postgres 16
                                   │                  ├─ users, profiles, food log, workouts, chats
                                   │                  ├─ foods (USDA, per 100 g) + full-text + vectors
                                   │                  ├─ knowledge chunks (pgvector + full-text)
                                   │                  └─ exercises (free-exercise-db)
                                   │
                                   ├─► LLM (any OpenAI-compatible API; Groq by default)
                                   ├─► Tavily (trusted-domain web search, optional)
                                   ├─► YouTube Data API (recipe videos, optional)
                                   └─► Open Food Facts (barcodes, no key)
```

**Accuracy by design**

- **Numbers come from the database, not the model.** Alden calls `search_foods` and
  `calculate_meal`; totals are computed in Python. Calorie targets come from
  `services/calculator.py`.
- **RAG for guidance.** MedlinePlus nutrition articles, WHO fact sheets and Health Canada
  guidelines are chunked by heading and searched with **hybrid search** (pgvector + Postgres
  full-text, fused with reciprocal-rank fusion). Answers cite `[S1]`, `[F12]` and so on.
- **Web results are never stored.** Tavily search is limited to trusted health domains and
  used for one answer only.

## 🍎 Run it on your Mac (no Docker)

**One-time setup**

1. Install [Postgres.app](https://postgresapp.com) (it includes pgvector), open it and click **Initialize**.
2. Create the database:
   ```bash
   /Applications/Postgres.app/Contents/Versions/latest/bin/createdb betteru
   ```
3. In `.env`, set `DATABASE_URL=postgresql+psycopg://localhost:5432/betteru`
4. Create the tables and load the data (3–5 minutes):
   ```bash
   cd apps/api && .venv/bin/alembic upgrade head && .venv/bin/python -m betteru.ingest
   ```

**Every time:** with Postgres.app running, start the server and open http://localhost:8000

```bash
cd apps/api && .venv/bin/uvicorn betteru.main:app --port 8000
```

After changing frontend code, rebuild it with `cd apps/web && npm run build`, or run `npm run dev` there for live reloading.

## ⚡ Quick start

You need **Docker**, **Python 3.11+** and **Node 22+**.

```bash
cp .env.example .env        # then add at least LLM_API_KEY and a JWT_SECRET
```

### Option A: everything in Docker

```bash
docker compose up --build
```

```bash
docker compose exec app python -m betteru.ingest
```

Open **http://localhost:8000**. Ingestion takes about 3–5 minutes the first time.

### Option B: local development (hot reload)

```bash
docker compose up -d db
```

```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
python -m betteru.ingest          # foods, exercises, knowledge base
uvicorn betteru.main:app --reload --port 8000
```

In a second terminal:

```bash
cd apps/web && npm install && npm run dev
```

Open **http://localhost:5173**. Vite proxies `/api` to the API on port 8000.

## 🔑 APIs and keys

| Service | Needed for | Key | Cost |
| --- | --- | --- | --- |
| **PostgreSQL + pgvector** | Everything | `DATABASE_URL` | Free locally (Docker); Supabase or Neon free tiers in the cloud |
| **LLM provider** (Groq by default) | Alden chat and workout plans | `LLM_API_KEY` | Groq free tier works but rate-limits multi-step answers; the paid tier removes the waits |
| **USDA FoodData Central API** | Branded/packaged foods searched by name (e.g. "clif bar"), and a barcode fallback | `USDA_API_KEY` | Optional, free, 1,000 requests/hour |
| **Tavily** | Web fallback when the knowledge base has no answer | `TAVILY_API_KEY` | Optional, free tier 1,000 searches/month |
| **YouTube Data API v3** | Recipe videos in chat | `YOUTUBE_API_KEY` | Optional, free quota |
| **Sentry** | Error tracking | `SENTRY_DSN` | Optional, free tier |
| USDA FoodData Central (bulk files) | Food database: whole foods and common dishes | none | Free, public domain |
| free-exercise-db | Exercises and images | none | Free, public domain |
| MedlinePlus, WHO, Health Canada | Knowledge base | none | Free public health information |
| Open Food Facts | Barcode lookup | none | Free, open data |

To switch LLM provider, change `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL`. Any
OpenAI-compatible endpoint with tool calling works.

## 🧠 Knowledge base and data

```bash
python -m betteru.ingest              # everything
python -m betteru.ingest foods        # USDA Foundation, SR Legacy, Survey (FNDDS)
python -m betteru.ingest exercises
python -m betteru.ingest docs         # web sources + any PDFs in apps/api/data/pdfs/
python -m betteru.ingest docs --force # re-embed even if unchanged
```

- Reloads **upsert**, so food and exercise IDs stay stable and favourites and logs keep working.
- Branded products aren't preloaded (~450k). When a search has no result containing every word
  you typed, the API asks USDA's branded database once, saves the matches, and serves them
  locally from then on (`services/branded.py`).
- Documents are re-embedded only when their text changes.
- Add more sources in `betteru/ingest/documents.py`, or drop PDFs (for example the
  Dietary Guidelines for Americans or ISSN position stands) into `apps/api/data/pdfs/`.
  Check each PDF's licence first.

## 🗂️ Project structure

```text
apps/
├── api/                      FastAPI backend
│   ├── betteru/
│   │   ├── main.py           app factory: /api plus the web app for every other path
│   │   ├── config.py         settings from environment
│   │   ├── models.py         SQLAlchemy tables
│   │   ├── schemas.py        request/response models (→ OpenAPI → TypeScript)
│   │   ├── routers/          HTTP only: auth, profile, foods + log, progress, workouts, chat
│   │   ├── services/         business logic: calculator, foods, retrieval, progress, workouts
│   │   ├── llm/              Alden: prompts, tools, streaming agent loop
│   │   ├── clients/          LLM, YouTube, Tavily, Open Food Facts
│   │   └── ingest/           data loaders + heading-aware chunker
│   ├── migrations/           Alembic
│   └── tests/                pytest (real Postgres, fake LLM and embeddings)
└── web/                      React + Vite + TypeScript PWA: website (/, /about, /team) and app (/app)
    └── src/
        ├── site/             website pages
        ├── pages/            app screens
        ├── components/       shared UI, incl. the Nutrition Facts panel
        │   └── rb/           React Bits components (reactbits.dev)
        └── api/              generated API types + client
```

## 🛠️ Development

```bash
cd apps/api && pytest -q && ruff check betteru migrations tests
```

```bash
cd apps/web && npm run lint && npm run build
```

```bash
cd apps/web && npm run gen:api     # after changing API schemas: regenerate TypeScript types
```

```bash
cd apps/api && alembic revision --autogenerate -m "describe change"   # after changing models
```

- Tests use `TEST_DATABASE_URL`. Locally they start an embedded Postgres via `pgserver` if it isn't set.
- CI (`.github/workflows/ci.yml`) runs lint, tests against `pgvector/pgvector:pg16`, and a web build.
- API docs: http://localhost:8000/api/docs (disabled when `ENVIRONMENT=production`).

## 🚀 Deploying

1. Create a Postgres database with the `vector` extension (Supabase, Neon, RDS, or the Docker image).
2. Build the `Dockerfile`. It builds the web app and serves everything from one container on port 8000.
3. Set `ENVIRONMENT=production`, a strong `JWT_SECRET`, `COOKIE_SECURE=true`, `DATABASE_URL` and `LLM_API_KEY`.
4. The container runs `alembic upgrade head` on start. Run `python -m betteru.ingest` once.

Render, Railway and Fly.io all run this image as-is.

---

<div align="center">BetterU gives general guidance, not medical advice.</div>
