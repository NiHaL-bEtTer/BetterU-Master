import os
import json
import sys
import time
import hashlib
from groq import Groq
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from googleapiclient.discovery import build
from sentence_transformers import SentenceTransformer
from tavily import TavilyClient
from cerebras.cloud.sdk import Cerebras
from pinecone import Pinecone
import httpx

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "Frontend")

sys.path.insert(0, BASE_DIR)
from calculator_tool import nutrition_calculator_tool
from nodes import (
    build_system_prompt,
    CALCULATOR_SYSTEM_PROMPT,
    needs_calculation,
)

# ── Config ────────────────────────────────────────────────────────────────

EMBED_MODEL     = "all-MiniLM-L6-v2"
CHAT_MODEL      = "llama-3.1-8b-instant"
CEREBRAS_MODEL  = "llama3.1-8b"
N_RESULTS       = 6
USDA_API_BASE = "https://api.nal.usda.gov/fdc/v1"
USDA_API_KEY  = os.getenv("USDA_API_KEY")

# Pinecone returns cosine SIMILARITY (higher = better, max 1.0)
# Below this threshold = poor match → trigger Tavily enrichment
KB_CONFIDENCE   = 0.75

# ── Clients ───────────────────────────────────────────────────────────────

groq_client     = Groq(api_key=os.getenv("GROQ_API_KEY"))
tavily_client   = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
cerebras_client = Cerebras(api_key=os.getenv("CEREBRAS_API_KEY"))


# ── Pinecone ──────────────────────────────────────────────────────────────
# No local files — fully hosted, free tier = 1 index, 100k vectors

pc    = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("betteru-data")

# ── Embedding model (loaded once at startup) ──────────────────────────────
# 384 dimensions — matches your betteru-data index exactly

print("Loading embedding model...")
embedder = SentenceTransformer(EMBED_MODEL)
print("Embedding model ready.")

# ── App ───────────────────────────────────────────────────────────────────

app = FastAPI(title="BetterU — Nutrition AI", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Recipe-Video-Id"],
)

# ── Serve frontend ────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def root():
    with open(os.path.join(FRONTEND_DIR, "chat.html")) as f:
        return f.read()

@app.get("/profile", response_class=HTMLResponse)
def profile_page():
    with open(os.path.join(FRONTEND_DIR, "profile.html")) as f:
        return f.read()

# ── Schemas ───────────────────────────────────────────────────────────────

class UserProfile(BaseModel):
    age:      int   = Field(..., ge=10,  le=100)
    sex:      str   = Field(...)
    weight:   float = Field(..., ge=20,  le=300)
    height:   float = Field(..., ge=100, le=250)
    activity: str   = Field(...)
    goal:     str   = Field(...)

class ChatRequest(BaseModel):
    message:      str
    history:      list = []
    profile:      Optional[UserProfile] = None
    calc_results: Optional[dict] = None
    user_notes:   Optional[str] = None

class AldenRequest(BaseModel):
    message: str
    profile: Optional[UserProfile] = None

# ── Embedding ─────────────────────────────────────────────────────────────

def embed_query(text: str) -> list[float]:
    return embedder.encode(text, normalize_embeddings=True).tolist()

def content_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()

# ── Pinecone retrieve ─────────────────────────────────────────────────────

def retrieve(query: str):
    """
    Query Pinecone index.
    NOTE: Pinecone returns cosine SIMILARITY scores (0–1, higher = better).
    This is the opposite of ChromaDB which returned distances (lower = better).
    Text is stored inside each vector's metadata under the 'text' key.
    """
    emb     = embed_query(query)
    results = index.query(
        vector=emb,
        top_k=N_RESULTS,
        include_metadata=True
    )
    matches   = results.get("matches", [])
    documents = [m["metadata"].get("text", "") for m in matches]
    metadatas = [m["metadata"]                  for m in matches]
    scores    = [m["score"]                     for m in matches]
    return metadatas, documents, scores

# ── Pinecone upsert ───────────────────────────────────────────────────────

