"""Bilingual flow specifications for the discontinuation phase (report section 6).

The report is written in Portuguese (``lang="pt"``); the README and the
``docs/workflows`` sources are in English (``lang="en"``). Both languages come
from the same structure, so they cannot drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass, field

try:
    from src import reverse_logistics_model as rl
except ImportError:  # pragma: no cover
    import reverse_logistics_model as rl


@dataclass(frozen=True)
class Node:
    ident: str
    label: str  # "\n" marks a line break
    kind: str = "process"  # start | decision | process | store | highlight | end
    lane: str = ""  # subgraph/cluster title; empty = top level


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    label: str = ""
    dashed: bool = False


@dataclass
class Flow:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    rankdir: str = "TB"  # TB (top-bottom) or LR (left-right)


def build_flows(p: dict | None = None, lang: str = "pt") -> dict[str, Flow]:
    """Build the three flows with the model's own numbers.

    ``motivo``: where can a returned card go? ``fim_de_vida``: what happens at
    end of life and where does the mass end up? ``fase``: the Chapter 12
    activity dependency diagram. One figure carries one claim.
    """
    if lang not in ("pt", "en"):
        raise ValueError("lang must be 'pt' or 'en'")
    p = p or rl.load_assumptions()

    def t(pt: str, en: str) -> str:
        return pt if lang == "pt" else en

    ref = p["return_rate_ref"]
    row = rl.mass_flows(p)
    row = row[(row["return_rate"] == ref) & (row["thickness_mm"] == p["card_thickness_mm"])].iloc[0]
    share = {k: f"{p[f'grade_{k}_share']:.0%}" for k in "abcd"}
    to_recycling = row["machining_scrap_kg"] + row["returned_grade_c_d_kg"]

    def kg(value: float) -> str:
        text = f"{value:.1f}"
        return text.replace(".", ",") if lang == "pt" else text

    lane_w, lane_d, lane_e = (t("Arrependimento", "Withdrawal"), t("Defeito ou vício", "Defect"),
                              t("Fim de vida", "End of life"))
    motivo = Flow(
        [
            Node("inicio", t("Cartão volta\nao vendedor", "Card returned\nto the seller"), "start"),
            Node("why", t("Motivo\ndo retorno?", "Reason\nfor return?"), "decision"),
            Node("r1", t("Reinspeção\n(peça sem uso)", "Re-inspection\n(unused card)"), lane=lane_w),
            Node("r2", t("Estoque", "Stock"), "store", lane_w),
            Node("d1", t("Análise de falha\nligada ao lote gravado", "Failure analysis\ntied to engraved lot"), lane=lane_d),
            Node("d2", t("Ajuste de processo\ne de inspeção", "Process and\ninspection fix"), lane=lane_d),
            Node("e1", t("Logística reversa\n(próxima figura)", "Reverse logistics\n(next diagram)"), "highlight", lane_e),
        ],
        [
            Edge("inicio", "why"),
            Edge("why", "r1", t("arrependimento\n(até 7 dias,\nCDC art. 49)", "withdrawal\n(within 7 days,\nCDC art. 49)")),
            Edge("why", "d1", t("defeito ou vício\n(garantia,\nCDC art. 26)", "defect\n(warranty,\nCDC art. 26)")),
            Edge("why", "e1", t("fim de vida\n(voluntário)", "end of life\n(voluntary)")),
            Edge("r1", "r2", t("íntegro", "intact")),
            Edge("d1", "d2", t("causa raiz", "root cause")),
        ],
    )

    fim = Flow(
        [
            Node("e1", t("Cliente pede devolução e recebe\ncódigo de postagem (a empresa\npaga, validade 30 dias)",
                         "Customer requests return and gets\npostage code (company pays,\nvalid 30 days)"), "start"),
            Node("e3", t("Recebimento: registro de lote,\ndata e massa (luvas, saco duplo)",
                         "Receipt: log lot, date and mass\n(gloves, double bag)")),
            Node("triage", t("Triagem visual\ne dimensional", "Visual and\ndimensional triage"), "highlight"),
            Node("A", t(f"A · íntegro {share['a']}\nensaio ou\nmostruário", f"A · intact {share['a']}\ntest piece or\ndisplay")),
            Node("B", t(f"B · desgaste leve {share['b']}\nsegunda vida só\nse validada",
                        f"B · light wear {share['b']}\nsecond life only\nif validated")),
            Node("C", t(f"C · delaminado {share['c']}\nvai para\nreciclagem", f"C · delaminated {share['c']}\ngoes to\nrecycling")),
            Node("D", t(f"D · fibra exposta {share['d']}\nsaco duplo,\ndestino licenciado",
                        f"D · exposed fibre {share['d']}\ndouble bag,\nlicensed disposal")),
            Node("scrap", t(f"Retalhos de usinagem\n{kg(row['machining_scrap_kg'])} kg por lote",
                            f"Machining offcuts\n{kg(row['machining_scrap_kg'])} kg per lot")),
            Node("stock", t(f"Estoque fechado por lote\naté o lote mínimo\n≈ {kg(to_recycling)} kg por lote",
                            f"Closed stock per lot\nuntil minimum lot\n≈ {kg(to_recycling)} kg per lot"), "store"),
            Node("dest", t("Destinador de compósito\n(aceite, lote mínimo e\npreço: consulta pendente)",
                           "Composite recycler\n(acceptance, minimum lot\nand price: pending)")),
            Node("voucher", t(f"Voucher de R$ {p['voucher_brl']:.0f}\n(1 por cartão validado)",
                              f"R$ {p['voucher_brl']:.0f} voucher\n(1 per validated card)")),
            Node("log", t("Registro: lote, massa,\nclasse e destino", "Record: lot, mass,\nclass and destination")),
            Node("fim", t(f"% recebido ≥ {p['return_rate_mid']:.0%}\nou {p['horizon_months']:.0f} meses:\nencerra a macrofase",
                          f"% received ≥ {p['return_rate_mid']:.0%}\nor {p['horizon_months']:.0f} months:\ncloses the phase"), "end"),
        ],
        [
            Edge("e1", "e3", t("cliente posta\no cartão", "customer ships\nthe card")),
            Edge("e3", "triage"),
            Edge("triage", "A"), Edge("triage", "B"), Edge("triage", "C"), Edge("triage", "D"),
            Edge("B", "C", t("reprovada\nem ensaio", "rejected\nin test"), dashed=True),
            Edge("C", "stock", t("cartão", "card")),
            Edge("D", "stock", t("cartão", "card"), dashed=True),
            Edge("scrap", "stock", t("retalho", "offcut")),
            Edge("stock", "dest", t("lote atingido", "minimum lot\nreached")),
            Edge("triage", "voucher", t("cartão validado", "card validated"), dashed=True),
            Edge("dest", "log", t("certificado", "certificate")),
            Edge("voucher", "log"),
            Edge("log", "fim"),
        ],
    )

    # Chapter 12, slide 6: dependency between the activities of the phase.
    fase = Flow(
        [
            Node("D1", t("D1 · Analisar e aprovar\na descontinuidade", "D1 · Analyse and approve\ndiscontinuation")),
            Node("D2", t("D2 · Planejar a\ndescontinuidade", "D2 · Plan the\ndiscontinuation")),
            Node("D3", t("D3 · Preparar o\nrecebimento", "D3 · Prepare\nproduct receipt")),
            Node("D4", t("D4 · Acompanhar o\nrecebimento", "D4 · Follow\nproduct receipt")),
            Node("D5", t("D5 · Descontinuar\na produção", "D5 · Stop\nproduction")),
            Node("D6", t("D6 · Finalizar suporte\nao produto", "D6 · End product\nsupport")),
            Node("D7", t("D7 · Avaliação geral e\nencerramento do projeto", "D7 · Overall review and\nproject closure")),
        ],
        [
            Edge("D1", "D2"), Edge("D2", "D3"), Edge("D3", "D4"),
            Edge("D2", "D5"), Edge("D5", "D6"), Edge("D2", "D6"),
            Edge("D4", "D7"), Edge("D6", "D7"),
        ],
        rankdir="LR",
    )
    return {"motivo": motivo, "fim_de_vida": fim, "fase": fase}
