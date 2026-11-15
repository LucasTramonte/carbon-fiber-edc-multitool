"""Figures for the Portuguese report, drawn in the style of the course examples.

* WBS/EAP as a top-down tree: Produto -> Entrega -> Pacote de trabalho (Cap. 5);
* functional block diagram with system boundary and energy/material/signal
  lines (Cap. 7);
* product structure tree with fabricated items in red and purchased in black
  (Cap. 8);
* launch dependency diagram (Cap. 10) and product life-cycle figure (Cap. 12);
* Gantt with S-curve and precedence network (Cap. 5 and cost management).

Graphviz renders the diagrams; matplotlib renders the two charts.
"""

from __future__ import annotations

from pathlib import Path

import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

try:
    from src import project_plan as pp
    from src import reverse_logistics_model as rl
    from src.reverse_flow_diagram import build_flows, render_png, to_dot
except ImportError:  # pragma: no cover
    import project_plan as pp
    import reverse_logistics_model as rl
    from reverse_flow_diagram import build_flows, render_png, to_dot

ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "outputs" / "visualizations"
DARK, ORANGE, GREY, LIGHT, RED = "#263238", "#ef6c00", "#90a4ae", "#eceff1", "#b71c1c"

HEAD = (
    'graph [fontname="Times-Roman", fontsize=12, nodesep=0.18, ranksep=0.35, pad=0.1];\n'
    f'  node [fontname="Times-Roman", fontsize=12, shape=box, style=filled, fillcolor=white, color="{DARK}", margin="0.12,0.07"];\n'
    f'  edge [fontname="Times-Roman", fontsize=11, color="{DARK}", fontcolor="{DARK}"];\n'
)


def _q(text: str) -> str:
    return text.replace('"', "'").replace("\n", "\\n")


def wbs_dot() -> str:
    """Top-down-style WBS (drawn left to right for width): product, deliverables, packages."""
    product = _q("Cartão multitool\nvalidado e lançado\nem piloto")
    lines = ["digraph wbs {", "  rankdir=LR;", "  " + HEAD,
             f'  P [label="{product}", fillcolor="{DARK}", fontcolor=white];']
    for code, name in pp.DELIVERABLES.items():
        lines.append(f'  E{code[0]} [label="{_q(code + " " + name)}", fillcolor="{LIGHT}"];')
        lines.append(f"  P -> E{code[0]};")
    for a in pp.ACTIVITIES:
        wrapped = "\n".join(textwrap.wrap(f"{a.ident} · {a.name}", 30))
        lines.append(f'  {a.ident} [label="{_q(wrapped)}"];')
        lines.append(f"  E{a.wbs[0]} -> {a.ident};")
    lines.append("}")
    return "\n".join(lines)


def block_diagram_dot() -> str:
    """Cap. 7 style: total function, system boundary, flows by line type."""
    return f"""digraph blocos {{
  rankdir=LR;
  {HEAD}
  obj [label="Objeto a manipular\\n(parafuso, embalagem)", shape=plaintext, style=""];
  force [label="Força do\\nusuário", shape=plaintext, style=""];
  out [label="Tarefa concluída\\nsem dano ao usuário\\nnem ao objeto", shape=plaintext, style=""];
  read [label="Medida\\nlida", shape=plaintext, style=""];
  subgraph cluster_f {{
    label="Função total: Resolver imprevisto cotidiano   (fronteira do sistema)";
    labelloc=t; style="dashed"; color="{DARK}"; fontsize=12;
    F1 [label="F1 Posicionar\\ne encaixar"];
    F2 [label="F2 Transmitir\\ntorque"];
    F3 [label="F3 Abrir\\nembalagem"];
    F4 [label="F4 Medir"];
    F5 [label="F5 Proteger\\no usuário\\n(secundária)", fillcolor="{LIGHT}"];
  }}
  obj -> F1 [penwidth=3.2, label="material"];
  F1 -> F2 [penwidth=3.2];
  F1 -> F3 [penwidth=3.2];
  F2 -> out [penwidth=3.2];
  F3 -> out [penwidth=3.2];
  force -> F2 [penwidth=1.0, color="{ORANGE}", fontcolor="{ORANGE}", label="energia"];
  force -> F3 [penwidth=1.0, color="{ORANGE}"];
  F4 -> read [style=dashed, label="sinal"];
  F1 -> F4 [style=dashed];
  F5 -> F3 [style=dotted, arrowhead=none];
  F5 -> F2 [style=dotted, arrowhead=none];
}}
"""


