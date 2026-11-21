from betteru.ingest.chunking import chunk_sections, html_sections

HTML = """<html><body><article><h1>Protein in diet: MedlinePlus</h1>
<p>Proteins are the building blocks of life.</p>
<h2>Food Sources</h2><p>Meat, fish, eggs and beans are good sources.</p>
<h2>References</h2><p>Some citation.</p></article></body></html>"""


def test_sections_and_prefix():
    title, sections = html_sections(HTML, ["article"])
    assert title == "Protein in diet"
    assert [s.heading for s in sections] == ["Overview", "Food Sources"]  # References skipped
    chunks = chunk_sections(title, sections)
    assert chunks[1].content.startswith("Protein in diet — Food Sources\n")


def test_long_sections_split_with_overlap():
    from betteru.ingest.chunking import Section

    paras = [f"Paragraph {i} " + "x" * 300 for i in range(8)]
    chunks = chunk_sections("T", [Section("H", paras)])
    assert len(chunks) > 1
    assert chunks[1].content.split("\n")[1] == chunks[0].content.split("\n")[-1]  # one-paragraph overlap
