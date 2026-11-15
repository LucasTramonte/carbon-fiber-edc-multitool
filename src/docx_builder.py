"""Formatting helpers that apply the course rules to python-docx.

Norms: Times New Roman 12, 1.5 line spacing, justified body text. Tables,
captions and references use a smaller single-spaced font (the norms do not
address them). Figures and tables are numbered in the body (``Figura 3``) and
in appendices (``Figura A.2``).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

try:
    from src.omml import math_element, math_paragraph_element, n as math_text
except ImportError:  # pragma: no cover
    from omml import math_element, math_paragraph_element, n as math_text

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "outputs" / "visualizations"
TEAM_LOCAL = ROOT / "report" / "team.local.json"
TEAM_EXAMPLE = ROOT / "report" / "team.example.json"
LOGO_LOCAL = ROOT / "report" / "local_assets" / "fca_logo.png"


def br(value: float, digits: int = 0) -> str:
    """Format a number in Brazilian Portuguese (dot thousands, comma decimals)."""
    text = f"{value:,.{digits}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def brl(value: float, digits: int = 2) -> str:
    return f"R$ {br(value, digits)}"


def pct(value: float, digits: int = 0) -> str:
    return f"{br(value * 100, digits)}%"


NBSP = "\u00a0"
NB_HYPHEN = "\u2011"
SHORT_PHRASE_CM = 5.0  # clauses up to this width stay on one line when the table allows it
_CLAUSE_END = re.compile(r"(?<=[,;:.!?]) +")  # ordinary spaces only: NBSP must stay bound
CELL_PADDING_CM = 0.45  # default cell margins (2 x 0.19 cm) plus a safety margin
MIN_TABLE_FONT = 6.0

_FONT_FILES = {
    False: ("C:/Windows/Fonts/times.ttf", "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
            "C:/Windows/Fonts/LiberationSerif-Regular.ttf"),
    True: ("C:/Windows/Fonts/timesbd.ttf", "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
           "C:/Windows/Fonts/LiberationSerif-Bold.ttf"),
}
_font_cache: dict = {}


def text_width_cm(text: str, font_pt: float, bold: bool = True) -> float:
    """Width of one line of text in Times New Roman (or its metric twin Liberation Serif)."""
    if bold not in _font_cache:
        _font_cache[bold] = None
        for path in _FONT_FILES[bold]:
            if Path(path).exists():
                try:
                    from PIL import ImageFont

                    _font_cache[bold] = ImageFont.truetype(path, 200)
                    break
                except Exception:  # pragma: no cover - fall back to the estimate below
                    pass
    text = text.replace(NB_HYPHEN, "-").replace(NBSP, " ")
    face = _font_cache[bold]
    if face is None:
        return len(text) * 0.52 * font_pt / 28.35
    return face.getlength(text) / 200 * font_pt / 28.35


def longest_word_cm(texts: list[str], font_pt: float) -> float:
    """Width of the widest single word among the texts (words never break inside a cell)."""
    words = [w for text in texts for line in text.split("\n") for w in line.replace(NBSP, " ").split()]
    return max((text_width_cm(w, font_pt) for w in words), default=0.0)


def fit_columns(headers: list[str], rows: list[list[str]], widths: list[float], font: float):
    """Per-column font sizes (and, if needed, widths) so no word is split across lines.

    Each column's font shrinks from the table font down to MIN_TABLE_FONT until its widest
    word fits. If even the minimum does not fit, width is taken from the column with the most
    spare room.
    """
    n = len(widths)
    widths = list(widths)
    columns = [[headers[i]] + [row[i] for row in rows] for i in range(n)]

    def fitting_font(i: int):
        f = font
        while f >= MIN_TABLE_FONT - 1e-9:
            if longest_word_cm(columns[i], f) + CELL_PADDING_CM <= widths[i]:
                return f
            f -= 0.25
        return None

    # First borrow width from roomier columns so the font can stay at 8 pt or more;
    # then, only if still needed, let the font shrink down to MIN_TABLE_FONT.
    for target in (min(font, 8.0), MIN_TABLE_FONT):
        for i in range(n):
            guard = 0
            while longest_word_cm(columns[i], target) + CELL_PADDING_CM > widths[i] + 1e-9 and guard < 40:
                guard += 1
                need = longest_word_cm(columns[i], target) + CELL_PADDING_CM
                slack = [(widths[j] - longest_word_cm(columns[j], target) - CELL_PADDING_CM - 0.3, j)
                         for j in range(n) if j != i]
                room, donor = max(slack)
                if room <= 0.05:
                    break
                move = min(need - widths[i] + 0.02, room)
                widths[i] += move
                widths[donor] -= move
    fonts = [f if f is not None else MIN_TABLE_FONT for f in (fitting_font(i) for i in range(n))]

    def phrase_need(i: int) -> float:
        """Width needed to keep every short body clause of column i on one line."""
        clauses = [part for text in columns[i][1:] for line in text.split("\n") for part in _CLAUSE_END.split(line)]
        short = [w for w in (text_width_cm(c, fonts[i]) for c in clauses) if w <= SHORT_PHRASE_CM]
        return max(short, default=0.0) + CELL_PADDING_CM

    original = list(widths)  # a donor never gives up more than 12% of its width: long text must keep room
    for i in range(n):
        guard = 0
        while phrase_need(i) > widths[i] + 1e-9 and guard < 40:
            guard += 1
            slack = [(min(widths[j] - max(phrase_need(j), longest_word_cm(columns[j], fonts[j]) + CELL_PADDING_CM) - 0.1,
                          widths[j] - 0.88 * original[j]), j)
                     for j in range(n) if j != i]
            room, donor = max(slack)
            if room <= 0.05:
                break
            move = min(phrase_need(i) - widths[i] + 0.02, room)
            widths[i] += move
            widths[donor] -= move
    return fonts, widths


_NUMBER_UNIT = re.compile(r"(?<=\d) (?=(?:g|kg|mm|cm|m|min|h|dias|semanas|meses|mil|unidades|cartões)\b)")
_LABEL_NUMBER = re.compile(r"\b(Lei|art\.|arts\.|R\$|US\$|€|Seção|Tabela|Figura|Apêndice) (?=\d)")


def bind_numbers(text: str) -> str:
    """Never break between a number and its unit, nor between 'art.', 'R$', 'Lei' and the number."""
    text = _NUMBER_UNIT.sub(NBSP, text).replace(" × ", NBSP + "×" + NBSP)
    return _LABEL_NUMBER.sub(lambda m: m.group(1) + NBSP, text)


def keep_phrases(text: str, width_cm: float, font: float) -> str:
    """Bind words with non-breaking spaces so lines wrap only after punctuation.

    A clause is bound only when it fits the cell on one line (measured with the real font
    metrics); longer clauses keep ordinary spaces so they can still wrap between words.
    """
    usable_cm = width_cm - CELL_PADDING_CM
    out_lines = []
    for line in text.split("\n"):
        parts = _CLAUSE_END.split(line)
        rebuilt = " ".join(part.replace(" ", NBSP) if text_width_cm(part, font) <= usable_cm else part
                           for part in parts)
        out_lines.append(rebuilt)
    return "\n".join(out_lines)


def load_team() -> dict:
    """Team data: the private local file when present, otherwise the placeholder example."""
    path = TEAM_LOCAL if TEAM_LOCAL.exists() else TEAM_EXAMPLE
    return json.loads(path.read_text(encoding="utf-8"))


class Builder:
    """Small helper that applies the course formatting rules."""

    def __init__(self) -> None:
        self.doc = Document()
        section = self.doc.sections[0]
        section.page_height, section.page_width = Cm(29.7), Cm(21.0)
        section.top_margin, section.left_margin = Cm(3), Cm(3)
        section.bottom_margin, section.right_margin = Cm(2), Cm(2)
        normal = self.doc.styles["Normal"]
        normal.font.name = "Times New Roman"
        normal.font.size = Pt(12)
        normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
        fmt = normal.paragraph_format
        fmt.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        fmt.space_after = Pt(4)
        fmt.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        for style_name in ("List Bullet",):
            style = self.doc.styles[style_name]
            style.font.name = "Times New Roman"
            style.font.size = Pt(12)
        self._footer_page_number(section)
        self.fig_no = 0
        self.tab_no = 0
        self.eq_no = 0
        self.table_log: list = []  # (table number, headers, per-column fonts), for tests
        self.prefix = ""  # "" in the body, "A." / "B." ... inside appendices

    # ------------------------------------------------------------- structure
    @staticmethod
    def _footer_page_number(section) -> None:
        paragraph = section.footer.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = paragraph.add_run()
        for kind, text in (("begin", None), (None, "PAGE"), ("end", None)):
            if kind:
                el = OxmlElement("w:fldChar")
                el.set(qn("w:fldCharType"), kind)
            else:
                el = OxmlElement("w:instrText")
                el.set(qn("xml:space"), "preserve")
                el.text = text
            run._r.append(el)
        run.font.name = "Times New Roman"
        run.font.size = Pt(10)

    def page_break(self) -> None:
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def heading(self, text: str, level: int = 1, new_page: bool = False) -> None:
        paragraph = self.doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
        paragraph.paragraph_format.keep_with_next = True
        paragraph.paragraph_format.page_break_before = new_page
        paragraph.paragraph_format.space_before = Pt(10 if level == 1 else 6)
        paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        run = paragraph.add_run(text)
        run.bold = True
        run.font.size = Pt(13 if level == 1 else 12)
        run.italic = level == 3

    def appendix(self, letter: str, title: str) -> None:
        """Start an appendix on a new page and restart figure/table counters."""
        self.prefix = f"{letter}."
        self.fig_no = 0
        self.tab_no = 0
        self.heading(f"Apêndice {letter}: {title}", 1, new_page=True)

    # ------------------------------------------------------------------ text
    def para(self, text: str, bold_lead: str | None = None) -> None:
        paragraph = self.doc.add_paragraph()
        if bold_lead:
            paragraph.add_run(bold_lead).bold = True
        paragraph.add_run(text)

    def bullet(self, text: str, bold_lead: str | None = None) -> None:
        paragraph = self.doc.add_paragraph(style="List Bullet")
        paragraph.paragraph_format.space_after = Pt(2)
        if bold_lead:
            paragraph.add_run(bold_lead).bold = True
        paragraph.add_run(text)

    def small(self, text: str, size: float = 10, left: bool = False, italic: bool = False) -> None:
        paragraph = self.doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT if left else WD_ALIGN_PARAGRAPH.JUSTIFY
        paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        paragraph.paragraph_format.space_after = Pt(6)
        run = paragraph.add_run(text)
        run.font.size = Pt(size)
        run.italic = italic

    # --------------------------------------------------------------- figures
    def figure(self, filename: str, caption: str, width_cm: float = 14.0, source: str = "") -> None:
        self.fig_no += 1
        paragraph = self.doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.keep_with_next = True
        paragraph.paragraph_format.keep_together = True
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        paragraph.add_run().add_picture(str(FIGURES / filename), width=Cm(width_cm))
        text = f"Figura {self.prefix}{self.fig_no}: {caption}"
        if source:
            text += f" Fonte: {source}"
        self.small(text, 10)

    # ---------------------------------------------------------------- tables
    def table(self, title: str, headers: list[str], rows: list[list[str]], widths_cm: list[float],
              source: str = "", font: float = 9.5, bold_rows: tuple[int, ...] = (),
              right_cols: tuple[int, ...] = ()) -> None:
        self.tab_no += 1
        caption = self.doc.add_paragraph()
        caption.alignment = WD_ALIGN_PARAGRAPH.LEFT
        caption.paragraph_format.keep_with_next = True
        caption.paragraph_format.space_after = Pt(2)
        caption.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        run = caption.add_run(f"Tabela {self.prefix}{self.tab_no}: {title}")
        run.bold = True
        run.font.size = Pt(10)
        table = self.doc.add_table(rows=1, cols=len(headers))
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        layout = OxmlElement("w:tblLayout")
        layout.set(qn("w:type"), "fixed")
        table._tbl.tblPr.append(layout)
        col_fonts, widths_cm = fit_columns(headers, rows, widths_cm, font)
        self.table_log.append((f"{self.prefix}{self.tab_no}", headers, col_fonts))
        for i, width in enumerate(widths_cm):
            table.columns[i].width = Cm(width)
        for i, header in enumerate(headers):
            self._cell(table.rows[0].cells[i], header, widths_cm[i], col_fonts[i], bold=True, shade="D9D9D9")
        self._repeat_header(table.rows[0])
        for r, row in enumerate(rows):
            cells = table.add_row().cells
            for i, value in enumerate(row):
                self._cell(cells[i], value, widths_cm[i], col_fonts[i], bold=r in bold_rows,
                           shade="F2F2F2" if r in bold_rows else "", right=i in right_cols)
            self._no_split(table.rows[-1])
        # a header must never be left alone at the bottom of a page: keep it with the first data row
        keep_rows = table.rows[:1]
        for row in keep_rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.keep_with_next = True
        if source:
            self.small(f"Fonte: {source}", 9.5)
        else:
            self.small("", 4)

    def equation(self, fragment: str) -> None:
        """Numbered display equation: a borderless row with the equation centred and its number at the right."""
        self.eq_no += 1
        table = self.doc.add_table(rows=1, cols=3)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        layout = OxmlElement("w:tblLayout")
        layout.set(qn("w:type"), "fixed")
        table._tbl.tblPr.append(layout)
        for cell, width in zip(table.rows[0].cells, (1.0, 13.6, 1.4)):
            cell.width = Cm(width)
            vertical = OxmlElement("w:vAlign")
            vertical.set(qn("w:val"), "center")
            cell._tc.get_or_add_tcPr().append(vertical)
        for column, width in zip(table.columns, (1.0, 13.6, 1.4)):
            column.width = Cm(width)
        middle = table.rows[0].cells[1].paragraphs[0]
        middle.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        middle.paragraph_format.space_after = Pt(0)
        middle._p.append(math_paragraph_element(fragment))
        number = table.rows[0].cells[2].paragraphs[0]
        number.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        number.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        number.paragraph_format.space_after = Pt(0)
        number.add_run(f"({self.eq_no})").font.size = Pt(12)
        self._no_split(table.rows[0])

    def math_para(self, parts: list) -> None:
        """Body paragraph mixing text (str) with inline math (a one-item tuple holding an OMML fragment)."""
        paragraph = self.doc.add_paragraph()
        for part in parts:
            if isinstance(part, tuple):
                paragraph._p.append(math_element(part[0]))
            else:
                paragraph.add_run(part)

    SWOT_STYLE = {
        "FORÇAS": ("Forças (interno, positivo)", "E1EDFA", "1F5FAA"),
        "FRAQUEZAS": ("Fraquezas (interno, negativo)", "FBEEE0", "A8501A"),
        "OPORTUNIDADES": ("Oportunidades (externo, positivo)", "E3F2E4", "1B7032"),
        "AMEAÇAS": ("Ameaças (externo, negativo)", "F9E6E6", "A02E2E"),
    }

    def swot_matrix(self, caption: str, quadrants: dict[str, tuple[str, ...]], source: str = "") -> None:
        """SWOT as a shaded 2 x 2 table, numbered and captioned as a figure."""
        self.fig_no += 1
        table = self.doc.add_table(rows=2, cols=2)
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        layout = OxmlElement("w:tblLayout")
        layout.set(qn("w:type"), "fixed")
        table._tbl.tblPr.append(layout)
        for column in table.columns:
            column.width = Cm(8.0)
        for index, name in enumerate(("FORÇAS", "FRAQUEZAS", "OPORTUNIDADES", "AMEAÇAS")):
            label, fill, ink = self.SWOT_STYLE[name]
            cell = table.cell(index // 2, index % 2)
            cell.width = Cm(8.0)
            props = cell._tc.get_or_add_tcPr()
            shade = OxmlElement("w:shd")
            shade.set(qn("w:val"), "clear")
            shade.set(qn("w:fill"), fill)
            props.append(shade)
            head = cell.paragraphs[0]
            head.alignment = WD_ALIGN_PARAGRAPH.LEFT
            head.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
            head.paragraph_format.space_after = Pt(3)
            run = head.add_run(label)
            run.bold = True
            run.font.size = Pt(10)
            run.font.color.rgb = RGBColor.from_string(ink)
            for item in quadrants[name]:
                line = cell.add_paragraph()
                line.alignment = WD_ALIGN_PARAGRAPH.LEFT
                line.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
                line.paragraph_format.space_after = Pt(2)
                line.paragraph_format.left_indent = Cm(0.4)
                line.paragraph_format.first_line_indent = Cm(-0.4)
                bullet = line.add_run("•\u00a0\u00a0" + item)
                bullet.font.size = Pt(9)
            if index % 2 == 0:
                self._no_split(table.rows[index // 2])
        text = f"Figura {self.prefix}{self.fig_no}: {caption}"
        if source:
            text += f" Fonte: {source}"
        self.small(text, 10)

    @staticmethod
    def _repeat_header(row) -> None:
        props = row._tr.get_or_add_trPr()
        el = OxmlElement("w:tblHeader")
        el.set(qn("w:val"), "true")
        props.append(el)

    @staticmethod
    def _no_split(row) -> None:
        props = row._tr.get_or_add_trPr()
        el = OxmlElement("w:cantSplit")
        el.set(qn("w:val"), "true")
        props.append(el)

    @staticmethod
    def _cell(cell, text: str, width_cm: float, font: float, bold: bool = False, shade: str = "",
              right: bool = False) -> None:
        cell.width = Cm(width_cm)
        paragraph = cell.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT if right else WD_ALIGN_PARAGRAPH.LEFT
        paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        paragraph.paragraph_format.space_after = Pt(1)
        text = bind_numbers(re.sub(r"(?<=\w)-(?=\w)", NB_HYPHEN, text))
        run = paragraph.add_run(keep_phrases(text, width_cm, font))
        run.font.size = Pt(font)
        run.bold = bold
        if shade:
            props = cell._tc.get_or_add_tcPr()
            fill = OxmlElement("w:shd")
            fill.set(qn("w:val"), "clear")
            fill.set(qn("w:fill"), shade)
            props.append(fill)

    # ----------------------------------------------------------------- cover
    def cover(self, title: str, subtitle: str, team: dict) -> None:
        def centered(text: str, size: float = 12, bold: bool = False, italic: bool = False,
                     space_after: float = 6) -> None:
            paragraph = self.doc.add_paragraph()
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
            paragraph.paragraph_format.space_after = Pt(space_after)
            run = paragraph.add_run(text)
            run.bold, run.italic, run.font.size = bold, italic, Pt(size)

        if LOGO_LOCAL.exists():
            paragraph = self.doc.add_paragraph()
            paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
            paragraph.add_run().add_picture(str(LOGO_LOCAL), width=Cm(4.2))
        for line in team["institution"]:
            centered(line, 12, bold=True, space_after=2)
        centered("", space_after=60)
        centered(title, 15, bold=True, space_after=10)
        centered(subtitle, 12, italic=True, space_after=70)
        for label, key in (("Disciplina: ", "course"), ("Grupo: ", "group"), ("Data de entrega: ", "due_date")):
            paragraph = self.doc.add_paragraph()
            paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
            paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
            paragraph.add_run(label).bold = True
            paragraph.add_run(str(team[key]))
        centered("", space_after=40)
        paragraph = self.doc.add_paragraph()
        paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
        paragraph.add_run("Discentes:").bold = True
        for member in team["members"]:
            paragraph = self.doc.add_paragraph()
            paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
            paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
            paragraph.paragraph_format.space_after = Pt(1)
            paragraph.paragraph_format.tab_stops.add_tab_stop(Cm(11), WD_TAB_ALIGNMENT.LEFT)
            paragraph.add_run(f"{member['name']}\tRA: {member['ra']}")
        centered("", space_after=60)
        centered(team["city"], 12, space_after=0)
        centered(str(team["year"]), 12)
        self.page_break()