def upsert_chunks(chunks: list[str], metadata_base: dict):
    """
    Embed and upsert text chunks into Pinecone.
    Pinecone is vector-only so text lives in metadata['text'].
    Batches of 100 to stay within Pinecone's recommended limits.
    """
    if not chunks:
        return

    vectors = []
    for chunk in chunks:
        doc_id    = f"{metadata_base.get('source', 'doc')}_{content_hash(chunk)}"
        embedding = embed_query(chunk)
        meta      = {**metadata_base, "text": chunk}
        vectors.append({"id": doc_id, "values": embedding, "metadata": meta})

    for i in range(0, len(vectors), 100):
        index.upsert(vectors=vectors[i:i + 100])



def usda_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search USDA FoodData Central for foods matching the query.
    Returns a list of simplified food dicts with nutrients.
    Upserts results into Pinecone so the KB grows over time.
    """
    if not USDA_API_KEY:
        print("USDA_API_KEY not set — skipping USDA enrichment")
        return []

    try:
        resp = httpx.get(
            f"{USDA_API_BASE}/foods/search",
            params={
                "api_key":   USDA_API_KEY,
                "query":     query,
                "pageSize":  max_results,
                "dataType":  "Foundation,SR Legacy",  # most reliable nutrient data
            },
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"USDA search failed: {e}")
        return []

    foods = []
    chunks = []

    for item in data.get("foods", []):
        name        = item.get("description", "")
        fdc_id      = item.get("fdcId")
        category    = item.get("foodCategory", "")
        nutrients   = {}

        for n in item.get("foodNutrients", []):
            nutrient_name  = n.get("nutrientName", "")
            nutrient_value = n.get("value")
            nutrient_unit  = n.get("unitName", "")
            if nutrient_value is None:
                continue
            # Capture the key macros + common micros
            key_nutrients = {
                "Energy":               "calories",
                "Protein":              "protein_g",
                "Total lipid (fat)":    "fat_g",
                "Carbohydrate, by difference": "carbs_g",
                "Fiber, total dietary": "fiber_g",
                "Sugars, total":        "sugars_g",
                "Sodium, Na":           "sodium_mg",
                "Calcium, Ca":          "calcium_mg",
                "Iron, Fe":             "iron_mg",
                "Vitamin C, total ascorbic acid": "vitamin_c_mg",
            }
            if nutrient_name in key_nutrients:
                nutrients[key_nutrients[nutrient_name]] = {
                    "value": nutrient_value,
                    "unit":  nutrient_unit,
                }

        food = {
            "name":      name,
            "fdc_id":    fdc_id,
            "category":  category,
            "nutrients": nutrients,
            "source":    "usda_fdc",
        }
        foods.append(food)

        # Build a text chunk for Pinecone
        nut_str = ", ".join(
            f"{k.replace('_', ' ')}: {v['value']}{v['unit']}"
            for k, v in nutrients.items()
        )
        chunk = f"{name} ({category}) — per serving nutrients: {nut_str}."
        chunks.append(chunk)

    if chunks:
        upsert_chunks(chunks, {
            "source":      "usda_fdc",
            "intent":      "nutrition",
            "query":       query,
            "ingested_at": str(int(time.time())),
        })
        print(f"USDA: upserted {len(chunks)} food entries for '{query}'")

    return foods

# ── Cerebras agent router ─────────────────────────────────────────────────

ROUTER_PROMPT = """You are a routing agent for a nutrition and fitness assistant.
Classify the user message into exactly one category:
- nutrition   (food facts, macros)
- calculation (BMI, TDEE, math)
- recipe      (cooking instructions, recipes, "how to make", "show me a video")
- exercise    (workouts)
- general     (greetings, other)
Return ONLY the category name.
"""



_youtube_client = None
_youtube_init_failed = False


def _get_youtube():
    """Lazy-init YouTube Data API client (avoids crash when API key is unset)."""
    global _youtube_client, _youtube_init_failed
    if _youtube_client is not None:
        return _youtube_client
    if _youtube_init_failed:
        return None
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        return None
    try:
        _youtube_client = build("youtube", "v3", developerKey=key)
        return _youtube_client
    except Exception as e:
        print(f"YouTube client init error: {e}")
        _youtube_init_failed = True
        return None


def get_recipe_video(query: str) -> Optional[str]:
    """Return the top embeddable YouTube video id for a recipe-style query."""
    yt = _get_youtube()
    if not yt:
        return None
    q = (query or "").strip()
    if not q:
        return None
    try:
        request = yt.search().list(
            q=f"{q} recipe cooking",
            part="snippet",
            type="video",
            maxResults=1,
            videoEmbeddable="true",
        )
        response = request.execute()
        items = response.get("items") or []
        if not items:
            return None
        vid = items[0].get("id", {}).get("videoId")
        if isinstance(vid, str) and len(vid) == 11:
            return vid
    except Exception as e:
        print(f"YouTube search error: {e}")
    return None


def _looks_like_recipe_request(message: str) -> bool:
    lower = (message or "").lower()
    needles = (
        "recipe",
        "how to make",
        "how do i make",
        "how to cook",
        "cook ",
        "cooking ",
        "bake ",
        "baking ",
        "ingredients for",
        "show me a video",
        "video for",
        "youtube",
        "meal prep",
        "tutorial",
    )
    return any(n in lower for n in needles)


def route_intent(message: str) -> str:
    """
    Cerebras is used here because it is the fastest free inference available.
    We only need a single word back so max_tokens=10 keeps it near-instant.
    Falls back to 'general' if the API call fails for any reason.
    """
    try:
        response = cerebras_client.chat.completions.create(
            model=CEREBRAS_MODEL,
            messages=[
                {"role": "system", "content": ROUTER_PROMPT},
                {"role": "user", "content": message},
            ],
            max_tokens=10,
            temperature=0.0,
            timeout=5,
        )
        intent = response.choices[0].message.content.strip().lower()
        valid = {"nutrition", "calculation", "recipe", "exercise", "guideline", "general"}
        intent = intent if intent in valid else "general"
    except Exception as e:
        print(f"Cerebras routing failed, defaulting to general: {e}")
        intent = "general"

    if intent == "general" and _looks_like_recipe_request(message):
        intent = "recipe"
    return intent

# ── Tavily KB enrichment ──────────────────────────────────────────────────

def tavily_enrich(query: str, intent: str):
    """
    Fires when Pinecone confidence score is below KB_CONFIDENCE.
    Searches Tavily with an intent-aware query, chunks the results,
    and upserts them into Pinecone so the KB grows over time.
    Each call uses 1–3 of your 1000/month free Tavily searches.
    """
    search_map = {
        "nutrition": f"nutritional facts {query} per 100g calories protein carbs fat",
        "exercise":  f"exercise guide {query} muscles targeted proper form how to",
        "guideline": f"WHO Health Canada dietary guideline {query}",
        "recipe":    f"healthy recipe {query} ingredients steps cooking tips",
        "general":   query,
    }
    search_query = search_map.get(intent, query)

    try:
        results = tavily_client.search(
            query=search_query,
            search_depth="advanced",
            max_results=3,
            include_answer=False,
        )
    except Exception as e:
        print(f"Tavily search failed: {e}")
        return

    all_chunks = []
    for result in results.get("results", []):
        content = result.get("content", "").strip()
        url     = result.get("url", "")
        if not content or len(content) < 100:
            continue

        # 400-char chunks with 50-char overlap
        chunks = [content[i:i+400] for i in range(0, len(content), 350)]
        chunks = [c.strip() for c in chunks if len(c.strip()) > 80]
        all_chunks.extend(chunks)

        upsert_chunks(chunks, {
            "source":      "tavily",
            "url":         url,
            "intent":      intent,
            "query":       query,
            "ingested_at": str(int(time.time()))
        })

    if all_chunks:
        print(f"Tavily enriched Pinecone with {len(all_chunks)} chunks for: '{query}'")

# ── Smart retrieve — Pinecone + Tavily fallback ───────────────────────────


    """
    1. Query Pinecone
    2. Check top similarity score against KB_CONFIDENCE threshold
    3. If poor match → enrich from Tavily → re-query Pinecone
    Calculation intents skip enrichment — math is handled by calculator_tool.
    """
    
def smart_retrieve(query: str, intent: str):
    metadatas, documents, scores = retrieve(query)
    best_score = scores[0] if scores else 0.0

    if best_score < KB_CONFIDENCE and intent != "calculation":
        if intent == "nutrition":
            print(f"Low score ({best_score:.2f}) — enriching via USDA FDC")
            usda_search(query)  # upserts into Pinecone as a side effect
        else:
            print(f"Low score ({best_score:.2f}) — enriching via Tavily")
            tavily_enrich(query, intent)

        metadatas, documents, scores = retrieve(query)

    return metadatas, documents, scores

# ── /chat ─────────────────────────────────────────────────────────────────

@app.post("/chat")
def chat(req: ChatRequest):
    intent = route_intent(req.message)

    video_id: Optional[str] = None
    if intent == "recipe":
        video_id = get_recipe_video(req.message)

    foods, docs, scores = smart_retrieve(req.message, intent)
    context = "\n".join(f"{i}. {doc}" for i, doc in enumerate(docs, 1))

    system_text = build_system_prompt(req.profile, req.calc_results, req.user_notes)
    if video_id:
        system_text += (
            "\n\nThe user's app has opened a YouTube recipe video in a side panel for this request. "
            "Briefly acknowledge the video and give clear cooking or prep tips that complement it."
        )

    messages = [{"role": "system", "content": system_text}]
    for turn in req.history[-6:]:
        messages.append(turn)
    messages.append({"role": "user", "content": f"Context:\n{context}\n\nUser question: {req.message}"})

    def generate():
        # Legacy: inline signal (some clients parse stream). Prefer X-Recipe-Video-Id header.
        if video_id:
            yield f"SIGNAL:VIDEO_ID:{video_id}\n"

        stream = groq_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            stream=True,
            temperature=0.3,
        )
        for chunk in stream:
            token = chunk.choices[0].delta.content
            if token:
                yield token

    headers = {}
    if video_id:
        headers["X-Recipe-Video-Id"] = video_id

    return StreamingResponse(generate(), media_type="text/plain", headers=headers)

# ── /calculate ────────────────────────────────────────────────────────────

@app.post("/calculate")
def calculate(profile: UserProfile):
    result = nutrition_calculator_tool({
        "age":      profile.age,
        "sex":      profile.sex,
        "weight":   profile.weight,
        "height":   profile.height,
        "activity": profile.activity,
        "goal":     profile.goal,
    })
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

# ── /alden ────────────────────────────────────────────────────────────────

@app.post("/alden")
def alden(req: AldenRequest):
    calc_results = None

    if needs_calculation(req.message):
        if req.profile is None:
            def ask_for_profile():
                stream = groq_client.chat.completions.create(
                    model=CHAT_MODEL,
                    messages=[
                        {"role": "system", "content": CALCULATOR_SYSTEM_PROMPT},
                        {"role": "user",   "content": (
                            f'The user said: "{req.message}"\n\n'
                            "Ask them in a friendly way to fill in their profile "
                            "on the Profile page first so you can give accurate numbers."
                        )},
                    ],
                    stream=True,
                    temperature=0.3,
                    max_tokens=256
                )
                for chunk in stream:
                    token = chunk.choices[0].delta.content
                    if token:
                        yield token
            return StreamingResponse(ask_for_profile(), media_type="text/plain")

        calc_results = nutrition_calculator_tool({
            "age":      req.profile.age,
            "sex":      req.profile.sex,
            "weight":   req.profile.weight,
            "height":   req.profile.height,
            "activity": req.profile.activity,
            "goal":     req.profile.goal,
        })
        if "error" in calc_results:
            raise HTTPException(status_code=400, detail=calc_results["error"])

        user_message = (
            f'The user said: "{req.message}"\n\n'
            f"[CALCULATOR RESULTS — use ONLY these numbers, do not recalculate]\n"
            f"{json.dumps(calc_results, indent=2)}\n\n"
            "Respond conversationally using these exact numbers. "
            "Explain what BMI, BMR, TDEE, and the macro targets mean for this person."
        )
    else:
        user_message = req.message

    def generate():
        stream = groq_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": CALCULATOR_SYSTEM_PROMPT},
                {"role": "user",   "content": user_message},
            ],
            stream=True,
            temperature=0.3,
            max_tokens=512
        )
        for chunk in stream:
            token = chunk.choices[0].delta.content
            if token:
                yield token

    return StreamingResponse(generate(), media_type="text/plain")

# ── /health ───────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    stats = index.describe_index_stats()
    return {
        "status":      "ok",
        "model":       CHAT_MODEL,
        "embed_model": EMBED_MODEL,
        "pinecone":    "betteru-data",
        "kb_vectors":  stats.get("total_vector_count", 0),
        "ollama":      "removed",
        "chromadb":    "removed — using Pinecone"
    }


class FoodSearchRequest(BaseModel):
    query: str
    max_results: int = 5

@app.post("/food")
def food_search(req: FoodSearchRequest):
    """Direct USDA FoodData Central lookup — returns structured nutrient data."""
    results = usda_search(req.query, req.max_results)
    if not results:
        raise HTTPException(status_code=404, detail="No USDA results found")
    return {"foods": results, "count": len(results)}

# ── wger exercise helpers ─────────────────────────────────────────────────

WGER_BASE = "https://wger.de/api/v2"

# wger category id → readable name
WGER_CATEGORIES = {
    10: "Abs", 8: "Arms", 12: "Back",
    14: "Calves", 15: "Cardio", 11: "Chest",
    9: "Legs", 13: "Shoulders",
}
WGER_CAT_BY_NAME = {v.lower(): k for k, v in WGER_CATEGORIES.items()}

def _wger_exercises_for_category(cat_id: int, limit: int = 20) -> list[dict]:
    """Fetch exercises + their images for one wger category."""
    try:
        resp = httpx.get(
            f"{WGER_BASE}/exerciseinfo/",
            params={"format": "json", "language": 2, "category": cat_id, "limit": limit},
            timeout=10,
        )
        resp.raise_for_status()
    except Exception as e:
        print(f"wger fetch failed: {e}")
        return []

    results = []
    for ex in resp.json().get("results", []):
        # English translation
        eng = next((t for t in ex.get("translations", []) if t.get("language") == 2), None)
        if not eng:
            continue
        name = eng.get("name", "").strip()
        desc = eng.get("description", "").strip()
        # strip HTML tags simply
        import re
        desc = re.sub(r"<[^>]+>", "", desc).strip()

        # images
        images = [img["image"] for img in ex.get("images", []) if img.get("image")]

        muscles = [m.get("name_en") or m.get("name", "") for m in ex.get("muscles", [])]
        equipment = [e.get("name", "") for e in ex.get("equipment", [])]

        results.append({
            "id":        ex["id"],
            "name":      name,
            "desc":      desc[:300] if desc else "",
            "category":  WGER_CATEGORIES.get(cat_id, ""),
            "muscles":   muscles,
            "equipment": equipment,
            "images":    images,
        })
    return results


def _wger_all_exercises(categories: list[str], per_cat: int = 15) -> list[dict]:
    all_ex = []
    for cat_name in categories:
        cat_id = WGER_CAT_BY_NAME.get(cat_name.lower())
        if cat_id:
            all_ex.extend(_wger_exercises_for_category(cat_id, per_cat))
    return all_ex


# ── /workout/generate ─────────────────────────────────────────────────────

class WorkoutRequest(BaseModel):
    message:    str
    profile:    Optional[UserProfile] = None
    user_notes: Optional[str] = None

WORKOUT_SYSTEM = """You are Alden, the BetterU fitness assistant. Given a list of real exercises from the wger database and the user's profile/notes, generate a structured workout plan.