def launch_dependency_dot() -> str:
    """Cap. 10 style: four support processes start before the launch phase."""
    return f"""digraph lancamento {{
  rankdir=LR;
  {HEAD}
  PL [label="Planejar\\nlançamento"];
  MK [label="Promover\\nmarketing"];
  LA [label="Lançar produto\\n(lote piloto)", fillcolor="{LIGHT}"];
  GE [label="Gerenciar lançamento\\n(resultados e satisfação)"];
  subgraph cluster_p {{
    label="Normalmente começam antes desta fase"; style="filled"; fillcolor="#e0e0e0"; color="{GREY}"; fontsize=11;
    V [label="Desenvolver processo\\nde vendas"];
    D [label="Desenvolver processo\\nde distribuição"];
    T [label="Desenvolver processo de\\nassistência técnica"];
    C [label="Desenvolver processo de\\natendimento ao cliente"];
  }}
  PL -> LA; MK -> LA;
  V -> LA; D -> LA; T -> LA; C -> LA;
  LA -> GE [style=dotted];
}}
"""


def network_dot() -> str:
    """Precedence network with early dates and slack (critical path in orange)."""
    sched = pp.schedule()
    lines = ["digraph rede {", "  rankdir=TB;", "  " + HEAD,
             f'  ini [label="Início", shape=circle, fillcolor="{LIGHT}"];',
             f'  fim [label="Fim\\nS{int(sched["end_week"].max())}", shape=circle, fillcolor="{LIGHT}"];']
    for r in sched.itertuples():
        color = f', color="{ORANGE}", penwidth=2' if r.critical else ""
        lines.append(f'  {r.id} [label="{r.id} · {r.duration_weeks} sem · S{r.start_week} a S{r.end_week} · folga {r.slack_weeks}"{color}];')
        if r.predecessors == "-":
            lines.append(f"  ini -> {r.id};")
        for pred in (x for x in r.predecessors.split(";") if x != "-"):
            crit = r.critical and bool(sched.loc[sched["id"] == pred, "critical"].item())
            lines.append(f'  {pred} -> {r.id}' + (f' [color="{ORANGE}", penwidth=2]' if crit else "") + ";")
        if r.successors == "-":
            lines.append(f"  {r.id} -> fim;")
    lines.append("}")
    return "\n".join(lines)


def lifecycle_figure(path: Path) -> None:
    """Cap. 12 slide 3 adapted: each customer's product life ends in a return."""
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 10)
    ax.axis("off")
    for x, label in ((4, "Início:\n1ª ideia"), (28, "Liberação da\nprodução"), (66, "Final da\nprodução"), (96, "Fim da\nvida")):
        ax.plot([x, x], [1.6, 8.2], color=DARK, lw=1, ls=":")
        ax.text(x, 0.6, label, ha="center", va="center", fontsize=9)
    bars = [(30, 55, 7.6), (33, 62, 6.9), (40, 70, 6.2), (47, 78, 5.5), (57, 88, 4.8), (68, 95, 4.1)]
    for start, end, y in bars:
        ax.plot([start, end], [y, y], color="#2e7d32", lw=5, solid_capstyle="butt")
        ax.scatter([end], [y], s=130, color="white", edgecolor="#2e7d32", zorder=3)
        ax.text(end, y, "↺", ha="center", va="center", fontsize=9, color="#2e7d32", zorder=4)
    xs = np.linspace(28, 70, 60)
    ax.plot(xs, 1.8 + 1.5 * np.sin((xs - 28) / 42 * np.pi) ** 0.6, color="#1565c0", lw=2)
    ax.text(40, 3.7, "volume de vendas", color="#1565c0", fontsize=9)
    ax.annotate("", xy=(66, 9.0), xytext=(28, 9.0), arrowprops={"arrowstyle": "<->", "color": DARK})
    ax.text(47, 9.25, "período de produção", ha="center", fontsize=9)
    ax.annotate("", xy=(96, 9.7), xytext=(55, 9.7), arrowprops={"arrowstyle": "<->", "color": DARK})
    ax.text(75.5, 9.95, "Descontinuar o produto: da 1ª devolução ao fim do suporte", ha="center", fontsize=9)
    for x, label in ((55, "1ª devolução"), (66, "Descontinuar\na produção"), (91, "Finalizar\nsuporte")):
        ax.text(x, 8.5 if x == 55 else 2.9, label, ha="center", va="center", fontsize=8.5,
                bbox={"boxstyle": "round", "fc": "#ffe0b2", "ec": ORANGE})
    ax.text(2, 9.6, "↺ devolução: reutilizar, remanufaturar, reciclar ou descartar", fontsize=9, color="#2e7d32")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


