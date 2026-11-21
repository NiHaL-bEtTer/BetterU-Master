"""Load trusted nutrition & health documents into the RAG knowledge base.

Sources (all public, freely reusable health information):
  - MedlinePlus Medical Encyclopedia nutrition articles (US National Library of Medicine)
  - WHO fact sheets on diet and physical activity
  - Health Canada's dietary guidelines
  - Any PDFs dropped into data/pdfs/ (e.g. Dietary Guidelines for Americans,
    ISSN position stands — check each PDF's licence first)

A document is re-embedded only when its text changes (content hash), so
re-running ingestion is cheap.
"""

import hashlib
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from betteru.ingest.chunking import chunk_sections, html_sections, text_sections
from betteru.models import Chunk, Document
from betteru.services.embeddings import embed_documents

log = logging.getLogger(__name__)

USER_AGENT = "BetterU-ingest/1.0 (nutrition app knowledge base)"


@dataclass
class WebSource:
    source: str
    url: str
    category: str
    selectors: list[str]


MEDLINEPLUS = [
    ("002399", "nutrition"), ("002400", "nutrition"), ("002401", "nutrition"), ("002402", "nutrition"),
    ("002403", "nutrition"), ("002404", "nutrition"), ("002405", "nutrition"), ("002406", "nutrition"),
    ("002407", "nutrition"), ("002408", "nutrition"), ("002409", "nutrition"), ("002410", "nutrition"),
    ("002411", "nutrition"), ("002412", "nutrition"), ("002413", "nutrition"), ("002415", "nutrition"),
    ("002416", "nutrition"), ("002417", "nutrition"), ("002418", "nutrition"), ("002419", "nutrition"),
    ("002420", "nutrition"), ("002421", "nutrition"), ("002422", "nutrition"), ("002423", "nutrition"),
    ("002467", "nutrition"), ("002469", "nutrition"), ("002470", "nutrition"), ("002136", "nutrition"),
    ("002444", "nutrition"), ("002445", "nutrition"), ("002459", "guideline"), ("002458", "exercise"),
    ("002096", "nutrition"), ("001942", "guideline"),
]
WHO_PAGES = [
    ("healthy-diet", "guideline"), ("obesity-and-overweight", "guideline"), ("salt-reduction", "guideline"),
    ("physical-activity", "exercise"), ("malnutrition", "guideline"), ("diabetes", "guideline"),
]
CANADA_PAGES = [
    "https://www.canada.ca/en/health-canada/services/food-guide/explore/dietary-guidelines.html",
    "https://www.canada.ca/en/health-canada/services/food-guide/explore/healthy-eating-recommendations.html",
]

WEB_SOURCES: list[WebSource] = (
    [WebSource("medlineplus", f"https://medlineplus.gov/ency/article/{aid}.htm", cat, ["article", "#mplus-content"])
     for aid, cat in MEDLINEPLUS]
    + [WebSource("who", f"https://www.who.int/news-room/fact-sheets/detail/{slug}", cat,
                 [".sf-detail-body-wrapper", "article"]) for slug, cat in WHO_PAGES]
    + [WebSource("health_canada", url, "guideline", ["main", "article"]) for url in CANADA_PAGES]
)


def _store(db: Session, source: str, key: str, title: str, url: str, category: str, version: str,
           chunks, force: bool) -> str:
    text_all = "\n".join(c.content for c in chunks)
    digest = hashlib.sha256(text_all.encode()).hexdigest()
    doc = db.scalar(select(Document).where(Document.source == source, Document.source_key == key))
    if doc and doc.content_hash == digest and not force:
        return "unchanged"
    if not chunks:
        return "empty"
    vectors = embed_documents([c.content for c in chunks])
    if doc is None:
        doc = Document(source=source, source_key=key, title=title, url=url, category=category,
                       version=version, content_hash=digest)
        db.add(doc)
        db.flush()
    else:
        doc.title, doc.url, doc.category, doc.version, doc.content_hash = title, url, category, version, digest
        db.execute(delete(Chunk).where(Chunk.document_id == doc.id))
    db.add_all(
        Chunk(document_id=doc.id, ordinal=i, heading=c.heading[:300], content=c.content, embedding=v)
        for i, (c, v) in enumerate(zip(chunks, vectors, strict=True))
    )
    db.commit()
    return f"{len(chunks)} chunks"


def ingest_web(db: Session, force: bool = False) -> int:
    failures = 0
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30, follow_redirects=True) as client:
        for src in WEB_SOURCES:
            try:
                r = client.get(src.url)
                r.raise_for_status()
                title, sections = html_sections(r.text, src.selectors)
                chunks = chunk_sections(title, sections)
                result = _store(db, src.source, src.url, title or src.url, src.url, src.category,
                                time.strftime("%Y-%m"), chunks, force)
                log.info("%-14s %-60s %s", src.source, title[:60], result)
            except Exception as e:  # noqa: BLE001 — one bad page shouldn't stop the run
                failures += 1
                db.rollback()
                log.warning("Failed %s: %s", src.url, e)
            time.sleep(0.5)  # be polite to public servers
    return failures


def ingest_pdfs(db: Session, pdf_dir: Path, force: bool = False) -> None:
    import pymupdf as fitz

    for pdf in sorted(pdf_dir.glob("*.pdf")):
        with fitz.open(pdf) as doc:
            pages = [page.get_text() for page in doc]
            title = (doc.metadata or {}).get("title") or pdf.stem.replace("_", " ")
        chunks = chunk_sections(title, text_sections(pages))
        result = _store(db, "pdf", pdf.name, title, "", "guideline", pdf.stem, chunks, force)
        log.info("pdf            %-60s %s", pdf.name[:60], result)
