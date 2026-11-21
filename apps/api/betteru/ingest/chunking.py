"""Heading-aware chunking.

Documents are split into sections at their headings, then sections are packed
into ~1,000-character chunks on paragraph boundaries with one paragraph of
overlap. Every chunk starts with "Title — Section" so it still makes sense when
retrieved on its own.
"""

from dataclasses import dataclass

from bs4 import BeautifulSoup

TARGET_CHARS = 1000
SKIP_SECTIONS = {
    "images", "references", "alternative names", "related medlineplus health topics",
    "related information", "browse the encyclopedia", "learn how to cite this page",
}


@dataclass
class Section:
    heading: str
    paragraphs: list[str]


@dataclass
class TextChunk:
    heading: str
    content: str


def html_sections(html: str, container_selectors: list[str]) -> tuple[str, list[Section]]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "form", "noscript"]):
        tag.decompose()
    root = None
    for sel in container_selectors:
        root = soup.select_one(sel)
        if root:
            break
    root = root or soup.body or soup
    title_el = root.find("h1") or soup.find("title")
    title = title_el.get_text(" ", strip=True).split(":")[0].strip() if title_el else ""

    sections: list[Section] = [Section(heading="Overview", paragraphs=[])]
    for el in root.find_all(["h2", "h3", "h4", "p", "li"]):
        text = el.get_text(" ", strip=True)
        if not text:
            continue
        if el.name in {"h2", "h3", "h4"}:
            sections.append(Section(heading=text[:200], paragraphs=[]))
        elif el.name == "li" and el.find(["p", "li"]):
            continue  # nested list item: its children are visited separately
        else:
            sections[-1].paragraphs.append(text)
    clean = [
        s for s in sections
        if s.paragraphs and not any(s.heading.lower().startswith(skip) for skip in SKIP_SECTIONS)
        and not s.heading.lower().startswith("review date")
    ]
    return title, clean


def chunk_sections(title: str, sections: list[Section]) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    for sec in sections:
        prefix = f"{title} — {sec.heading}\n" if title else f"{sec.heading}\n"
        current: list[str] = []
        size = 0
        for para in sec.paragraphs:
            if current and size + len(para) > TARGET_CHARS:
                chunks.append(TextChunk(sec.heading, prefix + "\n".join(current)))
                current = current[-1:]  # one paragraph of overlap
                size = len(current[0])
            current.append(para)
            size += len(para)
        if current:
            chunks.append(TextChunk(sec.heading, prefix + "\n".join(current)))
    # Drop exact duplicates created by overlap on tiny sections.
    seen, unique = set(), []
    for c in chunks:
        if c.content not in seen:
            seen.add(c.content)
            unique.append(c)
    return unique


def text_sections(pages: list[str]) -> list[Section]:
    """Sections for PDF text: one per page, split into paragraphs."""
    out = []
    for i, page in enumerate(pages, 1):
        paras = [" ".join(p.split()) for p in page.split("\n\n")]
        paras = [p for p in paras if len(p) > 40]
        if paras:
            out.append(Section(heading=f"Page {i}", paragraphs=paras))
    return out