GANTT_TEXT = {
    "pt": {"budget": "orçamento: R$ 54 mil", "ylabel": "Custo (R$ mil)\nacumulado e semanal",
           "title": "Cronograma-base e curva S", "xlabel": "Semana do projeto (S1 a S14)",
           "legend": ("Caminho crítico", "Atividade com folga (A4: 1 semana)")},
    "en": {"budget": "budget: R$ 54k", "ylabel": "Cost (R$ thousand)\ncumulative and weekly",
           "title": "Baseline schedule and S-curve", "xlabel": "Project week (W1 to W14)",
           "legend": ("Critical path", "Activity with slack (A4: 1 week)")},
}


def gantt_scurve_figure(path: Path, lang: str = "pt") -> None:
    """Cumulative cost (S-curve) above a Gantt, as in the cost-management lesson."""
    text = GANTT_TEXT[lang]
    sched, base = pp.schedule(), pp.weekly_baseline()
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(10, 6.6), sharex=True,
                                      gridspec_kw={"height_ratios": [1, 1.7]})
    top.plot(base["week"], base["cumulative_brl"] / 1000, color=DARK, marker="o", ms=4)
    top.bar(base["week"], base["cost_brl"] / 1000, color=GREY, alpha=0.6, width=0.6)
    top.axhline(pp.BUDGET / 1000, color=ORANGE, ls="--", lw=1)
    top.set_ylim(0, 62)
    top.text(0.7, pp.BUDGET / 1000 + 2.2, text["budget"], color=ORANGE, fontsize=9)
    top.set_ylabel(text["ylabel"], fontsize=9)
    top.set_title(text["title"], fontsize=11)
    y = np.arange(len(sched))
    colors = [DARK if c else GREY for c in sched["critical"]]
    bottom.barh(y, sched["duration_weeks"], left=sched["start_week"] - 0.5, color=colors,
                edgecolor=DARK, height=0.6)
    names = {r.id: (r.activity if lang == "pt" else pp.ACTIVITY_NAMES_EN[r.id]) for r in sched.itertuples()}
    bottom.set_yticks(y, [f"{ident} · {names[ident]}" for ident in sched["id"]], fontsize=8)
    bottom.invert_yaxis()
    bottom.set_xticks(range(1, 15))
    bottom.set_xlim(0.5, 14.5)
    bottom.set_xlabel(text["xlabel"], fontsize=9)
    bottom.grid(axis="x", alpha=0.3)
    handles = [plt.Rectangle((0, 0), 1, 1, fc=DARK), plt.Rectangle((0, 0), 1, 1, fc=GREY)]
    bottom.legend(handles, list(text["legend"]), loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def card_sketch_figure(path: Path) -> None:
    """Architecture sketch: top view of the CR80 card with its integrated functions."""
    from matplotlib.patches import FancyBboxPatch, RegularPolygon

    length, width = 85.60, 53.98
    fig, ax = plt.subplots(figsize=(9, 5.4))
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(FancyBboxPatch((0, 0), length, width, boxstyle="round,pad=0,rounding_size=3.2",
                                fc="#37474f", ec=DARK, lw=2))
    ax.add_patch(plt.Rectangle((4, width - 4.2), length - 8, 1.6, fc="#546e7a", ec="none", hatch="////"))
    for cx, cy, r in ((9, 33, 5.0), (9, 20, 4.2), (9, 9.5, 3.4)):
        ax.add_patch(RegularPolygon((cx, cy), 6, radius=r, orientation=np.pi / 6, fc="white", ec=DARK, lw=1.2))
    for k in range(0, 61, 5):
        h = 3.2 if k % 10 == 0 else 1.8
        ax.plot([20 + k, 20 + k], [2.2, 2.2 + h], color="white", lw=1)
        if k % 10 == 0:
            ax.text(20 + k, 6.6, f"{k // 10}", color="white", ha="center", fontsize=7)
    ax.text(26, 30, "LOTE 001 · CFRP", color="#cfd8dc", fontsize=9, family="monospace")
    ax.annotate("", xy=(0, -5), xytext=(length, -5), arrowprops={"arrowstyle": "<->", "color": DARK})
    ax.text(length / 2, -8.5, "85,60 mm (CR80)", ha="center", fontsize=9)
    ax.annotate("", xy=(length + 5, 0), xytext=(length + 5, width), arrowprops={"arrowstyle": "<->", "color": DARK})
    ax.text(length + 7, width / 2, "53,98 mm", rotation=90, va="center", fontsize=9)
    labels = [((9, 33), (-20, 44), "recortes hexagonais\n(tamanhos a definir)", "black"),
              ((50, width - 3.4), (58, 68), "chanfro rombo contínuo\n(abre fita sem lâmina)", "black"),
              ((58, 7.5), (64, 17), "escala gravada (cm)", "white"),
              ((38, 30.5), (46, 41), "identificação de lote\n(rastreabilidade)", "white")]
    for target, text_pos, text, color in labels:
        ax.annotate(text, xy=target, xytext=text_pos, fontsize=9, ha="center", color=color,
                    arrowprops={"arrowstyle": "-", "color": ORANGE, "lw": 1.3})
    ax.set_xlim(-30, length + 20)
    ax.set_ylim(-26, 78)
    ax.set_title("Croqui da arquitetura: placa única de CFRP, espessura ≤ 2 mm (ilustrativo, sem escala de fabricação)",
                 fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def regional_income_figure(path: Path) -> None:
    """Weighted per-capita income by macro-region, in Portuguese."""
    try:
        from src.regional_market_analysis import build_regional_analysis, load_state_indicators
    except ImportError:  # pragma: no cover
        from regional_market_analysis import build_regional_analysis, load_state_indicators
    regional = build_regional_analysis(load_state_indicators())
    names = {"North": "Norte", "Northeast": "Nordeste", "Southeast": "Sudeste", "South": "Sul",
             "Central-West": "Centro-Oeste"}
    fig, ax = plt.subplots(figsize=(8, 4.2))
    bars = ax.bar([names[r] for r in regional["region"]], regional["weighted_mean_income_brl"], color=DARK)
    for bar, value in zip(bars, regional["weighted_mean_income_brl"]):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 30, f"R$ {value:,.0f}".replace(",", "."),
                ha="center", fontsize=9)
    ax.set(ylabel="R$ por pessoa por mês (média ponderada)", title="Rendimento domiciliar per capita por região, 2024")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def break_even_figure(path: Path) -> None:
    """Units needed to recover the development budget, in Portuguese."""
    prices = [149, 199, 249]
    cost = 80
    fig, ax = plt.subplots(figsize=(8, 4.2))
    x = np.arange(len(prices))
    for offset, budget, color, label in ((-0.2, 54000, DARK, "Orçamento: R$ 54 mil"),
                                         (0.2, 60000, ORANGE, "Orçamento com reserva: R$ 60 mil")):
        values = [int(np.ceil(budget / (p - cost))) for p in prices]
        bars = ax.bar(x + offset, values, 0.38, color=color, label=label)
        for bar, value in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, value + 12, str(value), ha="center", fontsize=9)
    ax.set_xticks(x, [f"R$ {p}" for p in prices])
    ax.set(xlabel="Preço líquido por unidade (custo variável hipotético: R$ 80)",
           ylabel="Unidades no ponto de equilíbrio", title="Unidades para recuperar o orçamento de desenvolvimento")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


