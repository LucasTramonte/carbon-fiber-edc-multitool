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
    from src.reverse_flow_diagram import render_png
except ImportError:  # pragma: no cover
    import project_plan as pp
    from reverse_flow_diagram import render_png

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
    lines = ["digraph wbs {", "  rankdir=LR;", "  " + HEAD,
             f'  P [label="{_q("Cartão multitool\nvalidado e lançado\nem piloto")}", fillcolor="{DARK}", fontcolor=white];']
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


def product_structure_dot() -> str:
    """Cap. 8 style tree: fabricated items in red, purchased items in black."""
    fab = f'fontcolor="{RED}"'
    return f"""digraph estrutura {{
  rankdir=LR;
  {HEAD}
  P [label="Cartão multitool", fillcolor="{DARK}", fontcolor=white];
  S1 [label="S1 Corpo", fillcolor="{LIGHT}"];
  S2 [label="S2 Funções", fillcolor="{LIGHT}"];
  S3 [label="S3 Embalagem", fillcolor="{LIGHT}"];
  C1 [label="P1 Chapa curada (CFRP)"];
  C2 [label="P2 Cartão recortado\\ne usinado", {fab}];
  C3 [label="P3 Chanfro e acabamento", {fab}];
  C4 [label="P4 Hexágonos e recortes", {fab}];
  C5 [label="P5 Escala gravada", {fab}];
  C6 [label="P6 Gravação de lote", {fab}];
  C7 [label="P7 Envelope ou berço"];
  C8 [label="P8 Caixa externa"];
  C9 [label="P9 Manual e etiqueta"];
  P -> S1; P -> S2; P -> S3;
  S1 -> C1; S1 -> C2; S1 -> C3;
  S2 -> C4; S2 -> C5; S2 -> C6;
  S3 -> C7; S3 -> C8; S3 -> C9;
  L [shape=plaintext, style="", fontsize=11, label=<<table border="0" cellborder="0"><tr><td><font color="{RED}">vermelho: fabricado</font></td></tr><tr><td>preto: comprado</td></tr></table>>];
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


def gantt_scurve_figure(path: Path) -> None:
    """Cumulative cost (S-curve) above a Gantt, as in the cost-management lesson."""
    sched, base = pp.schedule(), pp.weekly_baseline()
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(10, 6.6), sharex=True,
                                      gridspec_kw={"height_ratios": [1, 1.7]})
    top.plot(base["week"], base["cumulative_brl"] / 1000, color=DARK, marker="o", ms=4)
    top.bar(base["week"], base["cost_brl"] / 1000, color=GREY, alpha=0.6, width=0.6)
    top.axhline(pp.BUDGET / 1000, color=ORANGE, ls="--", lw=1)
    top.set_ylim(0, 62)
    top.text(0.7, pp.BUDGET / 1000 + 2.2, "orçamento: R$ 54 mil", color=ORANGE, fontsize=9)
    top.set_ylabel("Custo (R$ mil)\nacumulado e semanal", fontsize=9)
    top.set_title("Cronograma-base e curva S", fontsize=11)
    y = np.arange(len(sched))
    colors = [DARK if c else GREY for c in sched["critical"]]
    bottom.barh(y, sched["duration_weeks"], left=sched["start_week"] - 0.5, color=colors,
                edgecolor=DARK, height=0.6)
    bottom.set_yticks(y, [f"{r.id} · {r.activity}" for r in sched.itertuples()], fontsize=8)
    bottom.invert_yaxis()
    bottom.set_xticks(range(1, 15))
    bottom.set_xlim(0.5, 14.5)
    bottom.set_xlabel("Semana do projeto (S1 a S14)", fontsize=9)
    bottom.grid(axis="x", alpha=0.3)
    handles = [plt.Rectangle((0, 0), 1, 1, fc=DARK), plt.Rectangle((0, 0), 1, 1, fc=GREY)]
    bottom.legend(handles, ["Caminho crítico", "Atividade com folga (A4: 1 semana)"],
                  loc="upper right", fontsize=8)
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


DOT_FIGURES = {
    "fig_eap.png": wbs_dot,
    "fig_blocos.png": block_diagram_dot,
    "fig_estrutura.png": product_structure_dot,
    "fig_lancamento.png": launch_dependency_dot,
    "fig_rede.png": network_dot,
}


def render_all(out_dir: Path = FIG_DIR) -> dict[str, bool]:
    """Render every report figure; the value is False if Graphviz is missing."""
    out_dir.mkdir(parents=True, exist_ok=True)
    status = {name: render_png(builder(), out_dir / name) for name, builder in DOT_FIGURES.items()}
    lifecycle_figure(out_dir / "fig_ciclo_vida.png")
    gantt_scurve_figure(out_dir / "fig_gantt_curva_s.png")
    card_sketch_figure(out_dir / "fig_croqui.png")
    regional_income_figure(out_dir / "fig_renda_regional.png")
    break_even_figure(out_dir / "fig_equilibrio.png")
    return status


def main() -> None:
    """Render the report figures."""
    print(render_all())


if __name__ == "__main__":
    main()
