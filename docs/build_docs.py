"""
Build the VANTA PDFs from Markdown sources.

    python3 docs/build_docs.py              # technical documentation (docs/src)
    python3 docs/build_docs.py strategy     # scope & strategy (docs/strategy/src)

Pipeline: Markdown -> HTML (numbered chapters/sections, highlighted code,
inline SVG diagrams) -> PDF with headless Chromium (Playwright). Two passes:
the first PDF's outline tells us which page every heading landed on, the
second pass writes those numbers into the table of contents. The cover is
rendered separately (no page footer) and merged in front.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import subprocess
import sys
from pathlib import Path

import markdown
from pygments.formatters import HtmlFormatter
from pypdf import PdfReader, PdfWriter

DOCS = Path(__file__).resolve().parent
ROOT = DOCS.parent
RENDER = DOCS / "render_pdf.cjs"

DOCSETS = {
    "technical": {
        "src": DOCS / "src",
        "out": DOCS / "VANTA-Technical-Documentation.pdf",
        "title": "VANTA — Technical documentation",
        "subject": "Every concept, feature and file of the VANTA project",
        "footer": "VANTA · Technical documentation",
        "tag": "technical documentation",
        "motto": '"Don\'t give the contestant a problem. <em>Give them a world.</em>"',
        "what": ("A complete guide to the project: every concept, every feature, every file, the "
                 "HTTP API, the database, the C protocols, testing, operations, limitations, how to "
                 "extend it, and how to present it."),
        "stats": None,  # computed from the repository
    },
    "strategy": {
        "src": DOCS / "strategy" / "src",
        "out": DOCS / "VANTA-Scope-and-Strategy.pdf",
        "title": "VANTA — Scope, learning, competition and industry strategy",
        "subject": "What VANTA is for, how students learn with it, competition formats, and a path to industry",
        "footer": "VANTA · Scope & strategy",
        "tag": "scope · learning · competition · industry",
        "motto": 'One engine that generates broken systems. <em>Three things built on it: learn, compete, assess.</em>',
        "what": ("What VANTA's scope really is, how to make students learn from it, how to run "
                 "Battlecode-, ICPC- and hackathon-style competitions with DSA and competitive "
                 "programming inside, and how it could succeed as an industry product."),
        "stats": [("product modes", "3"), ("competition formats", "6"),
                  ("proposed defect classes", "20"), ("roadmap phases", "4")],
    },
}
DS = DOCSETS["technical"]

CSS = r"""
@page { size: A4; margin: 17mm 17mm 19mm 17mm; }
* { box-sizing: border-box; }
html { font-family: Inter, "DejaVu Sans", sans-serif; font-size: 9.6pt; color: #1d2433; }
body { margin: 0; line-height: 1.55; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
p { margin: 0 0 7pt; }
a { color: #1f6f8b; text-decoration: none; }
strong { font-weight: 650; }
h1, h2, h3, h4 { font-family: "Inter Display", Inter, sans-serif; color: #121826; line-height: 1.25; }
h1 { font-size: 22pt; font-weight: 700; margin: 0 0 14pt; padding-top: 4pt; break-before: page;
     border-bottom: 2.5pt solid #1f7a99; padding-bottom: 8pt; letter-spacing: -0.01em; }
h1 .num { display: block; font-size: 9.5pt; font-weight: 600; color: #1f7a99; letter-spacing: 0.14em;
          text-transform: uppercase; margin-bottom: 4pt; }
h2 { font-size: 14pt; font-weight: 650; margin: 18pt 0 7pt; break-after: avoid; }
h2 .num { color: #1f7a99; margin-right: 6pt; font-weight: 600; }
h3 { font-size: 11.2pt; font-weight: 650; margin: 13pt 0 5pt; break-after: avoid; }
h4 { font-size: 10pt; font-weight: 650; margin: 10pt 0 4pt; break-after: avoid; }
h3 code, h4 code { font-size: 0.92em; }
ul, ol { margin: 0 0 8pt; padding-left: 16pt; }
li { margin: 1.5pt 0; }
blockquote { margin: 8pt 0 10pt; padding: 7pt 12pt; border-left: 3pt solid #c27a12;
             background: #fdf6ea; color: #3b3324; font-style: italic; }
blockquote p:last-child { margin: 0; }
code { font-family: "DejaVu Sans Mono", "Liberation Mono", monospace; font-size: 0.86em;
       background: #eef1f5; padding: 0.5pt 3pt; border-radius: 2.5pt; color: #2a3346; }
pre { font-family: "DejaVu Sans Mono", "Liberation Mono", monospace; font-size: 7.7pt; line-height: 1.45;
      background: #f6f8fa; border: 0.6pt solid #d9dee6; border-left: 2.5pt solid #1f7a99;
      border-radius: 3pt; padding: 7pt 9pt; margin: 6pt 0 10pt; white-space: pre-wrap;
      word-break: break-word; }
pre code { background: none; padding: 0; font-size: 1em; }
.hl { margin: 6pt 0 10pt; }
.hl pre { margin: 0; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 11pt; font-size: 8.5pt;
        break-inside: auto; }
thead { display: table-header-group; }
tr { break-inside: avoid; }
th { text-align: left; background: #1d2433; color: #fff; font-weight: 600; padding: 4pt 6pt;
     border: 0.6pt solid #1d2433; }
td { padding: 3.5pt 6pt; border: 0.6pt solid #d4d9e1; vertical-align: top; }
tbody tr:nth-child(even) td { background: #f7f9fb; }
td code, th code { font-size: 0.9em; white-space: normal; word-break: break-word; }
td:first-child { min-width: 31mm; }
figure.diagram { margin: 10pt 0 14pt; break-inside: avoid; text-align: center; }
figure.diagram svg { width: 100%; height: auto; max-height: 205mm; }
figcaption { font-size: 8.3pt; color: #5b6475; margin-top: 4pt; font-style: italic; }
.callout { border: 0.8pt solid #1f7a99; background: #eef7fa; border-radius: 4pt; padding: 7pt 10pt;
           margin: 8pt 0 11pt; break-inside: avoid; }
.callout.warn { border-color: #c27a12; background: #fdf6ea; }
.callout.good { border-color: #2f8f72; background: #edf7f2; }
.callout p:last-child { margin-bottom: 0; }
.callout .t { font-weight: 650; display: block; margin-bottom: 2pt; }
.file { break-inside: avoid-page; }
.filehead { display: flex; justify-content: space-between; align-items: baseline;
            border-top: 1.2pt solid #1f7a99; margin-top: 13pt; padding-top: 4pt; }
.filehead .path { font-family: "DejaVu Sans Mono", monospace; font-size: 9.6pt; font-weight: 700; color: #121826; }
.filehead .meta { font-size: 8pt; color: #5b6475; }
hr { border: none; border-top: 0.6pt solid #d4d9e1; margin: 12pt 0; }
/* table of contents */
.toc h1 { break-before: auto; }
.toc ol { list-style: none; padding: 0; margin: 0; }
.toc li.ch { margin-top: 7pt; font-weight: 650; font-size: 10.2pt; }
.toc li.sec { font-size: 8.9pt; padding-left: 16pt; margin: 1pt 0; color: #2a3346; }
.toc .row { display: flex; align-items: baseline; }
.toc .row .label { flex: 0 1 auto; }
.toc .row .dots { flex: 1 1 auto; border-bottom: 0.7pt dotted #9aa3b2; margin: 0 4pt; transform: translateY(-2.5pt); }
.toc .row .pg { flex: 0 0 auto; font-variant-numeric: tabular-nums; min-width: 14pt; text-align: right; }
.toc .n { color: #1f7a99; display: inline-block; min-width: 22pt; }
"""

COVER_CSS = r"""
@page { size: A4; margin: 0; }
html, body { margin: 0; height: 100%; font-family: Inter, sans-serif; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.cover { height: 297mm; width: 210mm; background: #0e1420; color: #dde6f2; position: relative; overflow: hidden; }
.grid { position: absolute; inset: 0;
  background-image: linear-gradient(#1c2638 1px, transparent 1px), linear-gradient(90deg, #1c2638 1px, transparent 1px);
  background-size: 11mm 11mm; }
.glow { position: absolute; inset: 0; background: radial-gradient(ellipse at 30% 25%, transparent 0%, #0e1420 75%); }
.inner { position: absolute; left: 22mm; right: 22mm; top: 48mm; }
.tag { font-family: "DejaVu Sans Mono", monospace; font-size: 9pt; letter-spacing: 0.2em; color: #e8a33d; text-transform: uppercase; }
.dot { display: inline-block; width: 6pt; height: 6pt; border-radius: 50%; background: #e8a33d; margin-right: 7pt; }
h1 { font-family: "Inter Display", Inter, sans-serif; font-size: 64pt; margin: 14mm 0 2mm; letter-spacing: 0.04em; color: #fff; font-weight: 800; }
.expand { font-size: 13pt; color: #93a3bd; margin: 0; }
.motto { margin-top: 16mm; font-size: 19pt; line-height: 1.35; color: #dde6f2; max-width: 150mm; font-weight: 500; }
.motto em { color: #7fd1e8; font-style: normal; }
.what { margin-top: 12mm; font-size: 11.5pt; line-height: 1.6; color: #93a3bd; max-width: 150mm; }
.stats { position: absolute; left: 22mm; right: 22mm; bottom: 30mm; display: flex; gap: 6mm; }
.stat { flex: 1; border: 1px solid #273449; background: rgba(20,28,43,0.85); border-radius: 3mm; padding: 4mm 5mm; }
.stat .k { font-family: "DejaVu Sans Mono", monospace; font-size: 7.5pt; color: #5f708d; letter-spacing: 0.12em; text-transform: uppercase; }
.stat .v { font-size: 20pt; font-weight: 700; color: #fff; margin-top: 1mm; }
.foot { position: absolute; left: 22mm; right: 22mm; bottom: 14mm; font-size: 8.5pt; color: #5f708d; display: flex; justify-content: space-between; }
"""


def _slug_num(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text)).strip()


def repo_stats() -> dict:
    files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    code = [f for f in files if f.endswith((".py", ".ts", ".tsx", ".css", ".cjs", ".sh"))
            and not f.startswith("docs/")]
    lines = 0
    for f in code:
        try:
            lines += sum(1 for _ in open(ROOT / f, encoding="utf-8", errors="ignore"))
        except OSError:
            pass
    tests = 0
    py = ROOT / "backend" / ".venv" / "bin" / "python3"
    out = subprocess.run([str(py), "-m", "pytest", "--collect-only", "-q", "tests"],
                         cwd=ROOT / "backend", capture_output=True, text=True).stdout
    m = re.search(r"(\d+) tests? collected", out)
    tests = int(m.group(1)) if m else 0
    return {"files": len(files), "code_files": len(code), "lines": lines, "test_cases": tests}


def build_body(page_map: dict[str, int] | None) -> tuple[str, list[dict]]:
    chapters = sorted(DS["src"].glob("*.md"))
    toc: list[dict] = []
    parts: list[str] = []
    for ci, path in enumerate(chapters, start=1):
        md = markdown.Markdown(
            extensions=["tables", "fenced_code", "codehilite", "toc", "attr_list", "md_in_html",
                        "sane_lists"],
            extension_configs={"codehilite": {"guess_lang": False, "css_class": "hl"},
                               "toc": {"slugify": lambda v, s: f"c{ci}-" + re.sub(r"[^a-z0-9]+", "-", v.lower()).strip("-")}},
        )
        text = path.read_text(encoding="utf-8")
        # {{lines:path}} -> current line count of that file in the repository.
        text = re.sub(r"\{\{lines:([^}]+)\}\}",
                      lambda m: str(sum(1 for _ in open(ROOT / m.group(1), encoding="utf-8",
                                                         errors="ignore"))), text)
        body = md.convert(text)
        sec = 0
        chap_num = [str(ci)]
        # Number chapter (h1) and section (h2) headings, and collect TOC entries.
        def number(m):
            nonlocal sec
            tag, attrs, inner = m.group(1), m.group(2), m.group(3)
            hid = re.search(r'id="([^"]+)"', attrs)
            hid = hid.group(1) if hid else ""
            title = _slug_num(inner)
            if tag == "h1":
                app = re.match(r"Appendix ([A-Z]): (.*)", title)
                if app:
                    chap_num[0] = app.group(1)
                    toc.append({"level": 1, "num": app.group(1), "title": app.group(2), "id": hid,
                                "label": f"Appendix {app.group(1)}"})
                    inner2 = re.sub(r"Appendix [A-Z]: ", "", inner, count=1)
                    return f'<h1{attrs}><span class="num">Appendix {app.group(1)} </span>{inner2}</h1>'
                chap_num[0] = str(ci)
                toc.append({"level": 1, "num": f"{ci}", "title": title, "id": hid,
                            "label": f"Chapter {ci}"})
                return f'<h1{attrs}><span class="num">Chapter {ci} </span>{inner}</h1>'
            sec += 1
            toc.append({"level": 2, "num": f"{chap_num[0]}.{sec}", "title": title, "id": hid,
                        "label": f"{chap_num[0]}.{sec}"})
            return f'<h2{attrs}><span class="num">{chap_num[0]}.{sec} </span>{inner}</h2>'
        body = re.sub(r"<(h1|h2)([^>]*)>(.*?)</\1>", number, body, flags=re.S)
        parts.append(f'<section class="chapter">{body}</section>')

    rows = []
    for e in toc:
        pg = (page_map or {}).get(e["id"], "")
        cls = "ch" if e["level"] == 1 else "sec"
        label = (f'<span class="n">{e["num"]}</span>{html.escape(e["title"])}')
        rows.append(f'<li class="{cls}"><a href="#{e["id"]}" class="row"><span class="label">{label}</span>'
                    f'<span class="dots"></span><span class="pg">{pg}</span></a></li>')
    toc_html = f'<section class="toc"><h1 id="contents">Contents</h1><ol>{"".join(rows)}</ol></section>'
    pyg = HtmlFormatter(style="friendly").get_style_defs(".hl")
    doc = (f'<!doctype html><html><head><meta charset="utf-8"><title>{DS["title"]}</title>'
           f'<style>{CSS}\n{pyg}\n.hl {{ background: transparent; }}</style></head>'
           f'<body>{toc_html}{"".join(parts)}</body></html>')
    return doc, toc


def build_cover(stats: dict) -> str:
    today = dt.date.today().strftime("%d %B %Y")
    boxes = DS["stats"] or [("tracked files", str(stats["files"])),
                            ("lines of code", f"{stats['lines']:,}"),
                            ("automated tests", str(stats["test_cases"])),
                            ("defect classes", "2")]
    stat_html = "".join(f'<div class="stat"><div class="k">{k}</div><div class="v">{v}</div></div>'
                        for k, v in boxes)
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{COVER_CSS}</style></head><body>
<div class="cover"><div class="grid"></div><div class="glow"></div>
<div class="inner">
  <div class="tag"><span class="dot"></span>{DS["tag"]}</div>
  <h1>VANTA</h1>
  <p class="expand">Virtualized Adversarial Network &amp; Technical Assessment</p>
  <p class="motto">{DS["motto"]}</p>
  <p class="what">{DS["what"]}</p>
</div>
<div class="stats">{stat_html}</div>
<div class="foot"><span>VANTA project · {DS["footer"].split(" · ")[1]}</span><span>{today}</span></div>
</div></body></html>"""


def render(html_path: Path, pdf_path: Path, footer: bool) -> None:
    subprocess.run(["node", str(RENDER), str(html_path), str(pdf_path), "1" if footer else "0",
                    DS["footer"]], check=True)


def outline_pages(pdf_path: Path, toc: list[dict]) -> dict[str, int]:
    """Map heading ids to page numbers using the PDF outline Chromium wrote."""
    reader = PdfReader(str(pdf_path))
    flat = []

    def walk(items):
        for it in items:
            if isinstance(it, list):
                walk(it)
            else:
                flat.append((_slug_num(it.title), reader.get_destination_page_number(it) + 1))
    walk(reader.outline)
    pages: dict[str, int] = {}
    cursor = 0
    for e in toc:
        want = e["label"]
        for j in range(cursor, len(flat)):
            t = flat[j][0].lower()
            if t.startswith(want.lower()) and e["title"][:20].lower() in t:
                pages[e["id"]] = flat[j][1]
                cursor = j + 1
                break
    return pages


def main() -> None:
    global DS
    name = sys.argv[1] if len(sys.argv) > 1 else "technical"
    DS = DOCSETS[name]
    BUILD = DOCS / "build" / name
    OUT = DS["out"]
    BUILD.mkdir(parents=True, exist_ok=True)
    stats = repo_stats() if DS["stats"] is None else {}
    (BUILD / "cover.html").write_text(build_cover(stats), encoding="utf-8")
    render(BUILD / "cover.html", BUILD / "cover.pdf", footer=False)

    doc, toc = build_body(None)
    (BUILD / "body.html").write_text(doc, encoding="utf-8")
    render(BUILD / "body.html", BUILD / "body_pass1.pdf", footer=True)
    pages = outline_pages(BUILD / "body_pass1.pdf", toc)
    missing = [e["title"] for e in toc if e["id"] not in pages]
    if missing:
        print("warning: no page found for", missing[:10], file=sys.stderr)

    doc, _ = build_body(pages)
    (BUILD / "body.html").write_text(doc, encoding="utf-8")
    render(BUILD / "body.html", BUILD / "body.pdf", footer=True)
    check = outline_pages(BUILD / "body.pdf", toc)
    if check != pages:
        print("warning: page numbers shifted between passes", file=sys.stderr)

    writer = PdfWriter()
    for p in PdfReader(str(BUILD / "cover.pdf")).pages:
        writer.add_page(p)
    body = PdfReader(str(BUILD / "body.pdf"))
    for p in body.pages:
        writer.add_page(p)
    # Rebuild bookmarks (offset by the cover page) so the PDF sidebar works.
    parents: dict[str, object] = {}
    last_ch = None
    for e in toc:
        if e["id"] not in pages:
            continue
        page_index = pages[e["id"]]  # cover is 1 page, body page n -> index n
        title = (f"{e['num']}. {e['title']}" if e["level"] == 1 else f"{e['num']} {e['title']}")
        if e["level"] == 1:
            last_ch = writer.add_outline_item(title, page_index)
        else:
            writer.add_outline_item(title, page_index, parent=last_ch)
    writer.add_metadata({"/Title": DS["title"], "/Subject": DS["subject"],
                         "/Creator": "docs/build_docs.py"})
    with open(OUT, "wb") as f:
        writer.write(f)
    print(json.dumps({"pdf": str(OUT), "pages": len(writer.pages), "toc_entries": len(toc),
                      "stats": stats}))


if __name__ == "__main__":
    main()