STRUCTURE_TEXT = {
    "pt": {
        "headers": ("Produto", "Sistema (S)", "Itens", "Planos de processo"),
        "product": "Cartão\nmultitool",
        "fabricated": "Itens fabricados", "purchased": "Itens comprados",
        "abbreviations": "S: sistema.  PIR: plano de inspeção de recebimento.  PPF: plano de processo de "
                         "fabricação.  PPM: plano de processo de montagem.",
        "systems": {"body": "S corpo", "functions": "S funções", "identification": "S identificação",
                    "packaging": "S embalagem"},
        "items": {"P1": "Chapa curada de fibra de carbono", "P2": "Cartão recortado e usinado",
                  "P3": "Chanfro e acabamento", "P4": "Hexágonos e recortes", "P5": "Escala gravada",
                  "P6": "Gravação de lote", "P7": "Envelope ou berço", "P8": "Caixa externa",
                  "P9": "Manual e etiqueta"},
        "plans": {"PIR": "Inspeção de recebimento\noperações 10 e 20", "PPF-1": "Corte e usinagem\noperações 30 a 50",
                  "PPF-2": "Acabamento e inspeção\noperações 60 e 70", "PPF-3": "Gravação de lote\noperação 80",
                  "PPM": "Embalagem e expedição\noperações 90 e 100"},
    },
    "en": {
        "headers": ("Product", "System (S)", "Items", "Process plans"),
        "product": "Multitool\ncard",
        "fabricated": "Manufactured items", "purchased": "Purchased items",
        "abbreviations": "S: system.  PIR: receiving inspection plan.  PPF: manufacturing process plan.  "
                         "PPM: assembly process plan.",
        "systems": {"body": "S body", "functions": "S functions", "identification": "S identification",
                    "packaging": "S packaging"},
        "items": {"P1": "Cured carbon-fibre sheet", "P2": "Cut and machined card", "P3": "Chamfer and finishing",
                  "P4": "Hexagons and cutouts", "P5": "Engraved scale", "P6": "Lot marking", "P7": "Envelope or cradle",
                  "P8": "Outer box", "P9": "Manual and label"},
        "plans": {"PIR": "Receiving inspection\noperations 10 and 20", "PPF-1": "Cutting and machining\noperations 30 to 50",
                  "PPF-2": "Finishing and inspection\noperations 60 and 70", "PPF-3": "Lot marking\noperation 80",
                  "PPM": "Packing and dispatch\noperations 90 and 100"},
    },
}

