"""
BetterU — Pinecone Ingestion Agent
------------------------------------
Pulls data from authoritative nutrition, exercise, and guideline sources
and upserts everything into your Pinecone betteru-data index.

Install:
    pip install pinecone-client sentence-transformers requests \
                beautifulsoup4 pymupdf tqdm python-dotenv

Usage:
    python ingest.py          # runs everything
    python ingest.py --skip-usda   # skip the large USDA download
"""

import os
import json
import hashlib
import logging
import argparse
import zipfile
import time
from pathlib import Path
from datetime import datetime

import requests
from bs4 import BeautifulSoup
import fitz  # pymupdf
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────

BASE_DIR     = Path(__file__).parent
RAW_DIR      = BASE_DIR / "raw_downloads"
LOG_FILE     = BASE_DIR / "ingestion.log"
VERSION_LOG  = BASE_DIR / "version_log.json"

EMBED_MODEL  = "all-MiniLM-L6-v2"   # 384 dims — matches betteru-data index
CHUNK_SIZE   = 400
CHUNK_OVERLAP = 50
BATCH_SIZE   = 100                   # Pinecone upsert batch size

RAW_DIR.mkdir(exist_ok=True)
(RAW_DIR / "pdfs").mkdir(exist_ok=True)
(RAW_DIR / "cnf").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
log = logging.getLogger(__name__)

# ── Pinecone + Embedder ───────────────────────────────────────────────────

log.info("Connecting to Pinecone...")
pc    = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("betteru-data")

log.info("Loading embedding model...")
embedder = SentenceTransformer(EMBED_MODEL)
log.info("Ready.")

# ── Version log ───────────────────────────────────────────────────────────

def load_version_log() -> dict:
    if VERSION_LOG.exists():
        return json.loads(VERSION_LOG.read_text())
    return {}

def save_version_log(data: dict):
    VERSION_LOG.write_text(json.dumps(data, indent=2))

def already_ingested(key: str, version: str) -> bool:
    return load_version_log().get(key) == version

def mark_ingested(key: str, version: str):
    vlog = load_version_log()
    vlog[key] = version
    save_version_log(vlog)

# ── Helpers ───────────────────────────────────────────────────────────────

def content_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:12]

def chunk_text(text: str) -> list[str]:
    text  = text.strip()
    if not text:
        return []
    chunks, start = [], 0
    step = CHUNK_SIZE - CHUNK_OVERLAP
    while start < len(text):
        chunk = text[start:start + CHUNK_SIZE].strip()
        if len(chunk) > 60:
            chunks.append(chunk)
        start += step
    return chunks

def embed(texts: list[str]) -> list[list[float]]:
    return embedder.encode(texts, normalize_embeddings=True).tolist()

# ── Pinecone upsert ───────────────────────────────────────────────────────

def upsert_to_pinecone(chunks: list[str], metadata_base: dict) -> int:
    """
    Embeds chunks and upserts into Pinecone in batches of 100.
    Text is stored inside metadata['text'] since Pinecone is vector-only.
    Returns number of vectors upserted.
    """
    if not chunks:
        return 0

    vectors = []
    for chunk in chunks:
        vid  = f"{metadata_base.get('source', 'doc')}_{content_hash(chunk)}"
        meta = {**metadata_base, "text": chunk}

        # Pinecone metadata values must be str, int, float, bool, or list of str
        # Sanitise anything that might be a dict or None
        meta = {k: (str(v) if not isinstance(v, (str, int, float, bool, list)) else v)
                for k, v in meta.items() if v is not None}

        vectors.append({
            "id":       vid,
            "values":   embed([chunk])[0],
            "metadata": meta
        })

    for i in range(0, len(vectors), BATCH_SIZE):
        index.upsert(vectors=vectors[i:i + BATCH_SIZE])
        time.sleep(0.1)   # be kind to the free tier rate limits

    return len(vectors)

# ═══════════════════════════════════════════════════════════════════════════
# SOURCE 1 — USDA FoodData Central
# ═══════════════════════════════════════════════════════════════════════════

