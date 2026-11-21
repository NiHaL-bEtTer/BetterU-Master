"""Tools Alden can call. Each tool returns a JSON-serialisable dict for the
model, and may also register sources, actions or a video on the ToolContext
so the web app can render them."""

import json
import logging
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from betteru.clients.external import web_search, youtube_recipe_video
from betteru.models import User
from betteru.services import food_log
from betteru.services.foods import food_summary, get_food, nutrients_for, search_foods_with_fallback
from betteru.services.retrieval import search_knowledge

log = logging.getLogger(__name__)


@dataclass
class ToolContext:
    db: Session
    user: User
    sources: dict[str, dict] = field(default_factory=dict)  # id -> Source
    actions: list[dict] = field(default_factory=list)
    relied_on: list[str] = field(default_factory=list)  # sources whose data went into totals/logs
    last_meal_items: list[dict] = field(default_factory=list)  # from the latest calculate_meal call
    video_id: str | None = None
    _doc_ids: dict[int, str] = field(default_factory=dict)
    _web_count: int = 0

    def cite_food(self, food) -> str:
        sid = f"F{food.id}"
        self.sources.setdefault(sid, {"id": sid, "title": food.name, "url": _food_url(food), "kind": "food"})
        return sid

    def cite_doc(self, chunk) -> str:
        if chunk.document_id not in self._doc_ids:
            sid = f"S{len(self._doc_ids) + 1}"
            self._doc_ids[chunk.document_id] = sid
            self.sources[sid] = {"id": sid, "title": chunk.title, "url": chunk.url, "kind": "document"}
        return self._doc_ids[chunk.document_id]

    def cite_web(self, title: str, url: str) -> str:
        self._web_count += 1
        sid = f"W{self._web_count}"
        self.sources[sid] = {"id": sid, "title": title or url, "url": url, "kind": "web"}
        return sid


def _food_url(food) -> str:
    if food.source.startswith("usda"):
        return f"https://fdc.nal.usda.gov/food-details/{food.source_id}/nutrients"
    if food.source == "off":
        return f"https://world.openfoodfacts.org/product/{food.source_id}"
    return ""


def _grams_for(food, raw) -> tuple[float, str | None]:
    """Grams for an item; if the model omitted them, assume one portion (or 100 g) and say so."""
    try:
        g = float(raw)
        if g > 0:
            return g, None
    except (TypeError, ValueError):
        pass
    if food.portions:
        p = food.portions[0]
        return p.grams, f"assumed {p.description} ({p.grams:g} g)"
    return 100.0, "assumed 100 g"


def _allergy_flags(name: str, user: User) -> list[str]:
    p = user.profile
    if not p:
        return []
    lowered = name.lower()
    return [a for a in p.allergies if a and a.lower() in lowered]


# ── Tool implementations ──────────────────────────────────────────────────


def t_search_foods(ctx: ToolContext, query: str) -> dict:
    foods = search_foods_with_fallback(ctx.db, query, limit=4)
    out = []
    for f in foods:
        item = food_summary(f)
        item["cite_as"] = ctx.cite_food(f)
        flags = _allergy_flags(f.name, ctx.user)
        if flags:
            item["allergy_warning"] = f"Contains {', '.join(flags)} — the user is allergic."
        out.append(item)
    return {"results": out, "note": "Nutrients are per 100 g. Use portions to convert to servings."}