Return ONLY valid JSON — no markdown, no explanation — in this exact shape:
{
  "title": "Workout plan title",
  "description": "One sentence about this plan",
  "days": [
    {
      "day": "Day 1",
      "focus": "Chest & Arms",
      "exercises": [
        {
          "id": <exercise id integer from the list>,
          "name": "Exercise name",
          "sets": 3,
          "reps": "10-12",
          "rest_sec": 60,
          "note": "Optional form tip"
        }
      ]
    }
  ]
}

Rules:
- Pick 4–6 exercises per day, 2–4 days total based on what the user asked.
- Only use exercises from the provided list (match by id).
- Tailor sets/reps to the user's goal (weight loss → higher reps/lower rest; muscle gain → lower reps/heavier).
- Keep notes short (one sentence max).
- Return nothing except the JSON object."""

@app.post("/workout/generate")
def generate_workout(req: WorkoutRequest):
    """
    1. AI decides which muscle groups to target from user message + profile.
    2. Fetch real exercises from wger for those categories.
    3. Ask Groq to build a structured plan from those exercises.
    4. Enrich each exercise with wger image URLs.
    """

    # Step 1 — decide categories
    profile_ctx = ""
    if req.profile:
        profile_ctx = (
            f"Goal: {req.profile.goal}, Activity: {req.profile.activity}, "
            f"Age: {req.profile.age}, Sex: {req.profile.sex}"
        )
    notes_ctx = (req.user_notes or "").strip()[:1000]

    category_prompt = (
        f"User request: {req.message}\n"
        f"Profile: {profile_ctx}\n"
        f"Notes: {notes_ctx}\n\n"
        "List the muscle group categories to target (comma-separated, pick from: "
        "abs, arms, back, calves, cardio, chest, legs, shoulders). "
        "Return ONLY the comma-separated list."
    )

    try:
        cat_resp = groq_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "user", "content": category_prompt}],
            temperature=0.0,
            max_tokens=40,
        )
        raw_cats = cat_resp.choices[0].message.content.strip().lower()
        categories = [c.strip() for c in raw_cats.split(",") if c.strip() in WGER_CAT_BY_NAME]
    except Exception as e:
        print(f"Category routing failed: {e}")
        categories = ["chest", "back", "legs"]

    if not categories:
        categories = ["chest", "back", "legs"]

    # Step 2 — fetch exercises from wger
    exercises = _wger_all_exercises(categories, per_cat=18)
    if not exercises:
        raise HTTPException(status_code=503, detail="Could not fetch exercises from wger API")

    # Build concise exercise list for the prompt (just id + name + category + muscles)
    ex_summary = "\n".join(
        f"[{ex['id']}] {ex['name']} ({ex['category']}"
        + (f", muscles: {', '.join(ex['muscles'])}" if ex['muscles'] else "") + ")"
        for ex in exercises
    )

    # Step 3 — Groq generates the plan
    plan_prompt = (
        f"User request: {req.message}\n"
        f"Profile: {profile_ctx}\n"
        f"Notes: {notes_ctx}\n\n"
        f"Available exercises:\n{ex_summary}\n\n"
        "Generate the workout plan JSON as instructed."
    )

    try:
        plan_resp = groq_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": WORKOUT_SYSTEM},
                {"role": "user",   "content": plan_prompt},
            ],
            temperature=0.4,
            max_tokens=1200,
        )
        raw_json = plan_resp.choices[0].message.content.strip()
        # Strip markdown code fences if model adds them
        if raw_json.startswith("```"):
            raw_json = raw_json.split("```")[1]
            if raw_json.startswith("json"):
                raw_json = raw_json[4:]
        plan = json.loads(raw_json)
    except Exception as e:
        print(f"Workout plan generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Plan generation failed: {e}")

    # Step 4 — enrich with wger image URLs
    ex_map = {ex["id"]: ex for ex in exercises}
    for day in plan.get("days", []):
        for ex in day.get("exercises", []):
            ex_id = ex.get("id")
            wger_ex = ex_map.get(ex_id, {})
            ex["images"] = wger_ex.get("images", [])
            ex["muscles"]   = wger_ex.get("muscles", [])
            ex["equipment"] = wger_ex.get("equipment", [])
            ex["desc"]      = wger_ex.get("desc", "")

    return plan