def ingest_usda():
    key     = "usda_fdc"
    version = "2024-10"

    if already_ingested(key, version):
        log.info("USDA already ingested, skipping.")
        return

    log.info("=== USDA FoodData Central ===")

    url      = "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_foundation_food_json_2024-10-31.zip"
    zip_path = RAW_DIR / "usda_foundation.zip"

    if not zip_path.exists():
        log.info("Downloading USDA Foundation Foods (~30MB)...")
        r = requests.get(url, stream=True, timeout=180)
        with open(zip_path, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        log.info("Download complete.")

    with zipfile.ZipFile(zip_path) as z:
        json_name = [n for n in z.namelist() if n.endswith(".json")][0]
        data      = json.loads(z.read(json_name))

    foods = data.get("FoundationFoods", [])
    log.info(f"Processing {len(foods)} foods...")

    total = 0
    for food in tqdm(foods, desc="USDA"):
        name     = food.get("description", "")
        category = food.get("foodCategory", {}).get("description", "")
        lines    = []

        for n in food.get("foodNutrients", []):
            nutrient = n.get("nutrient", {}).get("name", "")
            amount   = n.get("amount", "")
            unit     = n.get("nutrient", {}).get("unitName", "")
            if nutrient and amount != "":
                lines.append(f"  {nutrient}: {amount} {unit}")

        text   = f"Food: {name}\nCategory: {category}\nNutrients per 100g:\n" + "\n".join(lines)
        chunks = chunk_text(text)
        total += upsert_to_pinecone(chunks, {
            "source":       key,
            "category":     "nutrition_facts",
            "jurisdiction": "US",
            "food_name":    name,
            "version":      version,
            "ingested_at":  datetime.utcnow().isoformat()
        })

    mark_ingested(key, version)
    log.info(f"USDA done — {total} vectors upserted.")

# ═══════════════════════════════════════════════════════════════════════════
# SOURCE 2 — Health Canada CNF (manual download required)
# ═══════════════════════════════════════════════════════════════════════════

def ingest_health_canada_cnf():
    key     = "health_canada_cnf"
    version = "2024"

    if already_ingested(key, version):
        log.info("Health Canada CNF already ingested, skipping.")
        return

    cnf_dir    = RAW_DIR / "cnf"
    food_file  = cnf_dir / "FOOD NAME.csv"
    nutr_file  = cnf_dir / "NUTRIENT AMOUNT.csv"

    if not food_file.exists() or not nutr_file.exists():
        log.warning(
            "Health Canada CNF files not found.\n"
            "Download from: https://www.canada.ca/en/health-canada/services/"
            "food-nutrition/healthy-eating/nutrient-data.html\n"
            f"Place 'FOOD NAME.csv' and 'NUTRIENT AMOUNT.csv' in: {cnf_dir}"
        )
        return

    import csv
    log.info("=== Health Canada CNF ===")

    foods = {}
    with open(food_file, encoding="latin-1") as f:
        for row in csv.DictReader(f):
            fid        = row.get("FoodID") or row.get("Food_ID", "")
            foods[fid] = row.get("FoodDescription") or row.get("Food_Description", "")

    nutrients_by_food: dict[str, list[str]] = {}
    with open(nutr_file, encoding="latin-1") as f:
        for row in csv.DictReader(f):
            fid  = row.get("FoodID") or row.get("Food_ID", "")
            name = row.get("NutrientName") or row.get("Nutrient_Name", "")
            val  = row.get("NutrientValue") or row.get("Nutrient_Value", "")
            unit = row.get("NutrientUnit") or row.get("Nutrient_Unit", "")
            nutrients_by_food.setdefault(fid, []).append(f"  {name}: {val} {unit}")

    total = 0
    for fid, name in tqdm(foods.items(), desc="CNF"):
        text   = f"Food: {name}\nNutrients per 100g (Health Canada):\n" + "\n".join(nutrients_by_food.get(fid, []))
        chunks = chunk_text(text)
        total += upsert_to_pinecone(chunks, {
            "source":       key,
            "category":     "nutrition_facts",
            "jurisdiction": "CA",
            "food_name":    name,
            "version":      version,
            "ingested_at":  datetime.utcnow().isoformat()
        })

    mark_ingested(key, version)
    log.info(f"Health Canada CNF done — {total} vectors upserted.")

# ═══════════════════════════════════════════════════════════════════════════
# SOURCE 3 — ExerciseDB (open GitHub mirror, no API key needed)
# ═══════════════════════════════════════════════════════════════════════════

def ingest_exercisedb():
    key     = "exercisedb"
    version = "2025-01"

    if already_ingested(key, version):
        log.info("ExerciseDB already ingested, skipping.")
        return

    log.info("=== ExerciseDB ===")

    url       = "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/dist/exercises.json"
    exercises = requests.get(url, timeout=60).json()
    log.info(f"Processing {len(exercises)} exercises...")

    total = 0
    for ex in tqdm(exercises, desc="Exercises"):
        name        = ex.get("name", "")
        body_part   = ex.get("bodyPart", "")
        equipment   = ex.get("equipment", "")
        target      = ex.get("target", "")
        secondary   = ", ".join(ex.get("secondaryMuscles", []))
        instructions = " ".join(ex.get("instructions", []))

        text = (
            f"Exercise: {name}\n"
            f"Body part: {body_part}\n"
            f"Target muscle: {target}\n"
            f"Secondary muscles: {secondary}\n"
            f"Equipment: {equipment}\n"
            f"Instructions: {instructions}"
        )
        chunks = chunk_text(text)
        total += upsert_to_pinecone(chunks, {
            "source":      key,
            "category":    "exercise",
            "body_part":   body_part,
            "target":      target,
            "equipment":   equipment,
            "food_name":   name,
            "version":     version,
            "ingested_at": datetime.utcnow().isoformat()
        })

    mark_ingested(key, version)
    log.info(f"ExerciseDB done — {total} vectors upserted.")

# ═══════════════════════════════════════════════════════════════════════════
# SOURCE 4 — WHO dietary guideline pages (web scrape)
# ═══════════════════════════════════════════════════════════════════════════

def ingest_who_guidelines():
    key     = "who_dietary"
    version = "2025-04"

    if already_ingested(key, version):
        log.info("WHO guidelines already ingested, skipping.")
        return

    log.info("=== WHO Dietary Guidelines ===")

    pages = [
        ("https://www.who.int/news-room/fact-sheets/detail/healthy-diet",           "healthy_diet"),
        ("https://www.who.int/news-room/fact-sheets/detail/obesity-and-overweight",  "obesity"),
        ("https://www.who.int/news-room/fact-sheets/detail/salt-reduction",          "salt_reduction"),
        ("https://www.who.int/news-room/fact-sheets/detail/sugars-and-dental-caries","sugars"),
    ]

    headers = {"User-Agent": "Mozilla/5.0 (compatible; BetterU-Bot/1.0)"}
    total   = 0

    for url, topic in pages:
        try:
            soup  = BeautifulSoup(requests.get(url, headers=headers, timeout=30).text, "html.parser")
            block = soup.find("div", class_="sf-detail-body-wrapper") or soup.find("article") or soup.find("body")
            text  = "\n".join(p.get_text(strip=True) for p in block.find_all(["p","li","h2","h3"]) if p.get_text(strip=True))
            n     = upsert_to_pinecone(chunk_text(text), {
                "source":       key,
                "category":     "dietary_guidelines",
                "topic":        topic,
                "jurisdiction": "global",
                "url":          url,
                "version":      version,
                "ingested_at":  datetime.utcnow().isoformat()
            })
            total += n
            log.info(f"  WHO {topic}: {n} vectors")
        except Exception as e:
            log.error(f"  Failed {url}: {e}")

    mark_ingested(key, version)
    log.info(f"WHO done — {total} vectors upserted.")

# ═══════════════════════════════════════════════════════════════════════════
# SOURCE 5 — Canada Food Guide (web scrape)
# ═══════════════════════════════════════════════════════════════════════════

def ingest_canada_food_guide():
    key     = "canada_food_guide"
    version = "2025-04"

    if already_ingested(key, version):
        log.info("Canada Food Guide already ingested, skipping.")
        return

    log.info("=== Canada Food Guide ===")

    pages = [
        "https://food-guide.canada.ca/en/",
        "https://food-guide.canada.ca/en/guidelines/",
        "https://food-guide.canada.ca/en/healthy-eating-recommendations/",
        "https://food-guide.canada.ca/en/tips-for-healthy-eating/",
    ]

    headers = {"User-Agent": "Mozilla/5.0 (compatible; BetterU-Bot/1.0)"}
    total   = 0

    for url in pages:
        try:
            soup = BeautifulSoup(requests.get(url, headers=headers, timeout=30).text, "html.parser")
            text = "\n".join(t.get_text(strip=True) for t in soup.find_all(["p","li","h2","h3"]) if t.get_text(strip=True))
            n    = upsert_to_pinecone(chunk_text(text), {
                "source":       key,
                "category":     "dietary_guidelines",
                "jurisdiction": "CA",
                "url":          url,
                "version":      version,
                "ingested_at":  datetime.utcnow().isoformat()
            })
            total += n
            log.info(f"  CFG {url}: {n} vectors")
        except Exception as e:
            log.error(f"  Failed {url}: {e}")

    mark_ingested(key, version)
    log.info(f"Canada Food Guide done — {total} vectors upserted.")

# ═══════════════════════════════════════════════════════════════════════════
# SOURCE 6 — PDF guidelines (drop files into raw_downloads/pdfs/)
# ═══════════════════════════════════════════════════════════════════════════

PDF_CONFIGS = {
    # filename stem (lowercase, spaces → _) : (source_key, category, jurisdiction)
    "who_physical_activity_2020": ("who_physical_activity", "exercise_guidelines", "global"),
    "acsm_guidelines":            ("acsm_guidelines",       "exercise_guidelines", "US"),
    "dietitians_of_canada":       ("dietitians_canada",     "dietary_guidelines",  "CA"),
}

def ingest_pdf(pdf_path: Path):
    stem   = pdf_path.stem.lower().replace(" ", "_")
    config = PDF_CONFIGS.get(stem, (f"pdf_{stem}", "guidelines", "unknown"))
    key, category, jurisdiction = config
    version = stem

    if already_ingested(key, version):
        log.info(f"PDF {key} already ingested, skipping.")
        return

    log.info(f"=== PDF: {pdf_path.name} ===")
    doc   = fitz.open(str(pdf_path))
    text  = "\n".join(page.get_text() for page in doc)
    n     = upsert_to_pinecone(chunk_text(text), {
        "source":       key,
        "category":     category,
        "jurisdiction": jurisdiction,
        "pdf_file":     pdf_path.name,
        "version":      version,
        "ingested_at":  datetime.utcnow().isoformat()
    })
    mark_ingested(key, version)
    log.info(f"PDF {key} done — {n} vectors upserted.")

def ingest_all_pdfs():
    pdf_dir = RAW_DIR / "pdfs"
    pdfs    = list(pdf_dir.glob("*.pdf"))
    if not pdfs:
        log.info("No PDFs found in raw_downloads/pdfs/ — skipping.")
        return
    for pdf in pdfs:
        ingest_pdf(pdf)

# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="BetterU Pinecone Ingestion Agent")
    parser.add_argument("--skip-usda", action="store_true", help="Skip the large USDA download")
    args = parser.parse_args()

    log.info("========================================")
    log.info("  BetterU Ingestion Agent — Pinecone")
    log.info("========================================")

    stats = index.describe_index_stats()
    log.info(f"Pinecone index: betteru-data | vectors before: {stats.get('total_vector_count', 0)}")

    if not args.skip_usda:
        ingest_usda()
    else:
        log.info("Skipping USDA (--skip-usda flag set)")

    ingest_health_canada_cnf()
    ingest_exercisedb()
    ingest_who_guidelines()
    ingest_canada_food_guide()
    ingest_all_pdfs()

    stats = index.describe_index_stats()
    log.info("========================================")
    log.info(f"  Done! Pinecone vectors: {stats.get('total_vector_count', 0)}")
    log.info("========================================")

if __name__ == "__main__":
    main()