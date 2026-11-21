"""Food search and nutrient maths.

Search combines three signals with reciprocal-rank fusion (RRF):
  1. Postgres full-text search on name + category
  2. Embedding similarity on the food name (handles synonyms, rough typos)
  3. Trigram similarity when the pg_trgm extension is installed (strong typo tolerance)
Raw/whole foods get a small boost so "egg" finds "Egg, whole, raw" before
"Egg custard pie".
"""

import re

from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from betteru.db import has_trigram
from betteru.models import Food
from betteru.services.embeddings import embed_query

MACRO_FIELDS = ("kcal", "protein_g", "carbs_g", "fat_g")
PART_WORDS = ("yolk", "white", "oil", "flour", "powder", "dehydrated", "dried", "juice", "baby food",
              "frozen", "canned", "substitute", "imitation", "with ")

_SEARCH_SQL = """
WITH q AS (SELECT websearch_to_tsquery('english', :query) AS tsq),
fts AS (
    SELECT f.id, row_number() OVER (ORDER BY ts_rank_cd(f.search_tsv, q.tsq) DESC, length(f.name)) AS r
    FROM foods f, q
    WHERE f.search_tsv @@ q.tsq
    ORDER BY r LIMIT 50
),
pfx AS (
    -- Prefix match on each word's first letters: catches typos like "chiken brest"
    SELECT f.id, row_number() OVER (ORDER BY ts_rank_cd(f.search_tsv, to_tsquery('english', :prefix)) DESC, length(f.name)) AS r
    FROM foods f
    WHERE :prefix <> '' AND f.search_tsv @@ to_tsquery('english', :prefix)
    ORDER BY r LIMIT 50
),
vec AS (
    SELECT id, row_number() OVER (ORDER BY embedding <=> CAST(:embedding AS vector)) AS r
    FROM foods WHERE embedding IS NOT NULL
    ORDER BY embedding <=> CAST(:embedding AS vector) LIMIT 50
)
{trgm_cte}
SELECT id, sum(score) AS score FROM (
    SELECT id, 1.0 / (60 + r) AS score FROM fts
    UNION ALL SELECT id, 1.0 / (60 + r) FROM vec
    UNION ALL SELECT id, 1.0 / (60 + r) FROM pfx
    {trgm_union}
) s
GROUP BY id
"""

_TRGM_CTE = """,
trg AS (
    SELECT id, row_number() OVER (ORDER BY similarity(name, :query) DESC) AS r
    FROM foods WHERE name % :query
    ORDER BY r LIMIT 50
)"""


def search_foods(db: Session, query: str, limit: int = 10) -> list[Food]:
    query = query.strip()
    if not query:
        return []
    trgm = has_trigram()
    sql = _SEARCH_SQL.format(
        trgm_cte=_TRGM_CTE if trgm else "",
        trgm_union="UNION ALL SELECT id, 1.0 / (60 + r) FROM trg" if trgm else "",
    )
    words = [w for w in re.findall(r"[a-z]+", query.lower())]
    prefix = " & ".join(f"{w[:3]}:*" for w in words if len(w) >= 3)
    rows = db.execute(
        text(sql), {"query": query, "prefix": prefix, "embedding": str(embed_query(query))}
    ).all()
    if not rows:
        return []

    foods = {
        f.id: f
        for f in db.scalars(
            select(Food).where(Food.id.in_([r.id for r in rows])).options(selectinload(Food.portions))
        )
    }

    def final_score(row) -> float:
        food = foods[row.id]
        name = food.name.lower()
        score = float(row.score)
        if all(w in name for w in words):
            score += 0.01
        if "raw" in name or food.source == "usda_foundation":
            score += 0.004
        if words and name.startswith(words[0]):
            score += 0.004
        if "whole" in name:
            score += 0.003
        # Parts or processed forms rank lower unless the user asked for them.
        if any(p in name and p not in words for p in PART_WORDS):
            score -= 0.015
        return score

    ranked = sorted((r for r in rows if r.id in foods), key=final_score, reverse=True)
    # The same product often appears several times (e.g. separate UPCs); show it once.
    out, seen = [], set()
    for r in ranked:
        f = foods[r.id]
        key = (f.name.lower(), round(f.kcal or 0))
        if key not in seen:
            seen.add(key)
            out.append(f)
        if len(out) >= limit:
            break
    return out


