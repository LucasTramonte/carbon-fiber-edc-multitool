"""English edition of the project report, a condensed version of the Portuguese course report.

Written directly in English from the same models (project plan, economics, reverse logistics, strategic analysis),
so every number agrees with the Portuguese report. It carries no personal data and no course material: it is the
document linked at the top of the README. Build it with ``scripts/build_report_pdf.ps1 -Edition en``.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

try:
    from src import project_plan as pp
    from src import report_diagrams, reverse_flow_diagram, strategic_analysis
    from src import report_equations as eq
    from src import reverse_logistics_model as rl
    from src import strategic_analysis as sa
    from src.docx_builder import Builder
    from src.generate_report_docx import CRITERIA, SCORES, concept_scores, concept_winner_range
except ImportError:  # pragma: no cover
    import project_plan as pp
    import report_diagrams
    import report_equations as eq
    import reverse_flow_diagram
    import reverse_logistics_model as rl
    import strategic_analysis
    import strategic_analysis as sa
    from docx_builder import Builder
    from generate_report_docx import CRITERIA, SCORES, concept_scores, concept_winner_range

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DOCX = ROOT / "outputs" / "report_en.docx"
PDF_DIR = ROOT / "docs" / "report"
PDF_NAME = "carbon-fiber-edc-multitool-report-en.pdf"
HASH_FILE = PDF_DIR / "report-en.sha256"

LABEL_MAP = {
    "tables": {
        "Competitors": "competitors", "Product scope": "scope", "Morphological matrix": "morph",
        "Macro process plan": "macro", "Activities": "activities", "Economic viability": "viability_table",
    },
    "figures": {
        "product_structure_en.png": "structure", "viability_chart_en.png": "viability_chart",
        "reverse_flow_en.png": "eol_flow", "gantt_en.png": "gantt",
    },
    "headings": {},
}

CRITERIA_EN = {"Segurança": "Safety", "Utilidade": "Utility", "Fabricabilidade": "Manufacturability",
               "Custo": "Cost", "Massa e espessura": "Mass and thickness"}

# every source the English text can cite, in the form used in the reference list
SOURCES = {
    "ibge_pop": "IBGE. SIDRA, table 6579: resident population estimated by state, 2024. "
                "https://apisidra.ibge.gov.br/desctabapi.aspx?c=6579. Accessed 3 Nov 2026.",
    "ibge_income": "IBGE. SIDRA, table 7531: real average monthly household income per capita, 2024. "
                   "https://apisidra.ibge.gov.br/desctabapi.aspx?c=7531. Accessed 3 Nov 2026.",
    "cyclist": "TRANSPORTE ATIVO. Pesquisa Nacional Perfil do Ciclista 2024. https://ta.org.br/perfil/perfil24.pdf. "
               "Accessed 3 Nov 2026.",
    "law12305": "BRASIL. Law No. 12,305 of 2 August 2010 (National Solid Waste Policy). "
                "https://www.planalto.gov.br/ccivil_03/_ato2007-2010/2010/lei/l12305.htm. Accessed 10 Nov 2026.",
    "cdc": "BRASIL. Law No. 8,078 of 11 September 1990 (Consumer Defence Code), arts. 26 and 49. "
           "https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm. Accessed 10 Nov 2026.",
    "correios": "CORREIOS. Domestic parcels and price simulator. https://www.correios.com.br/enviar/encomendas/nacional. "
                "Accessed 10 Nov 2026.",
    "recaltech": "RECALTECH. Carbon fibre recycling. https://www.recaltech.com.br/reciclagem-de-fibra-de-carbono. "
                 "Accessed 10 Nov 2026.",
    "harden": "HARDEN, C. W.; PEDERSEN, T.; JENSEN, P. D. O. Motivation or inconvenience: what matters most? "
              "Understanding recycling behavior of healthcare waste. Cleaner and Responsible Consumption, v. 15, "
              "100240, 2024. https://doi.org/10.1016/j.clrc.2024.100240. Accessed 10 Nov 2026.",
    "leatherman_warranty": "LEATHERMAN. Built to last: the Leatherman warranty promise. "
                           "https://uk.leatherman.com/blogs/news/built-to-last-the-leatherman-warranty-promise. "
                           "Accessed 10 Nov 2026.",
    "victorinox_warranty": "VICTORINOX. Victorinox two-year warranty. "
                           "https://www.victorinox.com/en-DE/cms/victorinox-two-year-warranty/. Accessed 10 Nov 2026.",
    "toolstoday": "TOOLSTODAY. Cutting carbon fiber on a CNC: tips, safety and bit selection, 13 Oct 2025. "
                  "https://global.toolstoday.com/learn/cutting-carbon-fiber-on-a-cnc-tips-safety-bit-selection. "
                  "Accessed 11 Nov 2026.",
    "cncstep": "CNC-STEP. Milling, drilling and cutting carbon fiber sheets. "
               "https://www.cnc-step.com/milling-drilling-cutting-carbon-fiber-sheets/. Accessed 11 Nov 2026.",
    "walletninja": "WALLET NINJA. Product page. https://walletninja.com/. Accessed 11 Nov 2026.",
    "micra": "LEATHERMAN. Micra. https://www.leatherman.com/collections/bestsellers/products/micra. "
             "Accessed 11 Nov 2026.",
    "laser": "MICROMACHINES. A review of research progress on machining carbon fiber-reinforced composites with "
             "lasers. v. 14, n. 1, art. 24, 2023. https://www.mdpi.com/2072-666X/14/1/24. Accessed 15 Nov 2026.",
    "tog09": "OSO GRANDE KNIVES. Touch of Ginger Carbon Fiber Credit Card Spanner Tool (TOG09). "
             "https://www.osograndeknives.com/catalog/credit-card-sized-tools/touch-of-ginger-carbon-fiber-credit-"
             "card-spanner-tool-knife-wrench-wallet-size-3.375x2.125-tog09-31316.html. Accessed 15 Nov 2026.",
    "us5328026": "NEWMAN, C. M. Flat multiple tool holder. US 5,328,026, filed 11 June 1993. "
                 "https://patents.google.com/patent/US5328026. Accessed 15 Nov 2026.",
    "ca175697": "NITE IZE. Card-shaped multi-tool (design). CA 175697, filed 29 June 2017. "
                "https://patents.google.com/patent/CA175697S/en. Accessed 15 Nov 2026.",
    "us8713735": "PELTON, R. Y. Compact survival tool. US 8,713,735, filed 6 December 2011. "
                 "https://patents.google.com/patent/US8713735. Accessed 15 Nov 2026.",
    "cochran": "COCHRAN, W. G. Sampling techniques. 3rd ed. New York: Wiley, 1977.",
    "vanwestendorp": "VAN WESTENDORP, P. NSS Price Sensitivity Meter (PSM): a new approach to study consumer "
                     "perception of prices. In: ESOMAR Congress, 29th, Venice, 1976. p. 139-167.",
    "bcb": "BANCO CENTRAL DO BRASIL. Time Series Management System, series 432: Selic target rate. "
           "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json. Accessed 15 Nov 2026.",
    "sherpa": "EMBREY, D. E. SHERPA: a systematic human error reduction and prediction approach. In: International "
              "Topical Meeting on Advances in Nuclear Power Systems, Knoxville, 1986.",
    "reason": "REASON, J. Human error. Cambridge: Cambridge University Press, 1990.",
}


class Citations:
    """Numbers sources in the order they are first cited and keeps the list for the reference section."""

    def __init__(self) -> None:
        self.order: list[str] = []

    def __call__(self, *keys: str) -> str:
        out = ""
        for key in keys:
            if key not in SOURCES:
                raise KeyError(key)
            if key not in self.order:
                self.order.append(key)
            out += f"[{self.order.index(key) + 1}]"
        return out


def n0(value: float) -> str:
    return f"{value:,.0f}"


def n1(value: float) -> str:
    return f"{value:,.1f}"


def n2(value: float) -> str:
    return f"{value:,.2f}"


def reais(value: float, digits: int = 0) -> str:
    return f"R$ {value:,.{digits}f}"


def share(value: float, digits: int = 0) -> str:
    return f"{value * 100:,.{digits}f}%"


def report_text_hash(document) -> str:
    """Hash of the report text (non-breaking characters normalised), to detect a PDF that lags the code."""
    from docx.oxml.ns import qn

    paragraphs = ["".join(t.text or "" for t in el.iter(qn("w:t"))) for el in document.element.body.iter(qn("w:p"))]
    text = "\n".join(paragraphs).replace(" ", " ").replace("‑", "-")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_report() -> Builder:
    """Two passes: the first numbers tables and figures, the second writes the text citing those numbers."""
    first = _build({})
    return _build(first.labels)


def _build(labels: dict[str, str]) -> Builder:
    def R(key: str) -> str:
        return labels.get(key, "?")

    cite = Citations()
    p = rl.load_assumptions()
    sched, costs = pp.schedule(), pp.cost_table()
    phase = rl.build_schedule(p)
    ccost, flows, channels = rl.return_cost_table(p), rl.mass_flows(p), rl.channel_cost_table(p)
    reman = rl.remanufacturing_viability(p)
    ref = p["return_rate_ref"]
    voucher = ccost[(ccost["option"] == "frete_gratis_voucher") & (ccost["return_rate"] == ref)].iloc[0]
    store = channels[(channels["channel"] == "lojas_parceiras") & (channels["return_rate"] == ref)].iloc[0]
    margin = p["net_price_brl"] - p["variable_cost_brl"]
    eol_unit = rl.end_of_life_unit_cost(p)
    unit_net = margin - eol_unit
    break_even = math.ceil(pp.BUDGET / unit_net)
    zero_npv = math.ceil(pp.units_for_zero_npv(unit_net))
    t_be = pp.payback_months(pp.cash_flows(1000, unit_net))
    cap_cards = math.floor(p["management_reserve_brl"] / voucher["cost_per_return_brl"])
    mail_cost = p["reverse_freight_brl"] + p["return_kit_brl"]
    scores = concept_scores()
    lo_w, hi_w, b_wins = concept_winner_range()
    critical = " → ".join(pp.critical_path())
    se_s_share = rl.southeast_south_population_share()
    mean_force = sa.porter_mean()

    b = Builder(label_map=LABEL_MAP, lang="en", compact=True)
    b.title_block(
        "Carbon Fiber EDC Multitool",
        "Product development report, English edition",
        "This report presents the development plan for a compact carbon-fibre card multitool in the CR80 format, "
        "for everyday carry (EDC) and urban cyclists: product and market, concept design, project plan, economic "
        "viability and end-of-life planning. It is a condensed English edition of the course report, which is "
        "written in Portuguese. Every number comes from the reproducible models in the project repository; "
        "prices, costs and scores are planning hypotheses unless a source is cited.",
    )

    # ------------------------------------------------------------------ 1
    b.heading("1. Product and market", 1)
    b.heading("1.1 Concept and innovation", 2)
    b.para(
        "The product is one flat piece of carbon-fibre laminate, 85.60 × 53.98 mm and up to 2 mm thick, with "
        "hexagonal wrench cutouts on its outline, a blunt chamfer that opens package tape, an engraved scale and an "
        "engraved lot number. It has no moving parts. The innovation is incremental, not pioneering: card-shaped "
        f"multitools have been patented since 1993 {cite('us5328026')}, metal cards such as the Wallet Ninja exist "
        f"{cite('walletninja')}, and a single-piece carbon-fibre card with seven hex wrenches and a ruler, the "
        f"Touch of Ginger TOG09, is already sold {cite('tog09')}. The proposed card differs by the chamfer for "
        "opening packages, the engraved scale and lot, a safe edge proven in testing, after-sales service and an "
        "end-of-life take-back. Lower mass and thickness than metal cards are hypotheses that depend on the tests "
        "of activity A6."
    )
    b.table(
        "Product scope: functions, parameters and acceptance criteria",
        ["Function or parameter", "Specification", "Acceptance criterion"],
        [["Format and thickness", "CR80, 85.60 × 53.98 mm, up to 2 mm; single piece of carbon fibre and epoxy",
          "Measurement with a calibrated instrument"],
         ["Transmit torque (F1 and F2)", "Hexagonal cutouts on the outline",
          "No slipping or fracture at the torque defined in testing"],
         ["Open packaging (F3)", "Continuous blunt chamfer", "Opens the tape without touching the contents"],
         ["Measure (F4)", "Engraved scale", "Legible after the use tests"],
         ["Protect the user (F5)", "Radius and chamfer on the edge; inspection per lot",
          "No sharp edge; fracture in a safe mode, with no dangerous projection"],
         ["Transport", "Card in the wallet, with protected edge and engraved lot", "Fits a wallet; traceable lot"]],
        [3.8, 6.4, 5.8],
        "own elaboration; criteria from the technical validation plan of the project, with 5 samples per test.",
        font=9,
    )
    b.heading("1.2 Competitors", 2)
    b.table(
        "Competitors",
        ["Competitor", "Category", "Declared warranty", "Price, material and dimensions"],
        [["Touch of Ginger TOG09", "Wallet card, carbon fibre", "No public information",
          "US$ 14.95 to 19.99 at one store, discontinued at another; single piece; 85.7 × 54.0 mm; 1.5 mm; "
          f"23 to 28 g; 7 wrenches of 6 to 12 mm and a ruler {cite('tog09')}"],
         ["Wallet Ninja", "Wallet multitool, metal", "No public information",
          f"US$ 20; stainless steel; 85.6 × 54.0 mm; 28 g; 19 functions {cite('walletninja')}"],
         ["Victorinox", "Multi-use knife (SwissCard line)",
          f"2 years, repair or replacement, in the listed categories {cite('victorinox_warranty')}",
          "Official price unavailable; retailers disagree on currency and date"],
         ["Leatherman", "Multi-tool pliers (Micra, keychain size)",
          f"25 years, repair first {cite('leatherman_warranty')}",
          f"US$ 49.95; stainless steel; 63.5 mm closed, 9.4 mm thick; 51 g; 10 functions {cite('micra')}"]],
        [2.8, 3.4, 4.2, 5.6],
        "official manufacturer and retailer pages, consulted on 11 and 15 Nov 2026 (prices in US dollars, no "
        "publication date on the pages). Prices in reais and the official SwissCard price are missing.",
    )
    b.para(
        "Competitors sell for US$ 15 to 50, far below the base price of R$ 199, and the TOG09 already offers "
        "carbon fibre and hex wrenches for under US$ 20: the card can only hold its price through proven "
        "differentiation, which the price experiment of the primary research must test."
    )
    b.heading("1.3 Target audience and information sources", 2)
    b.para(
        f"The national cyclist profile survey {cite('cyclist')} covers 11,956 cyclists in 18 cities, not the whole "
        "country. Among them, 26% are women, 59% are up to 39 years old and 54% earn up to 2 minimum wages; only "
        "36% earn more. 74% ride to work and 34% ride every day; the most frequent trip takes 15 to 30 minutes "
        "(54%) and the main motivation is practicality (42%), followed by health (26%) and cost (21%). Two points "
        "guide the product: use is daily and utilitarian, so the tool would be carried on the street; and income is "
        "low, which makes a price of R$ 199 an obstacle for most and justifies aiming at the third with higher "
        f"income. Regional context: the Southeast and South hold {share(se_s_share, 1)} of the population "
        f"{cite('ibge_pop', 'ibge_income')}."
    )
    b.para(
        "Primary research is planned, not yet done: 20 to 30 interviews, a survey of 100 to 150 responses with "
        "regional quotas (margin of error of 8 to 10 percentage points at 95% confidence "
        f"{cite('cochran')}) and a price experiment with the four Van Westendorp questions {cite('vanwestendorp')}. "
        "No public report sizes the market for pocket multitools, so no market-share goal is set."
    )
    b.heading("1.4 Strategic environment", 2)
    b.swot_matrix("SWOT matrix of the carbon-fibre multitool card.", sa.SWOT_EN, source="own elaboration.")
    b.table(
        "Intensity of the five competitive forces (score from 1, very low, to 5, very high)",
        ["Force", "Score", "Justification"],
        [[name, str(score), why] for name, score, why in sa.PORTER_EN]
        + [["Mean", n1(mean_force), f"Competitive pressure {sa.porter_level(mean_force, 'en')}."]],
        [4.4, 1.2, 10.4],
        "own elaboration; scores by team judgement.",
        bold_rows=(5,), right_cols=(1,),
    )
    b.para(
        f"The mean of {n1(mean_force)} shows medium-high pressure. The three strongest forces (new entrants, "
        "suppliers and substitutes) mean the product should not compete on price: its defence is differentiation "
        "proven in testing, brand building in the EDC and cyclist niche, and negotiation with more than one sheet "
        "and machining supplier."
    )

    # ------------------------------------------------------------------ 2
    b.heading("2. Concept design", 1)
    b.heading("2.1 Concept selection", 2)
    b.table(
        "Morphological matrix and composition of alternatives A, B and C (number of the chosen principle)",
        ["Function", "Principle 1", "Principle 2", "Principle 3", "A", "B", "C"],
        [["F1 Position and fit", "Outline with cutouts", "Side groove", "Raised guide", "1", "1", "1"],
         ["F2 Transmit torque", "Hexagons on the outline", "Metal insert", "Flat slot", "1", "1", "2"],
         ["F3 Open packaging", "Exposed blade", "Blunt chamfer", "Serration", "1", "2", "2"],
         ["F4 Measure", "Engraved scale", "No scale", "Label scale", "1", "1", "2"],
         ["F5 Protect the user", "Sharp edge", "Radius and chamfer with inspection", "Protective cover", "1", "2", "3"]],
        [3.4, 3.2, 3.4, 2.6, 1.2, 1.2, 1.0],
        "own elaboration.",
        right_cols=(4, 5, 6),
    )
    b.table(
        "Alternatives and weighted score (scale from 1 to 5)",
        ["Criterion", "Weight", "A: blade", "B: chamfer", "C: insert"],
        [[CRITERIA_EN[name], share(weight), *[str(SCORES[k][i]) for k in "ABC"]]
         for i, (name, weight) in enumerate(CRITERIA.items())]
        + [["Weighted score", "100%", *[n2(scores[k]) for k in "ABC"]]],
        [4.6, 2.0, 3.1, 3.1, 3.2],
        "own elaboration. Weights and scores are team judgement.",
        bold_rows=(5,), right_cols=(1, 2, 3, 4),
    )
    b.para(
        f"Concept B scores {n2(scores['B'])}, against {n2(scores['A'])} for A and {n2(scores['C'])} for C. Varying "
        f"the weight of safety from {share(lo_w)} to {share(hi_w)}, B {'wins in every case' if b_wins else 'does not always win'}."
    )
    b.heading("2.2 Product structure, process plans and packaging", 2)
    b.para(
        f"{R('structure')} links each item to a process plan and {R('macro')} details the operations of each plan. "
        "Cutting times come from public milling parameters for carbon-fibre sheet: a feed of 1,000 to 1,500 mm/min "
        f"and 0.5 mm per pass on a 2 mm sheet {cite('toolstoday')}, and 900 mm/min on a 1.5 mm sheet "
        f"{cite('cncstep')}. With a 279 mm outline and four passes, that is about 1.1 m of toolpath and 0.9 to "
        "1.2 min per operation; machining a lot of 2,000 cards takes 62 to 83 machine-hours. Laser cutting leaves "
        f"a heat-affected zone and delamination {cite('laser')}, so cold cutting is used. Manual operations have "
        "no public data and will be timed on the prototype."
    )
    b.figure("product_structure_en.png", "Product structure in systems and items, with the process plan that covers "
             "each item; manufactured items in red and purchased items in black.", width_cm=15.0,
             source="own elaboration.")
    timed = f"0.9 to 1.2 min {cite('toolstoday', 'cncstep')}"
    b.table(
        "Macro process plan (operation, plan, station, description, time and control)",
        ["Op.", "Plan", "Station", "Description", "Time", "Control"],
        [["10", "PIR", "Receiving", "Receive the sheet and check the certificate", "To be timed in A5", "Lot and thickness"],
         ["20", "PIR", "Bench", "Inspect the lot", "To be timed in A5", "Visual and dimensional"],
         ["30", "PPF-1", "Cutting", "Fix the sheet on the table", "To be timed in A5", "Fixing without play"],
         ["40", "PPF-1", "Cutting", "Cut the outline", timed, "External dimension"],
         ["50", "PPF-1", "Cutting", "Machine cutouts and scale", timed, "Geometry of the functions"],
         ["60", "PPF-2", "Bench", "Chamfer and sand, with respiratory protection", "To be timed in A5", "Roughness and edge"],
         ["70", "PPF-2", "Bench", "Clean and inspect", "To be timed in A5", "Delamination after cutting"],
         ["80", "PPF-3", "Engraving", "Engrave the lot identification", "To be timed in A5", "Traceability"],
         ["90", "PPM", "Packing", "Pack", "To be timed in A5", "Edge protection"],
         ["100", "PPM", "Dispatch", "Release the lot", "To be timed in A5", "Inspection record"]],
        [1.0, 1.5, 2.0, 5.2, 3.2, 3.1],
        "own elaboration. PIR: receiving inspection; PPF: manufacturing; PPM: assembly.",
        font=9,
    )
    b.table(
        "Packaging conditions (six tasks of the course chapter)",
        ["Task", "Adopted condition", "Item"],
        [["Distribution", "Shipped by the post office in a rigid envelope, from the group's base", "P7"],
         ["Marking", "Lot, material, limits of use and warranty printed on the box and in the manual", "P8, P9"],
         ["Critical element", "The card edge, which must not chip or touch other products", "P7"],
         ["Adaptation", "Inner cradle that holds the card in place and away from other products", "P7"],
         ["Packaging design", "Outer box identified by lot", "P8"],
         ["Process", "Packing at the bench, with a lot check before dispatch", "Operations 90 and 100"]],
        [3.4, 9.2, 3.4],
        "own elaboration.",
        font=9,
    )
    b.heading("2.3 Ergonomics and human error", 2)
    b.para(
        f"The ergonomic evaluation uses the SHERPA method {cite('sherpa')}: for each user task it lists the possible "
        f"errors (slips, lapses and mistakes {cite('reason')}), the prevention in the design and the verification. "
        "The card is held in a pinch between thumb and index finger; its 2 mm thickness and the lack of a handle "
        "limit the force and torque that can be applied, so the torque limit is a design requirement."
    )
    b.table(
        "Ergonomic evaluation: operating human errors, prevention in the design and verification",
        ["Task", "Possible human error", "Prevention in the design", "Verification"],
        [["Taking the card out of the wallet", "Holding it by the edge and getting cut (slip)",
          "Continuous chamfer and rounded corners", "Edge inspection per lot (A7)"],
         ["Choosing the cutout", "Using the wrong size and rounding off the screw (mistake)",
          "Size engraved beside each cutout", "Observed use test (A6)"],
         ["Applying torque", "Forcing past the limit or out of the card plane and breaking it (mistake)",
          "Torque limit in the manual; fracture in a safe mode, with no projection", "Torque test to failure (A6)"],
         ["Opening a package", "Cutting the contents or the hand when pulling the chamfer (slip)",
          "Blunt chamfer that breaks the tape without cutting the contents",
          "Opening test without touching the contents (A6)"],
         ["Measuring with the scale", "Misreading for lack of contrast (slip)",
          "Scale engraved in low relief, with contrast", "Legibility test (A6)"],
         ["Storing", "Leaving the card outside the wallet and losing it (lapse)",
          "CR80 format that fits the wallet; lot engraved for replacement", "Observed use test (A6)"]],
        [3.0, 4.6, 4.6, 3.8],
        "own elaboration, with the SHERPA method and the error classification of Reason.",
        font=9,
    )

    # ------------------------------------------------------------------ 3
    b.heading("3. Project plan", 1)
    b.heading("3.1 Organization, schedule and budget", 2)
    b.figure("org_chart_en.png", "Project organogram: roles, hierarchy and the activities of each stakeholder.",
             width_cm=13.0, source="own elaboration.")
    cost_by_id = costs.set_index("id")
    rows = [[row.id, pp.ACTIVITY_NAMES_EN[row.id], f"W{row.start_week}", str(row.duration_weeks),
             f"W{row.end_week}", row.predecessors, n0(cost_by_id.loc[row.id, "activity_cost_brl"])]
            for row in sched.itertuples()]
    rows.append(["", "Project", "W1", str(int(sched["end_week"].max())), f"W{int(sched['end_week'].max())}", "",
                 n0(costs["activity_cost_brl"].sum())])
    b.table(
        "Activities, schedule and cost (R$)",
        ["ID", "Activity", "Start", "Dur. (weeks)", "End", "Predecessors", "Cost"],
        rows,
        [1.0, 5.8, 1.4, 1.8, 1.4, 2.4, 2.2],
        f"own elaboration. The activity totals are the group's original estimates; with the R$ "
        f"{n0(pp.RESERVE)} management reserve the limit is {reais(pp.BUDGET + pp.RESERVE)}.",
        font=9, bold_rows=(len(rows) - 1,), right_cols=(3, 6),
    )
    b.figure("gantt_en.png", "Cumulative cost (S-curve) and Gantt chart of the project, in weeks.", width_cm=15.0,
             source="own elaboration from the activities table.")
    b.para(
        f"The critical path is {critical}, {int(sched['end_week'].max())} weeks long; activity A4 has one week of "
        f"slack. The project costs {reais(pp.BUDGET)} plus a {reais(pp.RESERVE)} reserve. Schedule and cost "
        "deviations will be tracked with SPI and CPI (earned value) against this baseline."
    )

    # ------------------------------------------------------------------ 4
    b.heading("4. Economic viability", 1)
    b.para(
        "The model uses a weekly cash flow: the investment follows the cost baseline of the schedule, and sales, "
        "at a constant pace, start after the development. Flows fall at the end of each week and the end-of-life "
        "cost is proportional to the units sold. With the notation below, the following equations hold:"
    )
    eq.add_equations(b, "en")
    V, N, SUB, SUM = eq.V, eq.N, eq.SUB, eq.SUM
    F_t, C_t, T_d, T_v, i_s, r_star = eq.F_t, eq.C_t, eq.T_d, eq.T_v, eq.i_s, eq.r_star
    im = lambda fragment: (fragment,)  # noqa: E731
    b.math_para([
        "Here ", im(V("p")), f" is the net unit price (R$ {n0(p['net_price_brl'])}); ", im(SUB(V("c"), V("v"))),
        f" the variable cost (R$ {n0(p['variable_cost_brl'])}); ", im(SUB(V("c"), V("f"))),
        f" the end-of-life cost per card (R$ {n2(eol_unit)}); ", im(V("Q")), " the cards sold in 12 months; ",
        im(C_t), " the cost of week ", im(V("t")), " in the baseline; ",
        im(V("I") + N(" = ") + SUM(N("t = 1"), T_d, C_t) + N(f" = R$ {n0(pp.BUDGET)}")), " the investment; ",
        im(T_d + N(" = 14")), " and ", im(T_v + N(" = 52")), " the weeks of development and sales, with ",
        im(V("T") + N(" = ") + T_d + N(" + ") + T_v), "; and ", im(V("i")),
        f" the discount rate ({share(pp.DISCOUNT_RATE, 2)} a year, the Selic target {cite('bcb')}). The monthly IRR "
        "converts the weekly rate ", im(r_star), "; the payback is ", im(V("τ") + N(" · 12/52")),
        " months, with linear interpolation within week ", im(V("τ")), ". The simple break-even is ",
        im(SUB(V("Q"), N("eq")) + N(" = ⌈") + eq.FR(V("I"), V("m")) + N("⌉")),
        ", where the ROI is zero. Because the flow changes sign once, the positive IRR is unique (Descartes' rule "
        "of signs)."])
    econ_rows = []
    for units in (600, 1000, 2000):
        e = pp.economics(units, unit_net)
        econ_rows.append([n0(units), n1(e["payback_months"]), share(e["roi"]), reais(e["npv"]), share(e["irr_monthly"], 1)])
    b.table(
        "Economic viability by volume sold in 12 months (net price R$ 199, variable cost R$ 80)",
        ["Cards sold", "Break-even (month)", "ROI", "NPV", "Monthly IRR"],
        econ_rows,
        [3.2, 3.2, 2.6, 3.4, 3.6],
        f"own elaboration. ROI: net gain over the investment of {reais(pp.BUDGET)}. NPV at "
        f"{share(pp.DISCOUNT_RATE, 2)} a year; IRR from the weekly flow. These are planning goals, not forecasts.",
        right_cols=(0, 1, 2, 3, 4),
    )
    b.figure("viability_chart_en.png", "Cumulative investment, sales and profit by month in the base scenario of "
             "1,000 cards in 12 months; dashed lines show 600 and 2,000 cards.", width_cm=14.0,
             source="own elaboration; sales at a constant pace over the 12 months after the launch.")
    b.para(
        f"With a net margin of {reais(unit_net, 2)} per card after {reais(eol_unit, 2)} of end-of-life cost, the "
        f"base scenario recovers the investment in month {n1(t_be)} ({R('viability_chart')}). The simple break-even "
        f"needs {break_even} cards and the NPV is positive from {zero_npv}. The analysis must be reviewed at each "
        "decision point, since planning relies on preliminary information."
    )

    # ------------------------------------------------------------------ 5
    b.heading("5. End of life", 1)
    b.figure("reverse_flow_en.png", "End-of-life flow: triage, stock by lot and disposal; machining offcuts join "
             "the same stock as the returned material.", width_cm=10.5, source="own elaboration.")
    b.table(
        "End-of-life decisions",
        ["Question", "Decision", "Evidence", "Data still needed"],
        [["Is there a benefit for the customer?",
          f"Yes: free reverse shipping and a R$ {n0(p['voucher_brl'])} discount voucher, one per validated card; "
          f"cap of {n0(cap_cards)} cards in the pilot",
          f"Cost of R$ {n0(voucher['total_cost_brl'])} at {share(ref)} returns: R$ {n2(voucher['cost_per_unit_sold_brl'])} "
          f"per unit sold, {share(voucher['share_of_contribution_margin'], 1)} of the margin",
          "Post-office price, redemption rate"],
         ["Are there stores to collect returns?",
          "No: reverse mail through the post office; in-person drop-off only at the group's base",
          f"Stores: {n2(store['returns_per_store_per_month'])} cards per store per month and "
          f"R$ {n2(store['cost_per_return_brl'])} per card, against R$ {n2(mail_cost)} by mail; ceiling of "
          f"{share(se_s_share, 1)} of the population",
          "Post offices and stores by state"],
         ["How is remanufacturing handled?",
          "The card is not remanufactured; it is reused in cascade (grades A to D) and recycled by consolidated lot",
          f"Rework would cost R$ {n0(reman['cost_per_recovered_card_brl'])} per recovered card, against "
          f"R$ {n0(p['variable_cost_brl'])} for a new one; it breaks even only with "
          f"{share(reman['minimum_grade_a_yield'])} of recoverable pieces",
          "Acceptance, minimum lot and price of the recycler; residue assessment"]],
        [3.0, 4.6, 5.6, 2.8],
        "own elaboration. All values are planning scenarios.",
        font=9,
    )
    b.para(
        f"Take-back is voluntary: Law 12,305 {cite('law12305')} makes reverse logistics mandatory only for "
        "agrochemicals, batteries, tyres, lubricants, lamps and electronics, and extends it to other products only "
        "by regulation or sector agreement. Shared responsibility remains, and this reading should be confirmed by "
        f"legal advice. The return rate of {share(ref)} comes from another product's take-back programme, without a "
        f"reward, which saw about 22% returns despite 92% stated intention {cite('harden')}; it is a scenario, not a "
        f"forecast. Reverse postage needs a seller contract and its price comes only from the contract or the "
        f"simulator {cite('correios')}. Only one Brazilian company is known to recover cured composite, without "
        f"publishing minimum lot or price {cite('recaltech')}, so material is stocked by lot until a disposer is "
        f"confirmed. Consumer rights set a 7-day withdrawal and a 90-day statutory warranty {cite('cdc')}."
    )

    # ------------------------------------------------------------------ 6
    b.heading("6. Conclusion and open points", 1)
    b.para(
        f"The project costs {reais(pp.BUDGET)} plus a {reais(pp.RESERVE)} reserve over {int(sched['end_week'].max())} "
        f"weeks. Concept B has the highest score, {n2(scores['B'])}. The investment is recovered with {break_even} "
        f"cards at R$ {n0(p['net_price_brl'])} and the NPV is positive from {zero_npv}, but competitors cost far "
        f"less and one direct carbon-fibre competitor exists, so viability depends on the market paying for "
        f"differentiation. Competitive pressure is {sa.porter_level(mean_force, 'en')} ({n1(mean_force)} out of 5). "
        "Take-back by reverse postage is recommended as a voluntary measure, paid from the sales margin."
    )
    b.para("Open points, in the order they should be closed:")
    for lead, text in (
        ("Primary research: ", "interviews, concept test and price experiment, which have not been run."),
        ("Prices: ", "quotations in reais for the sheet and the machining, and the official SwissCard price."),
        ("Tests: ", "torque, edge and delamination tests (activity A6) and measured mass and thickness."),
        ("Intellectual property: ", "a search at the Brazilian patent office and legal advice, because an active "
                                    f"design right covers a card-shaped multitool {cite('ca175697')} and two older "
                                    f"patents have expired {cite('us8713735')}."),
    ):
        b.bullet(text, bold_lead=lead)

    b.heading("References", 1)
    for number, key in enumerate(cite.order, start=1):
        b.small(f"[{number}] {SOURCES[key]}", 9.5, left=True)
    return b


def render_figures() -> None:
    """Draw every figure the English edition uses."""
    reverse_flow_diagram.write_all(png_dir=ROOT / "outputs" / "visualizations")
    report_diagrams.render_all()
    strategic_analysis.render_all()


def main() -> None:
    render_figures()
    builder = build_report()
    OUTPUT_DOCX.parent.mkdir(parents=True, exist_ok=True)
    builder.doc.save(OUTPUT_DOCX)
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    HASH_FILE.write_text(report_text_hash(builder.doc) + "\n", encoding="utf-8")
    print(f"Report written to: {OUTPUT_DOCX}")


if __name__ == "__main__":
    main()
