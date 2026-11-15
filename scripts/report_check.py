"""Check the layout of the report PDF the way a reader sees it.

Tests prove the structure of the .docx; they cannot see page breaks, empty gaps, tiny text or a header
alone at the bottom of a page. This script reads the PDF and prints what changed pages look like:

    python scripts/report_check.py                      # summary: pages, where each part starts, gaps, dashes
    python scripts/report_check.py --png "Tabela 9" "Figura 5"   # also render the pages holding these captions

Needs PyMuPDF (``pip install pymupdf``); it is not a project requirement because only this check uses it.
Pages are rendered to the folder given by ``--out`` (default: the system temp folder) for visual inspection.
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = ROOT / "assets" / "relatorio_completo_cartao_multitool.docx.pdf"
FOOTER_Y = 790  # text below this line is the page number
HEADER_Y = 60
PAGE_BOTTOM = 785
GAP_PT = 90  # an empty band taller than this is worth a look
PARTS = ("Resumo", "1. ", "2. ", "3. ", "4. ", "5. ", "6. ", "7. Conclus", "Referências", "Apêndice A:", "Apêndice B:")
DASHES = ("—", "–")


def load(path: Path):
    try:
        import pymupdf
    except ImportError:  # pragma: no cover
        sys.exit("PyMuPDF is required: pip install pymupdf")
    return pymupdf.open(path)


def content_bottom(page) -> float:
    blocks = [b for b in page.get_text("blocks") if b[3] < FOOTER_Y and b[1] > HEADER_Y]
    images = [page.get_image_bbox(x) for x in page.get_images(full=True)]
    return max([b[3] for b in blocks] + [r.y1 for r in images] or [0])


def first_text(page) -> str:
    blocks = [b for b in page.get_text("blocks") if b[1] > HEADER_Y and b[4].strip()]
    return blocks[0][4].strip().replace("\n", " ")[:60] if blocks else ""


def summary(doc) -> dict:
    starts: dict[str, int] = {}
    for number, page in enumerate(doc, start=1):
        for line in page.get_text().splitlines():
            line = line.strip()
            for part in PARTS:
                if line.startswith(part) and part not in starts and len(line) < 70:
                    starts[part] = number
    gaps = []
    for number in range(2, len(doc)):  # skip the cover; the last page is allowed to be short
        free = PAGE_BOTTOM - content_bottom(doc[number - 1])
        if free > GAP_PT and number < len(doc):
            gaps.append((number, round(free), first_text(doc[number])))
    text = "".join(page.get_text() for page in doc)
    return {"pages": len(doc), "starts": starts, "gaps": gaps, "dashes": sum(text.count(d) for d in DASHES),
            "unresolved": len(re.findall(r"(Tabela|Figura|Seção|Seções) \?", text))}


def render(doc, captions: list[str], out: Path) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for caption in captions:
        for number, page in enumerate(doc, start=1):
            if re.search(rf"^{re.escape(caption)}:", page.get_text(), flags=re.M):
                target = out / f"report_page_{number}.png"
                page.get_pixmap(dpi=80).save(target)
                written.append(target)
                break
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--png", nargs="*", default=[], metavar="CAPTION", help="render the page of each caption")
    parser.add_argument("--out", type=Path, default=Path(tempfile.gettempdir()) / "report_check")
    args = parser.parse_args()
    doc = load(args.pdf)
    info = summary(doc)
    print(f"pages: {info['pages']}")
    for part, page in info["starts"].items():
        print(f"  {part.strip():<14} starts on page {page}")
    body_start, body_end = info["starts"].get("Resumo", 2), info["starts"].get("7. Conclus", 0)
    if body_end:
        print(f"body: pages {body_start} to {body_end} (the conclusion ends partway through the last one)")
    print(f"empty bands over {GAP_PT} pt: {len(info['gaps'])}")
    for number, free, following in info["gaps"]:
        print(f"  page {number}: {free} pt free; next page starts with: {following}")
    print(f"dashes (em or en): {info['dashes']}; unresolved references: {info['unresolved']}")
    for path in render(doc, args.png, args.out):
        print("rendered", path)
    return 1 if info["dashes"] or info["unresolved"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
