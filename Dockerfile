# ── 1. Build the web app ──────────────────────────────────────────────────
FROM node:22-slim AS web
WORKDIR /src/apps/web
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
COPY apps/web/ ./
RUN npm run build

# ── 2. API + built frontend ───────────────────────────────────────────────
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv
COPY apps/api/requirements.txt apps/api/requirements.txt
RUN pip install -r apps/api/requirements.txt
COPY apps/api/ apps/api/
COPY --from=web /src/apps/web/dist apps/web/dist
WORKDIR /srv/apps/api
RUN useradd --create-home app && chown -R app /srv
USER app
EXPOSE 8000
# Apply migrations, then serve. Load data once with: docker compose exec app python -m betteru.ingest
CMD ["sh", "-c", "alembic upgrade head && uvicorn betteru.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
