"""Strategic environment analysis: SWOT matrix and Porter's five forces.

The analysis was prepared by Marco Gabriel Landivar Silva (source document
``assets/SWOT_Porter_cartao_multitool.docx``, kept out of version control like
every ``.docx``). This module holds its content as data so that the report text,
the table and both figures come from one place and cannot disagree.

Classifications and scores are team judgement, to be reviewed after the primary
research and the tests of activity A6.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "outputs" / "visualizations"

# ----------------------------------------------------------------------- SWOT
SWOT: dict[str, tuple[str, ...]] = {
    "FORÇAS": (
        "Pioneirismo em forma (formato de cartão) e material (fibra de carbono)",
        "Peça única, sem peças móveis: leve, fina e discreta",
        "Conceito escolhido por critérios objetivos, com segurança como prioridade",
        "Investimento inicial baixo e estrutura enxuta",
        "Venda digital própria, com controle da margem e da experiência",
    ),
    "FRAQUEZAS": (
        "Resistência e segurança da borda ainda não comprovadas em ensaio",
        "Dependência de fornecedores de chapa e de usinagem terceirizada",
        "Custo de fim de vida elevado em relação à reserva do projeto",
        "Pouca informação sobre preços da concorrência e sobre o público",
        "Produto não remanufaturável; reciclagem ainda incerta",
    ),
    "OPORTUNIDADES": (
        "Regiões com maior população e renda concentradas no Sudeste e no Sul",
        "Nichos EDC e ciclismo urbano sem produto equivalente em fibra de carbono",
        "Avanço do corte a frio e da fabricação sob demanda",
        "Marketplaces com tráfego já existente",
        "Logística reversa voluntária como diferencial ambiental",
    ),
    "AMEAÇAS": (
        "Marcas metálicas consolidadas, com garantias longas e reconhecimento",
        "Facilidade de imitação do produto por novos concorrentes",
        "Falhas como delaminação ou borda viva podem gerar reclamações e desgaste da marca",
        "Atrasos de fornecedores e poucas opções de destinação do resíduo no país",
        "Possíveis restrições ao porte de ferramentas em viagens aéreas",
    ),
}

# ---------------------------------------------------------------- five forces
# (force, score from 1 = very low to 5 = very high, justification)
PORTER: tuple[tuple[str, int, str], ...] = (
    ("Ameaça de novos entrantes", 4,
     "Peça única, sem peças móveis, com usinagem terceirizada e venda digital; investimento baixo "
     "(R$ 54.000) e fácil imitação."),
    ("Poder de barganha dos fornecedores", 4,
     "Chapa curada e usinagem somam 44% do custo (R$ 24.000); o corte a frio é especializado e só se "
     "conhece um reciclador de compósito curado no Brasil."),
    ("Ameaça de produtos substitutos", 4,
     "Canivetes, chaves sextavadas avulsas, multitools de bicicleta e estiletes executam as mesmas "
     "tarefas, muitas vezes a preço menor."),
    ("Rivalidade entre concorrentes", 3,
     "Marcas metálicas consolidadas (Leatherman, Victorinox, Wallet Ninja), mas sem concorrente direto "
     "em fibra de carbono no formato CR80."),
    ("Poder de barganha dos compradores", 3,
     "Cliente final pulverizado, com baixo poder individual; porém o custo de troca é nulo e os "
     "marketplaces facilitam a comparação com o preço-base de R$ 199."),
)

LEVELS = {1: "muito baixa", 2: "baixa", 3: "média", 4: "alta", 5: "muito alta"}


def porter_mean() -> float:
    """Average intensity of the five forces."""
    return sum(score for _, score, _ in PORTER) / len(PORTER)


def porter_level(mean: float) -> str:
    """Verbal reading of the mean, as used in the report text."""
    if mean >= 4.0:
        return "alta"
    if mean >= 3.5:
        return "média-alta"
    if mean >= 2.5:
        return "média"
    return "baixa"


def _decimal(value: float) -> str:
    return f"{value:.1f}".replace(".", ",")


# -------------------------------------------------------------------- figures
_QUADRANTS = {
    "FORÇAS": ("#e1edfa", "#2b78d4", (0, 1)),
    "FRAQUEZAS": ("#fbeee0", "#c8641e", (1, 1)),
    "OPORTUNIDADES": ("#e3f2e4", "#228b3c", (0, 0)),
    "AMEAÇAS": ("#f9e6e6", "#c23b3b", (1, 0)),
}


def swot_figure(path: Path | None = None) -> Path:
    """Draw the 2 x 2 SWOT matrix (internal/external by positive/negative)."""
    path = path or FIG_DIR / "fig_swot.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 7.4))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    for x, label in ((29, "Positivo"), (71, "Negativo")):
        ax.text(x, 98.2, label, ha="center", va="center", fontsize=11, fontweight="bold", color="#555555")
    for y, label in ((74, "Interno"), (25, "Externo")):
        ax.text(3.2, y, label, ha="center", va="center", fontsize=11, fontweight="bold", color="#555555",
                rotation=90)
    width, height = 42.5, 45.5
    for name, items in SWOT.items():
        face, edge, (col, row) = _QUADRANTS[name]
        x0 = 8 + col * (width + 1.5)
        y0 = 3 + row * (height + 1.5)
        ax.add_patch(FancyBboxPatch((x0, y0), width, height, boxstyle="round,pad=0,rounding_size=1.2",
                                    facecolor=face, edgecolor="none"))
        ax.add_patch(plt.Rectangle((x0, y0 + height - 0.9), width, 0.9, facecolor=edge, edgecolor="none"))
        ax.text(x0 + 2.4, y0 + height - 5.5, name, fontsize=13, fontweight="bold", va="center", color="#111111")
        y = y0 + height - 10.0
        for item in items:
            lines = textwrap.wrap(item, 42)
            ax.text(x0 + 2.4, y, "•", fontsize=10, va="center", color=edge)
            for k, line in enumerate(lines):
                ax.text(x0 + 4.6, y - k * 2.4, line, fontsize=9, va="center", color="#222222")
            y -= 2.4 * len(lines) + 2.6
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def porter_figure(path: Path | None = None) -> Path:
    """Horizontal bars with the intensity of each force and the mean as a reference line."""
    path = path or FIG_DIR / "fig_porter.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 3.9))
    names = [name for name, _, _ in PORTER][::-1]
    scores = [score for _, score, _ in PORTER][::-1]
    ax.barh(names, scores, color="#2b78d4", height=0.55)
    mean = porter_mean()
    ax.axvline(mean, color="#444444", linestyle="--", linewidth=1.6)
    ax.text(mean, len(PORTER) - 0.38, f"Média: {_decimal(mean)}", ha="center", va="bottom", fontsize=10,
            color="#444444")
    for i, score in enumerate(scores):
        ax.text(4.3, i, f"{score} ({LEVELS[score]})", va="center", fontsize=10)  # aligned, clear of the bars
    ax.set_xlim(0, 5.6)
    ax.set_xticks(range(1, 6))
    ax.set_xticklabels([f"{k}\n{LEVELS[k]}" for k in range(1, 6)], fontsize=9, color="#444444")
    ax.set_xlabel("Intensidade da força (escala de 1 a 5)", fontsize=10, color="#444444")
    ax.grid(axis="x", color="#e3e3e3")
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.tick_params(axis="y", length=0, labelsize=10)
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def render_all() -> list[Path]:
    """Both figures used by the report."""
    return [swot_figure(), porter_figure()]


if __name__ == "__main__":
    for written in render_all():
        print(f"Figure written to: {written}")