def t_calculate_meal(ctx: ToolContext, items: list[dict]) -> dict:
    lines, totals = [], {"kcal": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
    for it in items[:30]:
        food = get_food(ctx.db, int(it.get("food_id", 0)))
        if not food:
            lines.append({"error": f"Unknown food_id {it.get('food_id')}"})
            continue
        grams, note = _grams_for(food, it.get("grams"))
        n = nutrients_for(food, grams)
        for k in totals:
            totals[k] += n[k]
        line = {"food": food.name, "grams": grams, "cite_as": ctx.cite_food(food), **n}
        ctx.relied_on.append(line["cite_as"])
        if note:
            line["note"] = note
        lines.append(line)
    ctx.last_meal_items = [{"food_id": int(it.get("food_id", 0)), "grams": it.get("grams")} for it in items[:30]]
    return {"items": lines, "totals": {k: round(v, 1) for k, v in totals.items()}}


def t_get_today(ctx: ToolContext) -> dict:
    s = food_log.day_summary(ctx.db, ctx.user, date.today())
    remaining = None
    if s.targets:
        remaining = {
            "kcal": round(s.targets.recommended_calories - s.totals.kcal),
            "protein_g": round(s.targets.macros.protein_g - s.totals.protein_g),
            "carbs_g": round(s.targets.macros.carbs_g - s.totals.carbs_g),
            "fat_g": round(s.targets.macros.fat_g - s.totals.fat_g),
        }
    return {
        "entries": [{"meal": e.meal, "food": e.name, "grams": e.grams, "kcal": e.kcal} for e in s.entries],
        "totals": s.totals.model_dump(),
        "remaining": remaining,
    }


def t_search_knowledge(ctx: ToolContext, query: str, topic: str | None = None) -> dict:
    category = topic if topic in {"nutrition", "guideline", "supplement", "exercise"} else None
    chunks = search_knowledge(ctx.db, query, category=category, limit=5)
    if not chunks and category:
        chunks = search_knowledge(ctx.db, query, limit=5)
    results = [{"cite_as": ctx.cite_doc(c), "title": c.title, "section": c.heading, "text": c.content} for c in chunks]
    ctx.relied_on.extend(r["cite_as"] for r in results[:2])  # top hits, shown if the answer cites nothing
    return {"results": results}


def t_web_search(ctx: ToolContext, query: str) -> dict:
    results = web_search(query)
    if not results:
        return {"results": [], "note": "Web search unavailable or returned nothing."}
    return {"results": [{"cite_as": ctx.cite_web(r["title"], r["url"]), **r} for r in results]}


def t_propose_meal_log(ctx: ToolContext, meal: str, items: list[dict]) -> dict:
    clean = []
    for it in items[:30]:
        food = get_food(ctx.db, int(it.get("food_id", 0)))
        if food:
            grams, _ = _grams_for(food, it.get("grams"))
            clean.append({"food_id": food.id, "grams": round(grams, 1), "name": food.name,
                          "cite_as": ctx.cite_food(food), **nutrients_for(food, grams)})
            ctx.relied_on.append(clean[-1]["cite_as"])
    if not clean:
        return {"error": "No valid foods to log. Search for the foods first and use their food_id."}
    meal = meal if meal in {"breakfast", "lunch", "dinner", "snack"} else "snack"
    kcal = round(sum(c["kcal"] for c in clean))
    ctx.actions.append({
        "type": "log_meal",
        "label": f"Log {meal}, {kcal} kcal",
        "payload": {"meal": meal, "items": clean},
    })
    totals = {k: round(sum(c[k] for c in clean), 1) for k in ("kcal", "protein_g", "carbs_g", "fat_g")}
    return {"status": "A 'Log meal' button is now shown to the user. Tell them to tap it to confirm.",
            "items": [{k: c[k] for k in ("name", "grams", "cite_as", "kcal", "protein_g", "carbs_g", "fat_g")} for c in clean],
            "totals": totals}


def t_propose_workout_plan(ctx: ToolContext, request: str) -> dict:
    ctx.actions.append({"type": "build_workout", "label": "Build this workout plan", "payload": {"request": request}})
    return {"status": "A 'Build workout plan' button is now shown to the user."}


def t_find_recipe_video(ctx: ToolContext, dish: str) -> dict:
    vid = youtube_recipe_video(dish)
    if vid:
        ctx.video_id = vid
        return {"status": "A recipe video is now shown next to the chat."}
    return {"status": "No video available."}


TOOLS = {
    "search_foods": t_search_foods,
    "calculate_meal": t_calculate_meal,
    "get_today": t_get_today,
    "search_knowledge": t_search_knowledge,
    "web_search": t_web_search,
    "propose_meal_log": t_propose_meal_log,
    "propose_workout_plan": t_propose_workout_plan,
    "find_recipe_video": t_find_recipe_video,
}

STATUS_TEXT = {
    "search_foods": "Looking up foods…",
    "calculate_meal": "Adding up nutrients…",
    "get_today": "Checking today's log…",
    "search_knowledge": "Searching the knowledge base…",
    "web_search": "Checking trusted sources…",
    "propose_meal_log": "Preparing your meal log…",
    "propose_workout_plan": "Preparing a workout plan…",
    "find_recipe_video": "Finding a recipe video…",
}

_ITEMS = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "food_id": {"type": "integer", "description": "food_id from search_foods"},
            "grams": {"type": "number", "description": "Amount eaten in grams (convert portions using search_foods results)"},
        },
        "required": ["food_id"],
    },
}


def _fn(name: str, description: str, properties: dict | None = None, required: list[str] | None = None) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties or {}, "required": required or []},
        },
    }


def tool_specs(*, web_enabled: bool, video_enabled: bool) -> list[dict]:
    specs = [
        _fn("search_foods", "Find foods in the USDA-based food database, including branded/packaged products. Returns food_id, nutrients per 100 g and common portions. Use a short food name; include the brand for packaged foods (e.g. 'clif bar chocolate chip').",
            {"query": {"type": "string", "description": "e.g. 'chicken breast', 'oatmeal', 'banana'"}}, ["query"]),
        _fn("calculate_meal", "Exact nutrient totals for foods and gram amounts. Not needed when logging: propose_meal_log returns totals too.", {"items": _ITEMS}, ["items"]),
        _fn("get_today", "The user's food log for today, totals, and what's left of their targets."),
        _fn("search_knowledge", "Search trusted nutrition and health documents (NIH, WHO, Dietary Guidelines, Canada's Food Guide). Write a complete, specific query.",
            {"query": {"type": "string"},
             "topic": {"type": "string", "enum": ["nutrition", "guideline", "supplement", "exercise"]}}, ["query"]),
        _fn("propose_meal_log", "Show the user a one-tap button to log these foods. Only after looking the foods up.",
            {"meal": {"type": "string", "enum": ["breakfast", "lunch", "dinner", "snack"]}, "items": _ITEMS},
            ["meal", "items"]),
        _fn("propose_workout_plan", "Show the user a button that builds a personalised workout plan.",
            {"request": {"type": "string", "description": "What the user wants, e.g. '3-day upper/lower split, no barbell'"}},
            ["request"]),
    ]
    if web_enabled:
        specs.append(_fn("web_search", "Search trusted health websites. Only when search_knowledge found nothing useful.",
                         {"query": {"type": "string"}}, ["query"]))
    if video_enabled:
        specs.append(_fn("find_recipe_video", "Show a recipe video for a dish.",
                         {"dish": {"type": "string"}}, ["dish"]))
    return specs


def run_tool(ctx: ToolContext, name: str, arguments: str) -> str:
    fn = TOOLS.get(name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool {name}"})
    try:
        args = json.loads(arguments or "{}")
        if not isinstance(args, dict):
            raise ValueError("arguments must be an object")
        return json.dumps(fn(ctx, **args), default=str, separators=(",", ":"))
    except Exception as e:  # noqa: BLE001 — report tool errors back to the model
        log.warning("Tool %s failed: %s", name, e)
        return json.dumps({"error": f"{type(e).__name__}: {e}"})
