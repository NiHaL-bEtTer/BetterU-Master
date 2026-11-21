"""Load USDA FoodData Central bulk datasets into the `foods` table.

  Foundation Foods   ~400 whole foods, the most carefully analysed data
  SR Legacy          ~7,800 foods, the classic USDA reference
  Survey (FNDDS)     ~5,400 foods as people eat them ("pizza, cheese", "chicken stir fry")

All nutrient values are per 100 g.
"""

import json
import logging
import zipfile
from pathlib import Path

import httpx
from sqlalchemy import delete, func, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from betteru.models import Food, FoodPortion
from betteru.services.embeddings import embed_documents

log = logging.getLogger(__name__)

BASE_URL = "https://fdc.nal.usda.gov/fdc-datasets/"
DATASETS = {
    "usda_foundation": ("FoodData_Central_foundation_food_json_2026-10-29.zip", "FoundationFoods"),
    "usda_sr_legacy": ("FoodData_Central_sr_legacy_food_json_2018-04.zip", "SRLegacyFoods"),
    "usda_survey": ("FoodData_Central_survey_food_json_2024-10-31.zip", "SurveyFoods"),
}

# USDA nutrient id -> our column. Energy has several ids; first match wins.
ENERGY_IDS = (1008, 2048, 2047)
NUTRIENTS = {
    1003: "protein_g", 1004: "fat_g", 1005: "carbs_g", 1079: "fiber_g",
    2000: "sugar_g", 1063: "sugar_g", 1258: "sat_fat_g", 1093: "sodium_mg",
    1092: "potassium_mg", 1087: "calcium_mg", 1089: "iron_mg", 1162: "vitamin_c_mg",
    1114: "vitamin_d_ug",
}


def download(filename: str, raw_dir: Path) -> Path:
    path = raw_dir / filename
    if path.exists():
        return path
    raw_dir.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    log.info("Downloading %s", filename)
    with httpx.stream("GET", BASE_URL + filename, timeout=300, follow_redirects=True) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
    tmp.replace(path)
    return path


def _portion_description(p: dict) -> str | None:
    if p.get("portionDescription"):
        desc = p["portionDescription"]
        return None if desc.lower().startswith("quantity not specified") else desc
    unit = (p.get("measureUnit") or {}).get("name", "")
    amount = p.get("amount") or p.get("value") or 1
    amount_s = f"{amount:g}" if isinstance(amount, int | float) else str(amount)
    modifier = (p.get("modifier") or "").strip()
    if modifier.isdigit():
        modifier = ""
    if unit == "RACC":
        return "1 serving (reference amount)"
    if unit in ("", "undetermined"):
        return f"{amount_s} {modifier}".strip() if modifier else None
    return f"{amount_s} {unit}" + (f", {modifier}" if modifier else "")


def parse_food(item: dict, source: str) -> tuple[dict, list[dict]] | None:
    values: dict[str, float] = {}
    energy = {}
    for n in item.get("foodNutrients", []):
        nid = (n.get("nutrient") or {}).get("id")
        amount = n.get("amount")
        if amount is None:
            continue
        if nid in ENERGY_IDS:
            energy[nid] = float(amount)
        elif nid in NUTRIENTS and NUTRIENTS[nid] not in values:
            values[NUTRIENTS[nid]] = float(amount)
    kcal = next((energy[i] for i in ENERGY_IDS if i in energy), None)
    if kcal is None:
        return None  # no energy data: not useful for logging

    category = (item.get("foodCategory") or {}).get("description") or (
        item.get("wweiaFoodCategory") or {}
    ).get("wweiaFoodCategoryDescription", "")
    food = {
        "source": source,
        "source_id": str(item["fdcId"]),
        "name": item.get("description", "").strip()[:300],
        "category": (category or "")[:200],
        "kcal": round(kcal, 2),
        **{k: round(v, 3) for k, v in values.items()},
    }
    portions = []
    seen = set()
    for p in item.get("foodPortions", []):
        grams = p.get("gramWeight") or 0
        desc = _portion_description(p)
        if grams > 0 and desc and desc not in seen:
            seen.add(desc)
            portions.append({"description": desc[:200], "grams": float(grams)})
    return food, portions


def ingest_foods(db: Session, raw_dir: Path, force: bool = False) -> None:
    for source, (filename, key) in DATASETS.items():
        existing = db.scalar(select(func.count()).select_from(Food).where(Food.source == source))
        if existing and not force:
            log.info("%s: %d foods already loaded, skipping (use --force to reload)", source, existing)
            continue

        path = download(filename, raw_dir)
        with zipfile.ZipFile(path) as z:
            data = json.loads(z.read(z.namelist()[0]))
        parsed = [p for p in (parse_food(i, source) for i in data[key]) if p]
        log.info("%s: %d foods parsed, embedding names…", source, len(parsed))

        embeddings = embed_documents([f["name"] for f, _ in parsed])
        rows = [f | {"embedding": e} for (f, _), e in zip(parsed, embeddings, strict=True)]
        # Every row must carry the same keys for a bulk upsert.
        columns = {k for r in rows for k in r}
        rows = [{k: r.get(k) for k in columns} for r in rows]
        # Upsert on (source, source_id) so food ids stay stable: favorites and
        # logged meals keep pointing at the same food after a reload.
        stmt = pg_insert(Food)
        stmt = stmt.on_conflict_do_update(
            index_elements=[Food.source, Food.source_id],
            set_={c: stmt.excluded[c] for c in columns if c not in ("source", "source_id")},
        ).returning(Food.id, Food.source_id)
        ids = db.execute(stmt, rows).all()
        id_by_source = {sid: fid for fid, sid in ids}
        db.execute(delete(FoodPortion).where(FoodPortion.food_id.in_(list(id_by_source.values()))))
        portion_rows = [
            {"food_id": id_by_source[f["source_id"]], **p}
            for f, portions in parsed for p in portions
        ]
        if portion_rows:
            db.execute(insert(FoodPortion), portion_rows)
        db.commit()
        log.info("%s: loaded %d foods, %d portions", source, len(rows), len(portion_rows))
