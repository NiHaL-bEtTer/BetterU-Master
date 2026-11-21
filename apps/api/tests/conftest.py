"""Test setup: a real Postgres (pgvector) database, fake embeddings, fake LLM.

Set TEST_DATABASE_URL to an empty database. Locally, if it isn't set and the
`pgserver` package is installed, an embedded Postgres is started automatically.
"""

import hashlib
import math
import os
import tempfile
import urllib.parse

import pytest


def _database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        return url
    try:
        import pgserver
    except ImportError:  # pragma: no cover
        pytest.exit("Set TEST_DATABASE_URL (Postgres with pgvector) or `pip install pgserver`.", 2)
    srv = pgserver.get_server(os.path.join(tempfile.gettempdir(), "betteru-test-pg"), cleanup_mode=None)
    if "1 row" not in srv.psql("SELECT 1 FROM pg_database WHERE datname='betteru_test'"):
        srv.psql("CREATE DATABASE betteru_test")
    host = urllib.parse.parse_qs(urllib.parse.urlparse(srv.get_uri()).query)["host"][0]
    return f"postgresql+psycopg://postgres@/betteru_test?host={host}"


os.environ["DATABASE_URL"] = _database_url()
os.environ["JWT_SECRET"] = "test-secret-that-is-long-enough-for-hs256"
os.environ["LLM_API_KEY"] = "test"
os.environ["TAVILY_API_KEY"] = ""
os.environ["YOUTUBE_API_KEY"] = ""


def fake_vector(text: str, dim: int = 384) -> list[float]:
    """Deterministic bag-of-words vector, so similar texts get similar vectors."""
    v = [0.0] * dim
    for word in text.lower().replace(",", " ").split():
        h = int(hashlib.md5(word.encode()).hexdigest(), 16)
        v[h % dim] += 1.0
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / norm for x in v]


@pytest.fixture(scope="session", autouse=True)
def database():
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import text

    from betteru.db import get_engine

    with get_engine().begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "migrations"))
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def clean_tables(monkeypatch):
    from sqlalchemy import text

    from betteru.db import get_engine
    from betteru.services import embeddings

    monkeypatch.setattr(embeddings, "embed_query", fake_vector)
    monkeypatch.setattr(embeddings, "embed_documents", lambda texts, batch_size=64: [fake_vector(t) for t in texts])
    # Modules that imported the functions directly need patching too.
    import betteru.services.branded as branded
    import betteru.services.foods as foods
    import betteru.services.retrieval as retrieval

    monkeypatch.setattr(branded, "embed_documents", lambda texts, batch_size=64: [fake_vector(t) for t in texts])
    branded._RECENT.clear()

    monkeypatch.setattr(foods, "embed_query", fake_vector)
    monkeypatch.setattr(retrieval, "embed_query", fake_vector)
    yield
    with get_engine().begin() as conn:
        conn.execute(text(
            "TRUNCATE users, foods, food_portions, documents, chunks, exercises RESTART IDENTITY CASCADE"
        ))


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from betteru.main import app

    return TestClient(app)


@pytest.fixture
def db():
    from betteru.db import SessionLocal

    s = SessionLocal()
    yield s
    s.close()


PROFILE = {
    "age": 30, "sex": "female", "height_cm": 165, "weight_kg": 62, "activity": "moderate",
    "goal": "maintain", "units": "metric", "diet": "vegetarian", "allergies": ["Peanut"],
    "equipment": ["dumbbell"], "training_days": 3, "notes": "",
}


@pytest.fixture
def user_client(client):
    r = client.post("/api/auth/register", json={"email": "sam@example.com", "password": "password123", "name": "Sam"})
    assert r.status_code == 201, r.text
    assert client.put("/api/profile", json=PROFILE).status_code == 200
    return client


@pytest.fixture
def foods(db):
    from betteru.models import Food, FoodPortion

    items = [
        Food(source="usda_sr_legacy", source_id="1", name="Egg, whole, raw, fresh", category="Dairy and Egg Products",
             kcal=143, protein_g=12.6, fat_g=9.5, carbs_g=0.7, embedding=fake_vector("Egg, whole, raw, fresh"),
             portions=[FoodPortion(description="1 large", grams=50)]),
        Food(source="usda_sr_legacy", source_id="2", name="Bread, whole-wheat", category="Baked Products",
             kcal=252, protein_g=12.4, fat_g=3.5, carbs_g=43.1, embedding=fake_vector("Bread, whole-wheat")),
        Food(source="usda_sr_legacy", source_id="3", name="Peanut butter, smooth", category="Legumes",
             kcal=588, protein_g=25, fat_g=50, carbs_g=20, embedding=fake_vector("Peanut butter, smooth")),
    ]
    db.add_all(items)
    db.commit()
    return {f.name.split(",")[0].lower(): f.id for f in items}