def _word_stem(w: str) -> str:
    return w[:-1] if len(w) > 3 and w.endswith("s") else w


def is_weak_match(foods: list[Food], query: str) -> bool:
    """True when no result contains every meaningful word of the query
    (e.g. a brand name like "clif" that only the branded dataset has)."""
    words = [_word_stem(w) for w in re.findall(r"[a-z0-9]+", query.lower()) if len(w) >= 3]
    if not words:
        return False
    for f in foods:
        name = f.name.lower()
        if all(w in name for w in words):
            return False
    return True


def search_foods_with_fallback(db: Session, query: str, limit: int = 10) -> list[Food]:
    """Local search; if it looks weak, fetch branded foods from USDA and search again."""
    from betteru.services.branded import lookup_branded

    foods = search_foods(db, query, limit=limit)
    if is_weak_match(foods, query) and lookup_branded(db, query):
        foods = search_foods(db, query, limit=limit)
    return foods


def get_food(db: Session, food_id: int) -> Food | None:
    return db.scalar(select(Food).where(Food.id == food_id).options(selectinload(Food.portions)))


def nutrients_for(food: Food, grams: float) -> dict[str, float]:
    factor = grams / 100.0
    return {f: round((getattr(food, f) or 0.0) * factor, 1) for f in MACRO_FIELDS}


def food_summary(food: Food) -> dict:
    """Compact dict for the LLM: per-100 g nutrients plus common portions."""
    per100 = {
        k: getattr(food, k)
        for k in (
            "kcal", "protein_g", "carbs_g", "fat_g", "fiber_g", "sugar_g",
            "sat_fat_g", "sodium_mg", "potassium_mg", "calcium_mg", "iron_mg",
            "vitamin_c_mg", "vitamin_d_ug",
        )
        if getattr(food, k) is not None
    }
    return {
        "food_id": food.id,
        "name": food.name,
        "category": food.category,
        "source": food.source,
        "per_100g": per100,
        "portions": [{"description": p.description, "grams": p.grams} for p in food.portions[:4]],
    }


def food_from_barcode(db: Session, barcode: str) -> Food | None:
    """Return the food for a barcode, fetching and caching it from Open Food Facts."""
    from sqlalchemy import func

    from betteru.clients.external import open_food_facts_product
    from betteru.models import FoodPortion
    from betteru.services.branded import lookup_barcode
    from betteru.services.embeddings import embed_documents

    # UPC/EAN codes are often stored with different leading-zero padding.
    existing = db.scalar(
        select(Food).where(func.ltrim(Food.barcode, "0") == barcode.lstrip("0")).options(selectinload(Food.portions))
    )
    if existing:
        return existing

    product = open_food_facts_product(barcode)
    if not product:
        # Not in Open Food Facts: try USDA's branded foods (US products).
        found = lookup_barcode(db, barcode)
        return get_food(db, found.id) if found else None
    n = product.get("nutriments") or {}

    def val(key: str, scale: float = 1.0) -> float | None:
        v = n.get(f"{key}_100g")
        try:
            return round(float(v) * scale, 3) if v is not None else None
        except (TypeError, ValueError):
            return None

    name = (product.get("product_name") or "").strip() or f"Product {barcode}"
    brand = (product.get("brands") or "").split(",")[0].strip()
    full_name = f"{name} ({brand})" if brand else name
    food = Food(
        source="off",
        source_id=barcode,
        barcode=barcode,
        name=full_name[:300],
        category=(product.get("categories") or "").split(",")[0].strip()[:200],
        kcal=val("energy-kcal"),
        protein_g=val("proteins"),
        fat_g=val("fat"),
        carbs_g=val("carbohydrates"),
        fiber_g=val("fiber"),
        sugar_g=val("sugars"),
        sat_fat_g=val("saturated-fat"),
        sodium_mg=val("sodium", 1000),
        embedding=embed_documents([full_name])[0],
    )
    serving_g = product.get("serving_quantity")
    try:
        if serving_g and float(serving_g) > 0:
            food.portions.append(
                FoodPortion(description=f"1 serving ({product.get('serving_size') or ''})".strip(), grams=float(serving_g))
            )
    except (TypeError, ValueError):
        pass
    db.add(food)
    db.commit()
    db.refresh(food)
    return food