# system -> items (code, manufactured?, process plan)
STRUCTURE = (
    ("body", (("P1", False, "PIR"), ("P2", True, "PPF-1"))),
    ("functions", (("P4", True, "PPF-1"), ("P5", True, "PPF-1"), ("P3", True, "PPF-2"))),
    ("identification", (("P6", True, "PPF-3"),)),
    ("packaging", (("P7", False, "PPM"), ("P8", False, "PPM"), ("P9", False, "PPM"))),
)
PLAN_STYLE = {"PIR": ("#fde7c8", "#e65100", "#4e342e"), "PPF-1": ("#cfe8ea", "#00796b", "#004d40"),
              "PPF-2": ("#cfe8ea", "#00796b", "#004d40"), "PPF-3": ("#cfe8ea", "#00796b", "#004d40"),
              "PPM": ("#e53935", "#b71c1c", "#ffffff")}


def _document_icon(ax, x: float, y: float, label: str, style: tuple[str, str, str]) -> None:
    """A page with a folded corner, as in the course example, labelled with the plan code."""
    fill, edge, ink = style
    w, h, fold = 7.6, 7.2, 1.9
    ax.add_patch(plt.Polygon([(x, y - h / 2), (x + w - fold, y - h / 2), (x + w, y - h / 2 + fold),
                              (x + w, y + h / 2), (x, y + h / 2)], closed=True, fc=fill, ec=edge, lw=1.2))
    ax.add_patch(plt.Polygon([(x + w - fold, y - h / 2), (x + w - fold, y - h / 2 + fold), (x + w, y - h / 2 + fold)],
                             closed=True, fc="white", ec=edge, lw=0.8))
    ax.text(x + w / 2, y + 0.9, label, ha="center", va="center", fontsize=6.8, fontweight="bold", color=ink)


