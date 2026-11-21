"""Live USDA lookup for branded (packaged) foods.

The bulk datasets cover whole foods and common dishes. Branded products
(~450k) are too large to preload, so when a local search looks weak — e.g.
"clif bar chocolate chip" — we ask the FoodData Central API, save the results
into `foods`, and serve every later search for them locally.

Needs USDA_API_KEY (free: https://fdc.nal.usda.gov/api-key-signup). Without
it, this module does nothing.
"""

import logging
import re
import time

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from betteru.config import get_settings
from betteru.ingest.foods import ENERGY_IDS, NUTRIENTS
from betteru.models import Food, FoodPortion
from betteru.services.embeddings import embed_documents

log = logging.getLogger(__name__)

SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
SOURCE = "usda_branded"
PAGE_SIZE = 15
# Remember recent lookups so repeated searches don't spend API quota (1,000 requests/hour).
_RECENT: dict[str, float] = {}
_RECENT_TTL = 6 * 3600
_SMALL_WORDS = {"and", "or", "of", "with", "in", "a", "the", "&"}


def _clean_name(description: str, brand: str) -> str:
    desc = description.strip()
    # USDA sometimes repeats the description twice: "X, Y, X, Y".
    parts = [p.strip() for p in desc.split(",")]
    half = len(parts) // 2
    if len(parts) % 2 == 0 and half and parts[:half] == parts[half:]:
        desc = ", ".join(parts[:half])
    desc = " ".join(w.lower() if w.lower() in _SMALL_WORDS else w.capitalize() for w in desc.lower().split())
    brand = brand.strip().title()
    if brand and brand.lower() not in desc.lower():
        desc = f"{brand} {desc}"
    return desc[:300]


def _parse(item: dict) -> tuple[dict, list[dict]] | None:
    values, energy = {}, None
    for n in item.get("foodNutrients", []):
        nid, value = n.get("nutrientId"), n.get("value")
        if value is None:
            continue
        if nid in ENERGY_IDS and (n.get("unitName") or "").upper() == "KCAL" and energy is None:
            energy = float(value)
        elif nid in NUTRIENTS and NUTRIENTS[nid] not in values:
            values[NUTRIENTS[nid]] = round(float(value), 3)
    if energy is None:
        return None
    food = {
        "source": SOURCE,
        "source_id": str(item["fdcId"]),
        "name": _clean_name(item.get("description", ""), item.get("brandName") or item.get("brandOwner") or ""),
        "category": (item.get("foodCategory") or "")[:200],
        "barcode": (item.get("gtinUpc") or "").strip()[:32] or None,
        "kcal": round(energy, 2),
        **values,
    }
    portions = []
    size, unit = item.get("servingSize"), (item.get("servingSizeUnit") or "").upper()
    if size and unit in ("G", "GRM", "GM", "ML", "MLT"):  # ml treated as ~g for drinks
        label = (item.get("householdServingFullText") or "").strip().lower() or "serving"
        portions.append({"description": f"1 {label}" if not label[0].isdigit() else label, "grams": float(size)})
    return food, portions


def _fetch(params: dict) -> list[dict]:
    key = get_settings().usda_api_key
    if not key:
        return []
    try:
        r = httpx.get(SEARCH_URL, params={"api_key": key, "dataType": "Branded", "pageSize": PAGE_SIZE, **params},
                      timeout=8)
        r.raise_for_status()
        return r.json().get("foods", [])
    except Exception as e:  # noqa: BLE001 — optional feature, never break search
        log.warning("USDA branded lookup failed: %s", e)
        return []


def _store(db: Session, items: list[dict]) -> int:
    parsed = [p for p in (_parse(i) for i in items) if p]
    if not parsed:
        return 0
    rows = [f for f, _ in parsed]
    columns = {k for r in rows for k in r}
    vectors = embed_documents([r["name"] for r in rows])
    rows = [{k: r.get(k) for k in columns} | {"embedding": v} for r, v in zip(rows, vectors, strict=True)]
    stmt = insert(Food)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Food.source, Food.source_id],
        set_={c: stmt.excluded[c] for c in [*columns, "embedding"] if c not in ("source", "source_id")},
    ).returning(Food.id, Food.source_id)
    ids = {sid: fid for fid, sid in db.execute(stmt, rows).all()}
    existing = set(db.scalars(select(FoodPortion.food_id).where(FoodPortion.food_id.in_(ids.values()))))
    for food, portions in parsed:
        fid = ids[food["source_id"]]
        if fid not in existing:
            db.add_all(FoodPortion(food_id=fid, **p) for p in portions)
    db.commit()
    return len(rows)


def _normalise(query: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", query.lower()))


def lookup_branded(db: Session, query: str) -> int:
    """Fetch branded foods matching `query` into the local table. Returns how many were saved."""
    key = _normalise(query)
    now = time.time()
    if not key or not get_settings().usda_api_key or now - _RECENT.get(key, 0) < _RECENT_TTL:
        return 0
    _RECENT[key] = now
    saved = _store(db, _fetch({"query": query}))
    log.info("USDA branded lookup %r: saved %d foods", query, saved)
    return saved


def lookup_barcode(db: Session, barcode: str) -> Food | None:
    """Find a packaged food by barcode in USDA's branded data."""
    items = [i for i in _fetch({"query": barcode}) if (i.get("gtinUpc") or "").lstrip("0") == barcode.lstrip("0")]
    if not items or not _store(db, items[:1]):
        return None
    return db.scalar(select(Food).where(Food.source == SOURCE, Food.source_id == str(items[0]["fdcId"])))
