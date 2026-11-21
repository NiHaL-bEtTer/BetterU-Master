"""Load free-exercise-db (public domain, ~870 exercises with images)."""

import logging

import httpx
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from betteru.models import Exercise

log = logging.getLogger(__name__)

DATA_URL = "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/dist/exercises.json"
IMAGE_BASE = "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises/"


def ingest_exercises(db: Session, force: bool = False) -> None:
    existing = db.scalar(select(func.count()).select_from(Exercise))
    if existing and not force:
        log.info("exercises: %d already loaded, skipping (use --force to reload)", existing)
        return
    r = httpx.get(DATA_URL, timeout=60, follow_redirects=True)
    r.raise_for_status()
    rows = [
        {
            "slug": ex["id"][:120],
            "name": ex["name"][:200],
            "category": ex.get("category") or "",
            "level": ex.get("level") or "",
            "equipment": ex.get("equipment") or "body only",
            "primary_muscles": ex.get("primaryMuscles") or [],
            "secondary_muscles": ex.get("secondaryMuscles") or [],
            "instructions": ex.get("instructions") or [],
            "images": [IMAGE_BASE + img for img in ex.get("images") or []],
        }
        for ex in r.json()
    ]
    # Upsert by slug so ids stay stable: saved plans and logged sets keep pointing at the same exercise.
    stmt = insert(Exercise)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Exercise.slug],
        set_={c: stmt.excluded[c] for c in rows[0] if c != "slug"},
    )
    db.execute(stmt, rows)
    db.commit()
    log.info("exercises: loaded %d", len(rows))