def product_structure_figure(path: Path, lang: str = "pt") -> None:
    """Product breakdown in the style of the course example (Cap. 8): product, systems, items (fabricated in
    red, purchased in black) and, at the right, the process plan that covers each item."""
    text = STRUCTURE_TEXT[lang]
    row, pad, gap = 5.0, 1.3, 3.4
    fig, ax = plt.subplots(figsize=(9.0, 7.2))
    ax.set_xlim(0, 100)
    ax.set_ylim(80.0, -2)
    ax.axis("off")
    columns = {"product": (0.5, 10.5), "system": (15.5, 15.5), "items": (36.0, 32.0)}
    for (name, (x, w)), header in zip(columns.items(), text["headers"][:3]):
        ax.text(x + w / 2, -0.4, header, ha="center", va="center", fontsize=9.5, fontweight="bold", color=DARK)
    ax.text(79.0, -0.4, text["headers"][3], ha="center", va="center", fontsize=9.5, fontweight="bold", color=DARK)

    y = 3.0
    centres, item_y = [], {}
    boxes = []
    for system, items in STRUCTURE:
        height = len(items) * row + 2 * pad
        boxes.append((system, items, y, height))
        centres.append(y + height / 2)
        for k, (code, _, _) in enumerate(items):
            item_y[code] = y + pad + row * (k + 0.5)
        y += height + gap
    middle = (centres[0] + centres[-1]) / 2

    px, pw = columns["product"]
    ax.add_patch(plt.Rectangle((px, middle - 5), pw, 10, fc=DARK, ec=DARK))
    ax.text(px + pw / 2, middle, text["product"], ha="center", va="center", fontsize=9.5, color="white",
            fontweight="bold")
    spine = px + pw + 2.2
    ax.plot([px + pw, spine], [middle, middle], color=DARK, lw=1.1)
    ax.plot([spine, spine], [centres[0], centres[-1]], color=DARK, lw=1.1)
    sx, sw = columns["system"]
    ix, iw = columns["items"]
    for (system, items, top, height), centre in zip(boxes, centres):
        ax.plot([spine, sx], [centre, centre], color=DARK, lw=1.1)
        ax.add_patch(plt.Rectangle((sx, centre - 3.1), sw, 6.2, fc="white", ec=DARK, lw=1.2))
        ax.text(sx + sw / 2, centre, text["systems"][system], ha="center", va="center", fontsize=9.5,
                fontweight="bold", color=DARK)
        ax.plot([sx + sw, ix], [centre, centre], color=DARK, lw=1.1)
        ax.add_patch(plt.Rectangle((ix, top), iw, height, fc="white", ec=DARK, lw=1.2))
        for k, (code, made, _) in enumerate(items):
            ax.text(ix + 1.4, item_y[code], f"{code}  {text['items'][code]}", ha="left", va="center", fontsize=8.6,
                    color=RED if made else "black")

    # process plans: one icon per plan, at the mean height of the items it covers
    plans: dict[str, list[float]] = {}
    for _, items in STRUCTURE:
        for code, _, plan in items:
            plans.setdefault(plan, []).append(item_y[code])
    bus = ix + iw + 2.4
    icon_x = 73.0
    for plan, ys in plans.items():
        target = sum(ys) / len(ys)
        for yy in ys:
            ax.plot([ix + iw, bus, bus, icon_x], [yy, yy, target, target], color=GREY, lw=1.0, solid_joinstyle="round")
        _document_icon(ax, icon_x, target, plan, PLAN_STYLE[plan])
        ax.text(icon_x + 9.4, target, text["plans"][plan], ha="left", va="center", fontsize=7.6, color=DARK)

    legend_y = 73.0
    ax.add_patch(plt.Rectangle((0.5, legend_y - 1.7), 5.5, 3.4, fc="white", ec=RED, lw=1.4))
    ax.text(7.2, legend_y, text["fabricated"], ha="left", va="center", fontsize=8.4, color=RED)
    ax.add_patch(plt.Rectangle((26.0, legend_y - 1.7), 5.5, 3.4, fc="white", ec="black", lw=1.4))
    ax.text(32.7, legend_y, text["purchased"], ha="left", va="center", fontsize=8.4)
    ax.text(0.5, legend_y + 4.2, text["abbreviations"], ha="left", va="center", fontsize=7.6, color=DARK)
    fig.tight_layout(pad=0.4)
    fig.savefig(path, dpi=190)
    plt.close(fig)


ORG_LABELS_EN = {
    "SP": "Sponsor (lecturer)\napproves the charter and the phases",
    "GP": "Project manager (student)\nschedule, cost and risks",
    "EQ": "Project team\nrequirements and tests\nA1, A2, A6, A9",
    "PJ": "Designer\nCAD and tolerances\nA3",
    "CP": "Purchasing\nsheet and machining\nA4",
    "PD": "Production and quality\nprocess and inspection\nA7",
    "MK": "Marketing and service\nsales and take-back\nA8",
    "FO": "Suppliers\nsheet and machining\nA4, A5",
    "US": "Users and customers\ntests and purchase\nA1, A6, A8",
    "CR": "Post office and recycler\nreverse freight and disposal\nA8, A9",
}

ORG_LABELS = {
    "SP": "Patrocinador (docente)\naprova a minuta e as fases",
    "GP": "Gerente do projeto (discente)\nprazo, custo e riscos",
    "EQ": "Equipe de projeto\nrequisitos e ensaios\nA1, A2, A6, A9",
    "PJ": "Projetista\nCAD e tolerâncias\nA3",
    "CP": "Compras\nchapa e usinagem\nA4",
    "PD": "Produção e qualidade\nprocesso e inspeção\nA7",
    "MK": "Marketing e atendimento\nvendas e recolhimento\nA8",
    "FO": "Fornecedores\nchapa e usinagem\nA4, A5",
    "US": "Usuários e clientes\ntestes e compra\nA1, A6, A8",
    "CR": "Correios e reciclador\nfrete reverso e destino\nA8, A9",
}


def org_chart_dot(lang: str = "pt") -> str:
    """Project organogram (Cap. 5): hierarchy, roles and the activities each one answers for."""
    q = {key: _q(text) for key, text in (ORG_LABELS if lang == "pt" else ORG_LABELS_EN).items()}
    external = "Interessados externos" if lang == "pt" else "External stakeholders"
    return f"""digraph organograma {{
  rankdir=TB;
  {HEAD}
  SP [label="{q['SP']}", fillcolor="{DARK}", fontcolor=white];
  GP [label="{q['GP']}", fillcolor="{LIGHT}"];
  EQ [label="{q['EQ']}"];
  PJ [label="{q['PJ']}"];
  CP [label="{q['CP']}"];
  PD [label="{q['PD']}"];
  MK [label="{q['MK']}"];
  subgraph cluster_ext {{
    label="{external}"; style="dashed"; color="{GREY}"; fontsize=11;
    FO [label="{q['FO']}", fillcolor="#fafafa"];
    US [label="{q['US']}", fillcolor="#fafafa"];
    CR [label="{q['CR']}", fillcolor="#fafafa"];
  }}
  SP -> GP;
  GP -> EQ; GP -> PJ; GP -> CP; GP -> PD; GP -> MK;
  EQ -> US [style=dashed]; CP -> FO [style=dashed]; MK -> CR [style=dashed];
}}
"""


VIABILITY_TEXT = {
    "pt": {"scenarios": ("600 cartões", "2.000 cartões"), "break_even": "Equilíbrio: mês {t}",
           "profit": "Lucro (1.000 cartões)", "sales": "Vendas (1.000 cartões)",
           "investment": "Investimento: R$ {v} mil", "gain": "Lucro efetivo", "launch": "Lançamento",
           "arrows": ("Desenvolvimento", "Vendas até o equilíbrio", "Tempo total até o equilíbrio"),
           "x": "Meses desde o início do projeto", "y": "R$ mil acumulados", "decimal": ","},
    "en": {"scenarios": ("600 cards", "2,000 cards"), "break_even": "Break-even: month {t}",
           "profit": "Profit (1,000 cards)", "sales": "Sales (1,000 cards)",
           "investment": "Investment: R$ {v}k", "gain": "Net gain", "launch": "Launch",
           "arrows": ("Development", "Sales until break-even", "Total time to break-even"),
           "x": "Months since project start", "y": "Cumulative R$ thousand", "decimal": "."},
}


def viability_figure(path: Path, lang: str = "pt") -> None:
    """Investment, sales and profit by month, in the style of the course example (Cap. 5).

    Base scenario: 1,000 cards sold evenly over the 12 months after the launch; the profit is the
    margin after variable and end-of-life costs. Dashed lines show two other volumes. ``lang`` is
    ``"pt"`` (report) or ``"en"`` (README).
    """
    text = VIABILITY_TEXT[lang]

    def decimal(value: str) -> str:
        return value.replace(".", text["decimal"])

    p = rl.load_assumptions()
    price = p["net_price_brl"]
    unit_net = price - p["variable_cost_brl"] - rl.end_of_life_unit_cost(p)
    base = pp.weekly_baseline()
    wpm = pp.WEEKS_PER_MONTH
    launch = len(base) / wpm
    horizon = launch + pp.SALES_WEEKS / wpm
    invest = pp.BUDGET / 1000
    blue, green = "#1565c0", "#2e7d32"

    def months_to_break_even(units: float) -> float:
        return launch + (pp.BUDGET / (units * unit_net / pp.SALES_WEEKS)) / wpm

    fig, ax = plt.subplots(figsize=(8.4, 5.4))
    t_inv = np.array([0, *base["week"]]) / wpm
    inv = np.array([0, *base["cumulative_brl"]]) / 1000
    ax.plot(np.append(t_inv, horizon), np.append(inv, invest), color=RED, lw=2.6)
    weeks = np.arange(pp.SALES_WEEKS + 1)
    t_sales = launch + weeks / wpm
    units = 1000
    profit = units * unit_net * weeks / pp.SALES_WEEKS / 1000
    ax.plot(t_sales, units * price * weeks / pp.SALES_WEEKS / 1000, color=green, lw=2.4)
    ax.plot(t_sales, profit, color=blue, lw=2.6)
    ax.fill_between(t_sales, invest, profit, where=profit >= invest, color=blue, alpha=0.18, hatch="||",
                    edgecolor=blue, linewidth=0)
    for other, label in zip((600, 2000), text["scenarios"]):
        line = other * unit_net * weeks / pp.SALES_WEEKS / 1000
        ax.plot(t_sales, line, color=blue, lw=1.4, ls="--", alpha=0.7)
        ax.text(horizon + 0.15, line[-1], label, color=blue, fontsize=8.5, va="center")
        t_other = months_to_break_even(other)
        if t_other <= horizon:
            ax.plot(t_other, invest, "o", color=blue, ms=4, alpha=0.7)
    t_be = months_to_break_even(units)
    ax.plot([t_be, t_be], [0, invest], color=DARK, ls=":", lw=1.2)
    ax.plot(t_be, invest, "o", color=DARK, ms=7, zorder=5)
    ax.text(t_be - 0.15, 3, text["break_even"].format(t=decimal(f"{t_be:.1f}")), fontsize=9.5, ha="right",
            color=DARK, fontweight="bold")
    ax.text(horizon + 0.15, profit[-1], text["profit"], color=blue, fontsize=8.5, va="center",
            fontweight="bold")
    ax.text(horizon + 0.15, units * price / 1000, text["sales"], color=green, fontsize=8.5,
            va="center", fontweight="bold")
    ax.text(0.15, invest + 6, text["investment"].format(v=f"{pp.BUDGET / 1000:.0f}"),
            color=RED, fontsize=9.5, fontweight="bold")
    ax.text(t_be + 2.6, invest + 6, text["gain"], color=blue, fontsize=9, style="italic")
    for (y, x0, x1), label in zip(((-17, 0, launch), (-17, launch, t_be), (-34, 0, t_be)), text["arrows"]):
        ax.annotate("", xy=(x1, y), xytext=(x0, y), arrowprops={"arrowstyle": "<->", "color": DARK, "lw": 1})
        ax.text((x0 + x1) / 2, y + 3.2, label, ha="center", fontsize=8.5, color=DARK)
    ax.axhline(0, color="black", lw=0.8)
    ax.axvline(launch, color=GREY, ls=":", lw=1)
    ax.text(launch + 0.1, 225, text["launch"], fontsize=8.5, color=GREY)
    ax.set_xlim(0, horizon + 2.6)
    ax.set_ylim(-45, 235)
    ax.set_yticks([0, 50, 100, 150, 200])
    ax.set_xticks(range(0, int(horizon) + 1, 2))
    ax.set_xlabel(text["x"])
    ax.set_ylabel(text["y"])
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


DOT_FIGURES = {
    "fig_eap.png": wbs_dot,
    "fig_blocos.png": block_diagram_dot,
    "fig_lancamento.png": launch_dependency_dot,
    "fig_rede.png": network_dot,
    "fig_organograma.png": org_chart_dot,
}


def render_all(out_dir: Path = FIG_DIR) -> dict[str, bool]:
    """Render every report figure; the value is False if Graphviz is missing."""
    out_dir.mkdir(parents=True, exist_ok=True)
    status = {name: render_png(builder(), out_dir / name) for name, builder in DOT_FIGURES.items()}
    lifecycle_figure(out_dir / "fig_ciclo_vida.png")
    gantt_scurve_figure(out_dir / "fig_gantt_curva_s.png")
    gantt_scurve_figure(out_dir / "gantt_en.png", lang="en")
    card_sketch_figure(out_dir / "fig_croqui.png")
    regional_income_figure(out_dir / "fig_renda_regional.png")
    break_even_figure(out_dir / "fig_equilibrio.png")
    viability_figure(out_dir / "fig_viabilidade.png")
    product_structure_figure(out_dir / "fig_estrutura.png")
    product_structure_figure(out_dir / "product_structure_en.png", lang="en")
    status["org_chart_en"] = render_png(org_chart_dot("en"), out_dir / "org_chart_en.png")
    status["reverse_flow_en"] = render_png(to_dot(build_flows(rl.load_assumptions(), "en")["fim_de_vida"]),
                                           out_dir / "reverse_flow_en.png")
    viability_figure(out_dir / "viability_chart_en.png", lang="en")
    return status


def main() -> None:
    """Render the report figures."""
    print(render_all())


if __name__ == "__main__":
    main()
