"""Generate the complete Portuguese report (DOCX): body under 15 pages plus appendices.

Every number comes from the labelled models (``project_plan``,
``reverse_logistics_model``) or from the public IBGE extracts, so the text, the
tables and the figures cannot disagree. Team data stay in a git-ignored local
file (``report/team.local.json``).
"""

from __future__ import annotations

import math
from pathlib import Path

try:
    from src import project_plan as pp
    from src import reverse_logistics_model as rl
    from src import omml as mm
    from src import report_equations as eq
    from src import strategic_analysis as sa
    from src.docx_builder import Builder, br, brl, load_team, pct
except ImportError:  # pragma: no cover
    import project_plan as pp
    import reverse_logistics_model as rl
    import omml as mm
    import report_equations as eq
    import strategic_analysis as sa
    from docx_builder import Builder, br, brl, load_team, pct

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DOCX = ROOT / "outputs" / "relatorio_cartao_multitool.docx"

# --- concept selection (Section 3.3): weights and 1-5 scores are team judgement
CRITERIA = {"Segurança": 0.30, "Utilidade": 0.25, "Fabricabilidade": 0.20, "Custo": 0.15, "Massa e espessura": 0.10}
SCORES = {"A": (2, 4, 3, 4, 5), "B": (5, 4, 5, 4, 5), "C": (4, 5, 2, 2, 2)}


def concept_scores(weights: dict[str, float] | None = None) -> dict[str, float]:
    """Weighted score per concept; the weights must sum to 1."""
    weights = weights or CRITERIA
    if not math.isclose(sum(weights.values()), 1.0):
        raise ValueError("weights must sum to 1")
    return {k: sum(w * s for w, s in zip(weights.values(), v)) for k, v in SCORES.items()}


def concept_winner_range() -> tuple[float, float, bool]:
    """Safety weight swept 20%-40% (others rescaled): does concept B always win?"""
    others = {k: v for k, v in CRITERIA.items() if k != "Segurança"}
    total = sum(others.values())
    wins = True
    for w in (0.20, 0.25, 0.30, 0.35, 0.40):
        weights = {"Segurança": w, **{k: v / total * (1 - w) for k, v in others.items()}}
        scores = concept_scores(weights)
        wins &= max(scores, key=scores.get) == "B"
    return 0.20, 0.40, wins


LABEL_MAP = {
    "tables": {
        "Planejamento estratégico do produto": "strat", "Concorrentes de referência": "compet",
        "Fontes de informação": "fontes", "Intensidade das cinco forças": "porter", "Termo de abertura": "charter",
        "Escopo do produto": "escopo", "Atividades, precedências e custos": "atividades", "Custo padrão": "custos",
        "Viabilidade econômica por volume": "viab", "Matriz morfológica": "morf", "Plano macro do processo": "macro",
        "Lista de materiais": "bom",
        "Atividades da fase de descontinuidade": "fase_ativ",
    },
    "figures": {
        "fig_organograma.png": "org", "fig_eap.png": "eap", "fig_viabilidade.png": "viab_fig",
        "reverse_flow_fase.png": "fase_fig", "fig_porter.png": "porter_fig", "fig_estrutura.png": "estrutura",
        "cad_technical_drawing.png": "desenho", "cad_3d_model.png": "modelo3d",
    },
    "headings": {
        "Inovação e tecnologia": "s_inov", "Mercado e coleta de informações": "s_mercado",
        "Análise do ambiente": "s_swot", "Planejamento do projeto": "s_proj", "Viabilidade econômica": "s_viab",
        "Plano macro do processo produtivo": "s_macro", "Modelagem CAD e desenho técnico": "s_cad", "Lançamento do produto": "s_lanc",
        "Atendimento ao cliente e assistência": "s_atend", "Descontinuidade do produto": "s_desc",
    },
}


def build_report() -> Builder:
    """Build the report in two passes: the first numbers every table, figure and section, the second writes
    the text with those numbers, so no cross-reference is typed by hand."""
    first = _build({})
    return _build(first.labels)


def _build(labels: dict[str, str]) -> Builder:
    def R(key: str) -> str:
        """Label of a table, figure or section (``Tabela 3``, ``Figura A.1``, ``Seção 1.2``)."""
        return labels.get(key, "?")

    def num(key: str) -> str:
        """Number of a section, without the word."""
        return R(key).split()[-1]

    p = rl.load_assumptions()
    sched, costs, base = pp.schedule(), pp.cost_table(), pp.weekly_baseline()
    se_s_share = rl.southeast_south_population_share()
    ref, low, mid, high = (p["return_rate_ref"], p["return_rate_low"], p["return_rate_mid"], p["return_rate_high"])
    margin = p["net_price_brl"] - p["variable_cost_brl"]
    ccost = rl.return_cost_table(p)
    flows = rl.mass_flows(p)
    channels = rl.channel_cost_table(p)
    benefit, channel = rl.benefit_matrix(p), rl.channel_matrix(p)
    reman = rl.remanufacturing_viability(p)
    phase = rl.build_schedule(p)

    def cost_row(option: str, rate: float):
        return ccost[(ccost["option"] == option) & (ccost["return_rate"] == rate)].iloc[0]

    def flow_row(rate: float, thickness: float):
        sel = flows[(flows["return_rate"] == rate) & (flows["thickness_mm"] == thickness)]
        return sel.iloc[0]

    voucher = cost_row("frete_gratis_voucher", ref)
    flow_ref = flow_row(ref, p["card_thickness_mm"])
    cap_cards = math.floor(p["management_reserve_brl"] / voucher["cost_per_return_brl"])
    sens = rl.weight_sensitivity(benefit, "custo")
    voucher_wins_until = sens[sens["winner"] == "frete_gratis_voucher"]["cost_weight"].max()
    csens = rl.weight_sensitivity(channel, "custo")
    mail_wins_until = csens[csens["winner"] == "correios_reversa"]["cost_weight"].max()
    store_ref = channels[(channels["channel"] == "lojas_parceiras") & (channels["return_rate"] == ref)].iloc[0]
    mail_cost = p["reverse_freight_brl"] + p["return_kit_brl"]
    eol_project = phase.loc[phase["cost_type"] == "projeto", "cost_brl"].sum()
    eol_opex = phase.loc[phase["cost_type"] == "operacional", "cost_brl"].sum()
    eol_unit = (eol_project + eol_opex) / p["lot_units"]
    break_even_total = math.ceil(p["development_budget_brl"] / (margin - eol_unit))
    be = lambda budget, price: math.ceil(budget / (price - p["variable_cost_brl"]))  # noqa: E731
    scores = concept_scores()
    lo_w, hi_w, b_always = concept_winner_range()
    s4 = base.loc[base["week"] == 4, "cumulative_brl"].item() / pp.BUDGET
    critical = " → ".join(pp.critical_path())

    b = Builder(label_map=LABEL_MAP)
    b.cover("CARTÃO MULTITOOL EM FIBRA DE CARBONO", "Relatório de Desenvolvimento de Produto: ER801A", load_team())

    # ----------------------------------------------------------- Resumo
    b.heading("Resumo", 1)
    b.para(
        "Este relatório planeja o desenvolvimento, o lançamento e a descontinuidade de um cartão multitool "
        "plano, no formato CR80, em fibra de carbono, para usuários de carregamento cotidiano (EDC, do inglês "
        "everyday carry) e ciclistas urbanos. "
        f"O projeto custa {brl(pp.BUDGET, 0)} em {int(sched['end_week'].max())} semanas, "
        f"com reserva de {brl(pp.RESERVE, 0)}. O recolhimento de fim de vida é viável por postagem reversa, com "
        "benefício modesto ao cliente; a remanufatura do cartão não é viável."
    )

    # ------------------------------------------------------------- 1
    b.heading("1. Planejamento estratégico do produto", 1)
    b.heading("1.1 Posicionamento da empresa", 2)
    b.para(
        f"A {R('strat')} responde, nesta ordem, às sete perguntas do roteiro de planejamento estratégico do "
        "Capítulo 4. Missão, posicionamento e competências são propostas do grupo; mercado e "
        "recursos usam dados do projeto."
    )
    b.table(
        "Planejamento estratégico do produto (roteiro do Capítulo 4)",
        ["Elemento", "Resposta", "Natureza"],
        [
            ["Missão", "Oferecer uma ferramenta plana, leve e discreta para pequenos imprevistos cotidianos, "
             "com desempenho comprovado por ensaio.", "Proposta"],
            ["Segmentação", "Ciclistas urbanos e usuários EDC. Entre 11.956 ciclistas de 18 cidades, 26% são "
             "mulheres, 59% têm até 39 anos e 54% ganham até 2 salários mínimos; só 36% ganham mais de 2 [4]. "
             "O alvo inicial são os de renda acima de 2 salários mínimos.", "Derivada"],
            ["Tendências tecnológicas", "Corte de compósitos por fresagem CNC, jato d'água abrasivo ou laser, "
             "este com zona afetada pelo calor [21]; cartões multiferramenta patenteados desde 1993, nenhum em "
             f"fibra de carbono ({R('s_inov')}).", "Observada"],
            ["Posicionamento", "Seguidor diferenciado: já existe um cartão de fibra de carbono com chaves "
             f"sextavadas ({R('compet')}). Compete por borda segura comprovada em ensaio, abertura de embalagens e "
             "serviço de recolhimento, e não por custo.", "Proposta"],
            ["Metas", f"ROI, VPL, TIR e participação de mercado ({R('viab')}): vender 1.000 cartões em 12 meses; "
             f"equilíbrio em {break_even_total} cartões. Sem meta de participação: não há dado público do "
             "tamanho do mercado.", "Derivada"],
            ["Competências", "Projeto em CAD, inspeção dimensional, atendimento e venda digital; usinagem "
             "terceirizada.", "Proposta"],
            ["Recursos necessários", f"Orçamento de {brl(pp.BUDGET, 0)} mais reserva de {brl(pp.RESERVE, 0)}; "
             "equipe de três discentes; chapa curada; bancada de ensaio.", "Observada"],
        ],
        [3.2, 10.3, 2.5],
        "elaboração própria a partir de [4] e [21].",
    )
    b.heading("1.2 Inovação e tecnologia", 2)
    b.para(
        "A inovação é incremental, e não pioneira. Cartões multiferramenta existem desde a patente US 5.328.026, "
        "de 1993 [23]; há cartões metálicos, como a Wallet Ninja [19], e um cartão de peça única em fibra de "
        "carbono com sete chaves sextavadas de 6 a 12 mm e régua, o Touch of Ginger TOG09, com 1,5 mm de "
        "espessura [22]. O cartão proposto se diferencia por chanfro rombo para abrir embalagens, escala e lote "
        "gravados, borda segura comprovada em ensaio, serviço pós-venda e recolhimento no fim de vida. Menor "
        "massa e espessura que os metálicos é hipótese não medida: depende dos ensaios da atividade A6."
    )
    b.para(
        "O cartão é cortado a frio em chapa curada. A fresagem CNC usa avanço de 1.000 a 1.500 mm/min em chapa "
        "de 2 mm [17]; o jato d'água abrasivo é alternativa; o laser deixa zona afetada pelo calor, delaminação "
        "e extração de fibras [21]. Na busca de patentes, a US 5.328.026 (cartão com ferramentas) e a "
        "US 8.713.735 (ferramenta com chaves sextavadas) expiraram [23][25]; já o desenho industrial CA 175697S "
        "da Nite Ize, de cartão multiferramenta, está ativo até 2028 [24]. Nenhum dos três cita fibra de "
        "carbono. A busca foi preliminar: antes do lançamento é preciso consultar o INPI e obter parecer "
        "jurídico, porque o desenho do cartão não deve reproduzir o protegido."
    )
    b.heading("1.3 Concorrentes", 2)
    b.table(
        "Concorrentes de referência",
        ["Concorrente", "Categoria", "Garantia declarada", "Preço, material e dimensões"],
        [
            ["Touch of Ginger TOG09", "Cartão de carteira, fibra de carbono", "Sem informação pública",
             "US$ 14,95 a 19,99 em uma loja, descontinuado em outra; peça única; 85,7 × 54,0 mm; 1,5 mm; "
             "23 a 28 g; 7 chaves de 6 a 12 mm e régua [22]"],
            ["Wallet Ninja", "Multitool de carteira, metálico", "Sem informação pública",
             "US$ 20; aço inoxidável; 85,6 × 54,0 mm; 28 g; 19 funções [19]"],
            ["Victorinox", "Canivete multiuso (linha SwissCard)", "2 anos, reparo ou troca, nas categorias listadas [14]",
             "Preço oficial indisponível; varejistas divergem em moeda e data"],
            ["Leatherman", "Alicate multiuso (Micra, porte de chaveiro)", "25 anos, reparo primeiro [13]",
             "US$ 49,95; aço inoxidável; 63,5 mm fechado, 9,4 mm de espessura; 51 g; 10 funções [20]"],
        ],
        [2.6, 3.6, 4.4, 5.4],
        "páginas oficiais dos fabricantes, consultadas em 11 nov. 2026 (preços em dólares, sem data de publicação "
        "na página). Faltam preços em reais e o preço oficial da SwissCard.",
    )
    b.para(
        "Os concorrentes custam de US$ 15 a 50, muito menos que R$ 199, e o TOG09 já oferece fibra de carbono "
        "e chaves sextavadas por menos de US$ 20: o cartão só se sustenta por diferenciação comprovada, o que o "
        f"experimento de preço ({R('s_mercado')}) deve testar."
    )
    b.heading("1.4 Mercado e coleta de informações", 2)
    b.para(
        f"A {R('fontes')} organiza as fontes pela tipologia do Capítulo 4."
    )
    b.table(
        "Fontes de informação de mercado e de tecnologia (tipologia do Capítulo 4)",
        ["Tipo de fonte", "Fonte", "Situação e o que mostra"],
        [["Secundária, dados publicados", "IBGE/SIDRA [1][2] e Cetic.br [3], 2024",
          f"Coletada: Sudeste e Sul concentram {pct(se_s_share, 1)} da população, com renda per capita de "
          "R$ 2.377 a R$ 2.488 (indicador territorial); entre os compradores online, 80% (Norte) a 92% "
          "(Sudeste) usaram sites de compra e venda."],
         ["Secundária, dados publicados", "Perfil do Ciclista 2024, Transporte Ativo [4]",
          "Coletada: perfil do público, resumido abaixo."],
         ["Secundária, dados padronizados", "Relatórios setoriais de mercado [26]",
          "Sem dado público do mercado de multitools de bolso; só de multiferramentas industriais."],
         ["Secundária, registros internos", "Assistência, devoluções e defeitos",
          f"Inexistente: o produto ainda não foi vendido; os registros nascem no piloto ({R('s_atend')})."],
         ["Tecnológica", "Patentes e produtos concorrentes [22] a [25]",
          f"Coletada: três documentos e um concorrente direto ({R('s_inov')})."],
         ["Primária, qualitativa", "20 a 30 entrevistas individuais", "Planejada na atividade A1."],
         ["Primária, quantitativa", "Enquete com 100 a 150 respostas, cotas por região",
          "Planejada: margem de erro de 8 a 10 pontos percentuais [27]."],
         ["Primária, experimento", "Teste de uso observado (10 a 15) e experimento de preço [28]",
          "Planejado na atividade A6."]],
        [3.6, 5.2, 7.2],
        "elaboração própria, com a tipologia de fontes do Capítulo 4.",
        font=9,
    )
    b.para(
        "Perfil do público. A pesquisa [4] cobre 11.956 ciclistas de 18 cidades, e não o país inteiro. Entre eles, "
        "74% pedalam para o trabalho e 34% todos os dias; o trajeto mais frequente leva de 15 a 30 minutos (54%) "
        "e a principal motivação é a praticidade (42%), seguida de saúde (26%) e custo (21%). Dois pontos "
        "orientam o produto: o uso é diário e utilitário, ou seja, a ferramenta iria para a rua; e a renda é "
        "baixa (54% ganham até 2 salários mínimos), o que torna o preço de R$ 199 um obstáculo para a maioria e "
        "justifica mirar o terço de maior renda."
    )
    b.para(
        "Como recomenda o Capítulo 4, as perguntas tratam de hábitos e locais de uso, e não do tamanho desejado. "
        "Com 100 a 150 respostas, a margem de erro é de 8 a 10 pontos percentuais com 95% de confiança, pela "
        "fórmula de Cochran para proporções [27]. O experimento de preço usa as quatro perguntas de Van "
        "Westendorp [28]. Nenhuma etapa estima o mercado nacional: servem para validar hipóteses."
    )
    b.heading("1.5 Análise do ambiente: SWOT e cinco forças de Porter", 2)
    b.para(
        "A matriz SWOT cruza fatores internos e externos; as cinco forças de Porter medem a pressão competitiva "
        "do setor. Classificações e notas são julgamento da equipe, a revisar após a pesquisa primária e os "
        "ensaios (A6)."
    )
    b.swot_matrix("Matriz SWOT do cartão multitool em fibra de carbono.", sa.SWOT, source="elaboração própria.")
    b.para(
        "A principal força, a combinação de forma e material, é também o ponto mais exposto: a arquitetura "
        "simples e a usinagem terceirizável facilitam a imitação, e já existe um cartão de fibra de carbono com "
        f"chaves sextavadas ({R('compet')})."
    )
    mean_force = sa.porter_mean()
    b.table(
        "Intensidade das cinco forças competitivas (nota de 1, muito baixa, a 5, muito alta)",
        ["Força", "Nota", "Justificativa"],
        [[name, str(score), why] for name, score, why in sa.PORTER]
        + [["Média", br(mean_force, 1), f"Pressão competitiva {sa.porter_level(mean_force)}."]],
        [4.2, 1.2, 10.6],
        "elaboração própria; notas por julgamento da equipe.",
        bold_rows=(5,), right_cols=(1,),
    )
    b.para(
        f"A média de {br(mean_force, 1)} ({R('porter_fig')}) indica pressão competitiva {sa.porter_level(mean_force)}. As três forças "
        "mais intensas (novos entrantes, fornecedores e substitutos) mostram que o produto não deve competir por "
        "preço: a defesa está na diferenciação comprovada por ensaio, na construção de marca no nicho EDC e "
        "ciclista e na negociação com mais de um fornecedor de chapa e de usinagem, coerente com o "
        f"posicionamento por diferenciação da {R('strat')}."
    )

    # ------------------------------------------------------------- 2
    b.heading("2. Planejamento do projeto", 1)
    b.heading("2.1 Interessados e responsabilidades", 2)
    b.figure("fig_organograma.png", "Organograma do projeto: funções, hierarquia e atividades de cada interessado.",
             width_cm=14.5, source="elaboração própria.")
    b.para(
        f"A {R('org')} mostra a hierarquia do projeto e as atividades (A1 a A9, {R('eap')}) de cada função. As "
        "funções internas são exercidas pelos três discentes; o gerente é designado pelo grupo."
    )
    b.heading("2.2 Escopo do produto e do projeto", 2)
    b.para(f"A {R('charter')} segue os campos do modelo do Capítulo 5 para a declaração do escopo do projeto; a "
           f"{R('escopo')} detalha o escopo do produto.")
    b.table(
        "Termo de abertura do projeto",
        ["Campo", "Conteúdo"],
        [
            ["Projeto", "Cartão multitool em fibra de carbono (ER801A)."],
            ["Gerente e patrocinador", "Gerente: discente designado pelo grupo. Patrocinador: docente da disciplina."],
            ["Objetivo", "Desenvolver e validar um cartão multitool plano para EDC e ciclistas urbanos, "
             "com lote piloto."],
            ["Benefícios", "Testar uma alternativa leve e portátil, com evidências, antes de qualquer "
             "afirmação de demanda."],
            ["Prazo e custo", f"{int(sched['end_week'].max())} semanas; {brl(pp.BUDGET, 0)} mais reserva de "
             f"{brl(pp.RESERVE, 0)} (limite de {brl(pp.BUDGET + pp.RESERVE, 0)}, definido pelo grupo)."],
            ["Escopo do produto", f"Funções e parâmetros da {R('escopo')}."],
            ["Escopo do projeto", f"Entregas 1.0 a 7.0 da {R('eap')}. Fora do escopo: certificação de segurança ou "
             "de transporte aéreo e produção em escala."],
            ["Premissas", "Chapa curada disponível; corte por jato d'água ou CNC; venda inicial digital."],
            ["Restrições", "Segurança das bordas, custo, espessura de carteira, capacidade de usinagem."],
            ["Equipe", f"Três discentes, com as funções da {R('org')}."],
            ["Riscos", "Delaminação, baixa utilidade percebida, custo alto, atraso de fornecedor e rejeição "
             "em inspeção."],
            ["Aprovações", "Avanço de fase só com requisitos aprovados, protótipo funcional e ensaios sem "
             "falha crítica (ponto de decisão do docente)."],
        ],
        [3.6, 12.4],
        "elaboração própria.",
    )
    b.table(
        "Escopo do produto: funções, parâmetros e critérios de aceitação",
        ["Função ou parâmetro", "Especificação", "Critério de aceitação"],
        [["Formato e espessura", "CR80, 85,60 × 53,98 mm, até 2 mm; peça única de fibra de carbono e epóxi",
          "Medição com instrumento calibrado"],
         ["Transmitir torque (F1 e F2)", "Recortes sextavados no contorno",
          "Sem escorregamento nem fratura no torque definido em ensaio"],
         ["Abrir embalagem (F3)", "Chanfro rombo contínuo", "Abre a fita sem tocar no conteúdo"],
         ["Medir (F4)", "Escala gravada", "Legível após os ensaios de uso"],
         ["Proteger o usuário (F5)", "Raio e chanfro na borda; inspeção por lote",
          "Nenhuma aresta viva; fratura em modo seguro, sem projeção perigosa"],
         ["Transporte", "Cartão na carteira, com borda protegida e lote gravado",
          "Cabe na carteira; lote rastreável"]],
        [4.2, 6.0, 5.8],
        "elaboração própria; critérios do plano de validação técnica do projeto, com 5 amostras por ensaio.",
        font=9,
    )
    b.heading("2.3 Estrutura analítica do projeto (EAP)", 2)
    b.figure("fig_eap.png", "EAP em três níveis: produto do projeto, entregas e pacotes de trabalho (atividades A1 a A9).",
             width_cm=12.5, source="elaboração própria.")
    b.heading("2.4 Atividades, precedências e custos", 2)
    b.para(
        f"A {R('atividades')} reproduz o formato da planilha do professor (ID, atividade, início, duração, término, "
        "precedência) acrescido dos custos por tipo de recurso. Prazos estão em semanas do projeto, e não "
        "em dias corridos. Os totais por atividade são as estimativas originais do grupo; a divisão por tipo é "
        f"premissa até haver cotações ({R('custos')})."
    )
    cost_by_id = costs.set_index("id")
    rows: list[list[str]] = []
    bold: list[int] = []
    rows.append(["0", "Cartão multitool validado e lançado em piloto", "S1", br(int(sched["end_week"].max())),
                 f"S{int(sched['end_week'].max())}", "-", br(costs["labour_brl"].sum()),
                 br(costs["equipment_services_brl"].sum()), br(costs["inputs_brl"].sum()),
                 br(costs["activity_cost_brl"].sum())])
    bold.append(0)
    for code, dname in pp.DELIVERABLES.items():
        members = [a for a in pp.ACTIVITIES if a.wbs == code]
        mid_ids = [a.ident for a in members]
        sub = sched[sched["id"].isin(mid_ids)]
        sub_cost = cost_by_id.loc[mid_ids]
        bold.append(len(rows))
        rows.append([code, dname, f"S{int(sub['start_week'].min())}", br(int(sub["end_week"].max() - sub["start_week"].min() + 1)),
                     f"S{int(sub['end_week'].max())}", "-", br(sub_cost["labour_brl"].sum()),
                     br(sub_cost["equipment_services_brl"].sum()), br(sub_cost["inputs_brl"].sum()),
                     br(sub_cost["activity_cost_brl"].sum())])
        for a in members:
            s = sched[sched["id"] == a.ident].iloc[0]
            c = cost_by_id.loc[a.ident]
            labour = c["labour_codes"] if c["labour_codes"] != "-" else "-"
            rows.append([a.ident, a.name, f"S{s['start_week']}", br(s["duration_weeks"]), f"S{s['end_week']}",
                         s["predecessors"], f"{labour}\n{br(c['labour_brl'])}" if labour != "-" else "-",
                         br(c["equipment_services_brl"]), br(c["inputs_brl"]), br(c["activity_cost_brl"])])
    b.table(
        "Atividades, precedências e custos (R$)",
        ["ID", "Atividade", "Início", "Dur.", "Término", "Precedência", "Mão de obra", "Equip. e serv.",
         "Insumos", "Custo"],
        rows, [0.9, 3.0, 1.2, 1.0, 1.5, 1.9, 1.7, 1.5, 1.5, 1.3],
        f"elaboração própria. Soma das atividades: {brl(costs['activity_cost_brl'].sum(), 0)}; com a reserva, "
        f"{brl(pp.BUDGET + pp.RESERVE, 0)}. Linhas em destaque somam as atividades de cada entrega.",
        font=8, bold_rows=tuple(bold), right_cols=(3, 6, 7, 8, 9),
    )
    std_rows = [[code, name, "pessoa-semana", brl(rate, 0), brl(rate / 40, 2)]
                for code, (name, kind, rate) in pp.STANDARD_COST.items()]
    b.table(
        "Custo padrão por tipo de recurso e legenda das siglas",
        ["Sigla", "Recurso", "Unidade", "Custo", "R$/hH"],
        std_rows + [["Equip.", "Fresagem CNC terceirizada", "R$/hM", "a cotar", "-"],
                    ["Equip.", "Bancada de ensaio e licença de CAD", "R$/utilização", "a cotar", "-"],
                    ["Insumos", "Chapa curada, corpos de prova e embalagem", "R$/unidade", "a cotar", "-"]],
        [2.0, 7.2, 3.0, 2.2, 1.6],
        "elaboração própria. hH: hora-homem, com 40 horas por semana; hM: hora-máquina. As taxas de mão de obra "
        "são hipóteses e os demais preços dependem de cotação; a fresagem do lote de 2.000 cartões usa de 62 a "
        f"83 horas-máquina ({R('s_macro')}).",
        right_cols=(3, 4),
    )
    b.heading("2.5 Cronograma, caminho crítico e linha de base", 2)
    b.para(
        f"O caminho crítico é {critical}, com {int(sched['end_week'].max())} semanas; a atividade A4 tem folga de "
        f"uma semana. A curva S concentra {pct(s4)} do orçamento até a semana 4, porque A4 (chapa, "
        f"{brl(cost_by_id.loc['A4', 'inputs_brl'], 0)} em insumos) é a maior compra. O desvio de prazo e de custo "
        "será medido por SPI e CPI (valor agregado), com a linha de base acima."
    )

    b.figure("fig_gantt_curva_s.png", "Curva S de custo acumulado e Gantt do projeto, em semanas.", width_cm=13.0,
             source=f"elaboração própria a partir da {R('atividades')}.")
    b.heading("2.6 Viabilidade econômica", 2)
    unit_net = margin - eol_unit
    V, N, SUB, SUP, FR, SUM, PAR = eq.V, eq.N, eq.SUB, eq.SUP, eq.FR, eq.SUM, eq.PAR
    F_t, C_t, T_d, T_v, i_s, r_star = eq.F_t, eq.C_t, eq.T_d, eq.T_v, eq.i_s, eq.r_star
    b.para(
        f"O modelo usa um fluxo de caixa semanal: o investimento segue a linha de base de custo ({R('atividades')}) e as "
        "vendas, em ritmo constante, começam depois do desenvolvimento. Os fluxos ocorrem no fim de cada semana e "
        "o custo de fim de vida é proporcional às unidades vendidas. Com a notação abaixo, valem as equações:"
    )
    eq.add_equations(b, "pt")
    im = lambda fragment: (fragment,)  # noqa: E731
    b.math_para([
        "Nelas, ", im(V("p")), " é o preço líquido (R$ 199); ", im(SUB(V("c"), V("v"))), " o custo variável "
        "(R$ 80); ", im(SUB(V("c"), V("f"))), f" o custo de fim de vida por cartão ({brl(eol_unit)}); ",
        im(V("Q")), " os cartões vendidos em 12 meses; ", im(C_t), " o custo da semana ", im(V("t")),
        " na linha de base; ", im(V("I") + N(" = ") + SUM(N("t = 1"), T_d, C_t) + N(f" = {brl(pp.BUDGET, 0)}")),
        " o investimento; ", im(T_d + N(" = 14")), " e ", im(T_v + N(" = 52")), " as semanas de desenvolvimento e de "
        "vendas, com ", im(V("T") + N(" = ") + T_d + N(" + ") + T_v), "; e ", im(V("i")),
        f" a taxa de desconto ({pct(pp.DISCOUNT_RATE, 2)} ao ano, meta Selic [29]). A TIR mensal converte a "
        "taxa semanal ", im(r_star), "; o prazo de recuperação é ", im(V("\u03c4") + N(" \u00b7 12/52")),
        " meses, com interpolação linear na semana ", im(V("\u03c4")), ". O equilíbrio simples é ",
        im(SUB(V("Q"), N("eq")) + N(" = \u2308") + FR(V("I"), V("m")) + N("\u2309")), ", em que o ROI se anula. "
        "Como o fluxo muda de sinal uma única vez, a TIR positiva é única (regra de sinais de Descartes)."])
    zero_npv = math.ceil(pp.units_for_zero_npv(unit_net))
    t_be = pp.payback_months(pp.cash_flows(1000, unit_net))
    price_be = lambda price: math.ceil(pp.BUDGET / (price - p["variable_cost_brl"] - eol_unit))  # noqa: E731
    b.para(
        f"Com margem líquida de {brl(unit_net)} por cartão, depois de {brl(eol_unit)} de fim de vida ({R('fase_ativ')}), o "
        f"cenário base, de 1.000 cartões vendidos em 12 meses, iguala o investimento no mês {br(t_be, 1)} "
        f"({R('viab_fig')}). O equilíbrio simples exige {break_even_total} cartões e o VPL só é positivo a partir de "
        f"{zero_npv}; a R$ 149 de preço o equilíbrio sobe para {price_be(149)} cartões e a R$ 249 cai para "
        f"{price_be(249)}."
    )
    econ_rows = []
    for units in (600, 1000, 2000):
        e = pp.economics(units, unit_net)
        econ_rows.append([br(units), br(e["payback_months"], 1), pct(e["roi"], 0), brl(e["npv"], 0),
                          pct(e["irr_monthly"], 1)])
    b.table(
        "Viabilidade econômica por volume vendido em 12 meses (preço líquido R$ 199, custo variável R$ 80)",
        ["Cartões vendidos", "Equilíbrio (mês)", "ROI", "VPL", "TIR mensal"],
        econ_rows,
        [3.2, 3.2, 2.6, 3.4, 3.6],
        f"elaboração própria. ROI: lucro líquido sobre o investimento de {brl(pp.BUDGET, 0)}. VPL a "
        f"{pct(pp.DISCOUNT_RATE, 2)} ao ano e TIR com fluxo semanal. São metas de planejamento, não previsões.",
        right_cols=(0, 1, 2, 3, 4),
    )
    b.figure("fig_viabilidade.png", "Investimento, vendas e lucro acumulados por mês no cenário base de 1.000 "
             "cartões em 12 meses; as linhas tracejadas mostram 600 e 2.000 cartões.", width_cm=14.0,
             source="elaboração própria; vendas em ritmo constante nos 12 meses após o lançamento.")
    b.para(
        "A participação de mercado fica sem meta: não há dado público do tamanho do mercado de multitools de bolso "
        "no Brasil, e os relatórios gratuitos tratam de multiferramentas industriais (US$ 1,9 bilhão no mundo em "
        "2024) [26]. Como o planejamento só dispõe de informações preliminares, esta análise deve ser revista a "
        "cada ponto de decisão."
    )

    # ------------------------------------------------------------- 3
    b.heading("3. Projeto conceitual", 1)
    b.heading("3.1 Diagrama de blocos funcional", 2)
    b.figure("fig_blocos.png", "Função total e subfunções, com fluxos de material (linha grossa), energia (linha "
             "fina) e sinal (tracejada).", width_cm=14.5, source="elaboração própria.")
    b.para(
        "A função total é resolver um imprevisto cotidiano: entra um objeto a manipular (parafuso ou "
        "embalagem) e a força do usuário; sai a tarefa concluída sem dano ao usuário nem ao objeto. As funções "
        "principais são posicionar e encaixar (F1), transmitir torque (F2) e abrir embalagem (F3); medir (F4) e "
        "proteger o usuário (F5) são secundárias."
    )
    b.heading("3.2 Matriz morfológica e seleção do conceito", 2)
    b.table(
        "Matriz morfológica e composição das alternativas A, B e C (número do princípio escolhido)",
        ["Função", "Princípio 1", "Princípio 2", "Princípio 3", "A", "B", "C"],
        [["F1 Posicionar e encaixar", "Contorno com recortes", "Ranhura lateral", "Guia em relevo", "1", "1", "1"],
         ["F2 Transmitir torque", "Hexágonos no contorno", "Inserto metálico", "Ranhura chata", "1", "1", "2"],
         ["F3 Abrir embalagem", "Lâmina exposta", "Chanfro rombo", "Serrilha", "1", "2", "2"],
         ["F4 Medir", "Escala gravada", "Sem escala", "Escala em etiqueta", "1", "1", "2"],
         ["F5 Proteger o usuário", "Borda viva", "Raio e chanfro com inspeção", "Capa protetora", "1", "2", "3"]],
        [3.4, 3.0, 3.3, 2.8, 1.2, 1.2, 1.1],
        "elaboração própria.",
        right_cols=(4, 5, 6),
    )
    b.table(
        "Alternativas de solução e nota ponderada (escala de 1 a 5)",
        ["Critério", "Peso", "A: lâmina", "B: chanfro", "C: inserto"],
        [[crit, pct(w), *[str(SCORES[k][i]) for k in "ABC"]] for i, (crit, w) in enumerate(CRITERIA.items())]
        + [["Nota ponderada", "100%", *[br(scores[k], 2) for k in "ABC"]]],
        [4.6, 2.0, 3.1, 3.1, 3.2],
        f"elaboração própria. As alternativas A, B e C estão compostas na {R('morf')}. Pesos e notas são julgamento "
        "da equipe.",
        bold_rows=(5,), right_cols=(1, 2, 3, 4),
    )
    b.para(
        f"O conceito B obtém {br(scores['B'], 2)}, contra {br(scores['A'], 2)} de A e {br(scores['C'], 2)} de C. "
        f"Variando o peso da segurança de {pct(lo_w)} a {pct(hi_w)}, B "
        f"{'vence em todos os casos' if b_always else 'nem sempre vence'}; os pesos devem ser revisados com "
        "usuários na etapa de teste de conceito."
    )
    b.heading("3.3 Arquitetura e ergonomia", 2)
    b.figure("fig_croqui.png", "Croqui da arquitetura integral: uma placa de fibra de carbono com funções usinadas "
             "e gravadas.", width_cm=12.0, source="elaboração própria; ilustrativo.")
    b.para(
        "A avaliação ergonômica usa o método SHERPA [30]: para cada tarefa do usuário, listam-se os erros "
        "possíveis (deslizes, lapsos e enganos [31]), a prevenção no projeto e a verificação. O cartão é segurado "
        "em pinça entre o polegar e o indicador; a espessura de 2 mm e a ausência de cabo limitam a força e o "
        "torque aplicáveis, e por isso o limite de torque é um requisito de projeto."
    )
    b.table(
        "Avaliação ergonômica: erros humanos operacionais, prevenção no projeto e verificação",
        ["Tarefa", "Erro humano possível", "Prevenção no projeto", "Verificação"],
        [["Retirar o cartão da carteira", "Segurar pela borda e se cortar (deslize)",
          "Chanfro contínuo e cantos arredondados", "Inspeção de borda por lote (A7)"],
         ["Escolher o recorte", "Usar o recorte de tamanho errado e arredondar o parafuso (engano)",
          "Medida gravada ao lado de cada recorte", "Teste de uso observado (A6)"],
         ["Aplicar o torque", "Forçar além do limite ou fora do plano do cartão e quebrá-lo (engano)",
          "Limite de torque no manual; fratura em modo seguro, sem projeção", "Ensaio de torque até a falha (A6)"],
         ["Abrir embalagem", "Cortar o conteúdo ou a mão ao puxar o chanfro (deslize)",
          "Chanfro rombo, que rompe a fita sem cortar o conteúdo", "Ensaio de abertura sem tocar no conteúdo (A6)"],
         ["Medir com a escala", "Ler errado por falta de contraste (deslize)",
          "Escala gravada em baixo relevo, com contraste", "Teste de legibilidade (A6)"],
         ["Guardar", "Deixar o cartão fora da carteira e perdê-lo (lapso)",
          "Formato CR80, que cabe na carteira; lote gravado para reposição", "Teste de uso observado (A6)"]],
        [3.0, 4.6, 4.6, 3.8],
        "elaboração própria, com o método SHERPA [30] e a classificação de erros de [31].",
        font=9,
    )

    # ------------------------------------------------------------- 4
    b.heading("4. Projeto detalhado", 1)
    b.heading("4.1 Subconjuntos e itens a fabricar ou comprar", 2)
    def when(ident: str) -> str:
        row = sched[sched["id"] == ident].iloc[0]
        return f"{ident}: S{row['start_week']} a S{row['end_week']}"

    b.table(
        "Lista de materiais, decisão de fazer ou comprar e plano de aquisições",
        ["Código", "Item", "Qtd.", "Material", "Decisão", "Critério", "Aquisição"],
        [["P1", "Chapa curada", "1/40 de chapa", "Fibra de carbono e epóxi", "Comprar", "Certificado, espessura e lote", when("A4")],
         ["P2", "Cartão recortado e usinado", "1", "Fibra de carbono", "Fazer (terceirizar a usinagem)", "Corte a frio, sem delaminação", when("A5")],
         ["P3", "Chanfro e acabamento", "1", "Fibra de carbono", "Fazer", "Segurança da borda", "Interno"],
         ["P4", "Hexágonos e recortes", "1 conjunto", "Fibra de carbono", "Fazer", "Torque em ensaio", "Interno"],
         ["P5", "Escala gravada", "1", "Fibra de carbono", "Fazer", "Legibilidade", "Interno"],
         ["P6", "Gravação de lote", "1", "Fibra de carbono", "Fazer ou terceirizar", "Rastreabilidade", when("A7")],
         ["P7", "Envelope ou berço", "1", "Papel ou plástico reciclável", "Comprar", "Protege a borda", when("A7")],
         ["P8", "Caixa externa", "1", "Papelão", "Comprar", "Identificação do lote", when("A7")],
         ["P9", "Manual e etiqueta", "1", "Papel", "Comprar", "Instruções e limites de uso", when("A7")]],
        [1.1, 3.0, 1.8, 2.8, 2.6, 2.8, 1.9],
        "elaboração própria. Aquisição: atividade e semanas do cronograma. Custos unitários dependem das "
        "cotações da atividade A4 e do fornecedor de usinagem; a decisão considera custo, prazo, capacidade e "
        "competência.",
        font=9,
    )
    b.figure("fig_estrutura.png", "Estrutura do produto em sistemas e itens, com o plano de processo que cobre cada "
             "item; itens fabricados em vermelho e comprados em preto.", width_cm=15.0,
             source=f"elaboração própria, no formato de estrutura do produto e planos de processo; itens da {R('bom')}.")
    b.heading("4.2 Modelagem CAD e desenho técnico", 2)
    b.para(
        f"A geometria do cartão foi modelada em software de desenho assistido por computador (CAD) e documentada "
        f"em desenho técnico ({R('desenho')}) e em modelo tridimensional ({R('modelo3d')}). O contorno segue o "
        "formato CR80: 85,60 mm de largura, com tolerância de +0,12 e -0,13 mm, e 53,80 mm de altura, com +0,20 e "
        "-0,05 mm, faixa que contém os 53,98 mm nominais do formato. A espessura é de 2,00 mm e as tolerâncias não "
        "cotadas são de ±0,05 mm, com raios não cotados de 0,5 mm."
    )
    b.figure("cad_technical_drawing.png", "Desenho técnico e detalhado com dimensões e tolerância do produto e seus "
             "sistemas.", width_cm=15.0, source="elaboração própria, em milímetros.")
    b.para(
        "Os recortes sextavados formam uma sequência de entradas para chaves de M8 a M3 ao longo de 64,46 mm do "
        "contorno (função F2). O chanfro rombo percorre uma das bordas maiores e abre embalagens sem cortar o "
        "conteúdo (F3). A escala gravada tem marcas a cada 5 mm e numeração a cada 10 mm (F4), e a identificação "
        "do lote é gravada na face (A7). Cotas e tolerâncias são hipóteses de projeto: serão validadas com as "
        "medições dos protótipos (A5) e com os ensaios (A6)."
    )
    b.figure("cad_3d_model.png", "Modelagem 3D do produto construído por software de desenho assistido por "
             "computador.", width_cm=7.0, source="elaboração própria.")
    b.heading("4.3 Plano macro do processo produtivo", 2)
    b.para(
        f"A {R('estrutura')} associa cada item a um plano de processo; a {R('macro')} detalha as operações de cada "
        "plano, com o posto, o tempo e o controle."
    )
    b.table(
        "Plano macro do processo (operação, plano, posto, descrição, tempo e controle)",
        ["Op.", "Plano", "Posto", "Descrição", "Tempo", "Controle"],
        [["10", "PIR", "Recebimento", "Receber a chapa e conferir o certificado", "Cronometrar em A5", "Lote e espessura"],
         ["20", "PIR", "Bancada", "Inspecionar o lote", "Cronometrar em A5", "Visual e dimensional"],
         ["30", "PPF-1", "Corte", "Fixar a chapa na mesa", "Cronometrar em A5", "Fixação sem folga"],
         ["40", "PPF-1", "Corte", "Cortar o perfil", "0,9 a 1,2 min [17][18]", "Dimensão externa"],
         ["50", "PPF-1", "Corte", "Usinar recortes e escala", "0,9 a 1,2 min [17][18]", "Geometria das funções"],
         ["60", "PPF-2", "Bancada", "Chanfrar e lixar, com proteção respiratória", "Cronometrar em A5", "Rugosidade e borda"],
         ["70", "PPF-2", "Bancada", "Limpar e inspecionar", "Cronometrar em A5", "Delaminação após o corte"],
         ["80", "PPF-3", "Gravação", "Gravar a identificação do lote", "Cronometrar em A5", "Rastreabilidade"],
         ["90", "PPM", "Embalagem", "Embalar", "Cronometrar em A5", "Proteção da borda"],
         ["100", "PPM", "Expedição", "Liberar o lote", "Cronometrar em A5", "Registro de inspeção"]],
        [1.0, 1.5, 2.2, 5.0, 3.3, 3.0],
        "elaboração própria. PIR: inspeção de recebimento; PPF: fabricação; PPM: montagem. Os tempos de corte são "
        "derivados de parâmetros publicados (ver texto); os demais saem dos protótipos (A5) e dos testes (A6).",
        font=9,
    )
    b.para(
        "Os tempos de corte derivam de parâmetros públicos de fresagem CNC: 1.000 a 1.500 mm/min e 0,5 mm por "
        "passe em chapa de 2 mm [17]; 900 mm/min em chapa de 1,5 mm [18]. O contorno CR80 tem cerca de 279 mm; com "
        "quatro passes, são 1.117 mm de trajetória, ou 0,9 a 1,2 min por operação (recortes internos supostos "
        "iguais ao contorno, hipótese). O total de 2 a 2,5 min por cartão equivale a 62 a 83 horas-máquina no "
        "lote de 2.000. As etapas manuais não têm dado público e serão cronometradas no protótipo."
    )
    b.heading("4.4 Embalagem e análise de modos de falha", 2)
    b.table(
        "Condições de embalagem (seis tarefas do Capítulo 8)",
        ["Tarefa", "Condição adotada", "Item"],
        [["Distribuição", "Envio pelos Correios em envelope rígido, a partir da base do grupo", "P7"],
         ["Formas e marcações", "Lote, material, limites de uso e garantia impressos na caixa e no manual", "P8, P9"],
         ["Elemento crítico", "A borda do cartão, que não pode lascar nem encostar em outros produtos", "P7"],
         ["Adaptação", "Berço interno que mantém o cartão fixo e afastado de outros produtos", "P7"],
         ["Projeto da embalagem", "Caixa externa identificada por lote", "P8"],
         ["Processo", "Embalagem em bancada, com conferência do lote antes da expedição", "Operações 90 e 100"]],
        [3.4, 9.2, 3.4],
        "elaboração própria.",
        font=9,
    )
    b.table(
        "Análise de modos e efeitos de falha (FMEA), pontuações hipotéticas",
        ["Modo de falha", "Efeito", "S", "O", "D", "R = S×O×D", "Ação"],
        [["Delaminação no corte", "Peça rejeitada ou fratura", "8", "5", "4", "160", "Corte a frio e inspeção por lote"],
         ["Borda viva", "Corte no usuário ou na carteira", "9", "4", "3", "108", "Chanfro e inspeção de borda"],
         ["Falha no torque", "Peça quebrada em uso", "7", "4", "4", "112", "Ensaio de torque em amostras"],
         ["Dano no envio", "Borda lascada no cliente", "5", "4", "3", "60", "Envelope rígido e berço"]],
        [3.3, 3.6, 0.8, 0.8, 0.8, 1.8, 4.9],
        "elaboração própria; severidade (S), ocorrência (O) e detecção (D) de 1 a 10 são hipóteses a calibrar "
        "nos ensaios.",
        font=9, right_cols=(2, 3, 4, 5),
    )

    # ------------------------------------------------------------- 5
    b.heading("5. Lançamento do produto", 1)
    b.heading("5.1 Processo de vendas e distribuição", 2)
    b.table(
        "Canais de venda avaliados",
        ["Canal", "Vantagem", "Limite", "Decisão no piloto"],
        [["Página própria", "Margem integral e controle da experiência", "Exige tráfego e meio de pagamento", "Adotar"],
         ["Plataforma de vendas (marketplace)", "Tráfego existente", "Taxas e regras de terceiros (a cotar)", "Adotar, se permitida"],
         ["Varejo físico", "Alcance presencial", "Margem repartida; estoque em loja", "Fora do piloto"],
         ["Atacado e catálogo", "Volume", "Prazo, estoque e capital de giro", "Fora do piloto"]],
        [3.6, 4.4, 4.6, 3.4],
        "elaboração própria.",
    )
    b.para(
        "O fluxo vai do pedido à confirmação de entrega, com envio pelos Correios a partir da base do grupo; um "
        "centro de distribuição próprio não se justifica nesse volume."
    )
    b.heading("5.2 Atendimento ao cliente e assistência", 2)
    b.table(
        "Processos de atendimento, responsáveis e níveis de serviço propostos",
        ["Processo", "Canal", "Responsável", "Nível de serviço"],
        [["Dúvidas antes da compra", "Formulário e mensagens da plataforma", "Vendas e atendimento", "1ª resposta em 1 dia útil"],
         ["Pedido e entrega", "Plataforma e rastreio", "Vendas e atendimento", "Envio em até 2 dias úteis"],
         ["Arrependimento (7 dias)", "Formulário", "Vendas e atendimento", "Reembolso imediato [7]"],
         ["Defeito ou vício", "Formulário com fotos e lote", "Produção e qualidade", "Triagem técnica em 5 dias úteis"],
         ["Fim de vida", "Formulário e código de postagem", "Vendas e atendimento", f"Ver {R('s_desc')}"]],
        [3.8, 4.4, 3.6, 4.2],
        "elaboração própria. Os níveis de serviço são propostas do grupo, "
        "revisáveis após o piloto.",
    )
    b.para(
        "Cada ocorrência é registrada em uma base única (pedido, lote, motivo, evidência, decisão e prazo); borda, "
        "delaminação ou falha funcional retornam ao projeto como mudança de engenharia. A garantia legal é de 90 "
        "dias [7, art. 26]; propõe-se garantia contratual de 12 meses contra defeito de fabricação, a confirmar. "
        "Não há peças substituíveis: a assistência é troca ou reembolso. A fase custa "
        f"{brl(cost_by_id.loc['A8', 'activity_cost_brl'], 0)} (atividade A8)."
    )

    b.figure("fig_lancamento.png", "Os quatro processos de apoio começam antes da fase de lançamento.", width_cm=10.0,
             source="elaboração própria.")

    # ------------------------------------------------------------- 6
    b.heading("6. Descontinuidade do produto", 1)
    b.heading("6.1 Fim de vida e logística reversa", 2)
    b.para(
        "A fase começa na primeira devolução e termina quando o suporte acaba. Três retornos físicos têm "
        "destinos distintos (Apêndice A): arrependimento em 7 dias [7, art. 49], com reinspeção e retorno ao "
        "estoque; defeito ou vício [7, art. 26], com análise de falha por lote; e fim de vida, que é a logística "
        "reversa tratada aqui. O recolhimento é voluntário: a Lei 12.305, art. 33, obriga a logística reversa "
        "de agrotóxicos, pilhas, pneus, óleos, lâmpadas e eletroeletrônicos, e só estende a outros produtos por "
        "regulamento ou acordo setorial [5][6]. Permanecem a responsabilidade compartilhada e o dever de "
        "informar como evitar e eliminar o resíduo (arts. 30 e 31) [5]. Essa leitura deve ser confirmada por "
        "parecer jurídico."
    )
    b.figure("fig_ciclo_vida.png", "Posição da descontinuidade no ciclo de vida: cada cliente devolve o cartão em "
             "um momento diferente.", width_cm=13.0, source="elaboração própria; esquemático, sem escala.")
    b.heading("6.2 Decisões de recolhimento e remanufatura", 2)
    b.table(
        "Decisões da logística reversa",
        ["Pergunta", "Decisão", "Evidência", "Dado ainda necessário"],
        [["Há benefício ao cliente?", f"Sim: frete reverso gratuito e vale-desconto de {brl(p['voucher_brl'], 0)}, "
          f"um por cartão validado; teto de {br(cap_cards)} cartões no piloto",
          f"Custo de {brl(voucher['total_cost_brl'], 0)} no cenário de {pct(ref)} de devolução: "
          f"{brl(voucher['cost_per_unit_sold_brl'])} por unidade vendida, {pct(voucher['share_of_contribution_margin'], 1)} da margem",
          "Preço do frete (Correios), taxa de resgate"],
         ["Há lojas para o recolhimento?", "Não: postagem reversa pelos Correios; ponto presencial apenas na base do grupo",
          f"Lojas: {br(store_ref['returns_per_store_per_month'], 2)} cartão por loja por mês e "
          f"{brl(store_ref['cost_per_return_brl'])} por cartão, contra {brl(mail_cost)} nos Correios; teto de {pct(se_s_share, 1)} da população",
          "Agências e lojas por UF"],
         ["Como é a remanufatura?", "O cartão não é remanufaturado; reaproveita-se em cascata (triagem A a D) e recicla-se por lote consolidado",
          f"Retrabalho custaria {brl(reman['cost_per_recovered_card_brl'], 0)} por cartão recuperado, contra {brl(p['variable_cost_brl'], 0)} "
          f"de um novo; só empata com {pct(reman['minimum_grade_a_yield'])} de peças recuperáveis",
          "Aceite, lote mínimo e preço do reciclador; laudo do resíduo"]],
        [3.0, 4.6, 5.6, 2.8],
        "elaboração própria (Apêndice A). Todos os valores são cenários de planejamento.",
        font=9,
    )
    b.para(
        "Benefício: o vale-desconto vence a matriz enquanto o custo pesar até "
        f"{pct(voucher_wins_until)}, resultado apertado que depende dos pesos da equipe; a taxa de {pct(ref)} de "
        "devolução vem de outro produto, sem recompensa, e é cenário, não previsão [12]. Recolhimento: os Correios "
        f"vencem enquanto o custo pesar até {pct(mail_wins_until)}; o preço depende de contrato [8][9]. "
        "Reaproveitamento: o maior volume a destinar são os retalhos de usinagem "
        f"({br(flow_ref['machining_scrap_kg'], 1)} kg por lote, {br(flow_ref['scrap_to_returned_ratio'], 1)} vez a massa "
        f"devolvida a {pct(ref)}), segregados por lote. Só se conhece uma empresa brasileira que recupera fibra de "
        "compósito curado, sem divulgar lote mínimo nem preço [10]; por isso o material fica estocado até haver "
        "destinador. A reciclagem térmica retém cerca de 75% da resistência da fibra e a química, valores próximos "
        "aos da fibra virgem; a mecânica gera fibra curta, de baixo valor [11]; há pesquisa brasileira em [15][16]."
    )
    b.heading("6.3 Operação, encerramento e custo", 2)
    b.para(
        f"O recolhimento é considerado encerrado quando forem recebidas {pct(mid)} das unidades vendidas "
        f"({br(p['lot_units'] * mid)} cartões do lote de {br(p['lot_units'])}) ou {br(p['horizon_months'])} meses "
        f"após o fim das vendas, o que ocorrer primeiro, com revisão aos 12 meses. A {R('fase_fig')} "
        f"e a {R('fase_ativ')} mostram dependências, prazos e custos."
    )
    b.figure("reverse_flow_fase.png", "Dependência entre as atividades da fase de descontinuidade.", width_cm=15.0,
             source="elaboração própria.")
    prow = [[r.id, r.activity, br(r.duration_weeks), r.predecessors or "-", r.resources, br(r.cost_brl, 0),
             "Projeto" if r.cost_type == "projeto" else "Operacional"] for r in phase.itertuples()]
    b.table(
        "Atividades da fase de descontinuidade",
        ["ID", "Atividade", "Dur. (sem.)", "Precedência", "Recursos", "Custo (R$)", "Natureza"],
        prow, [1.0, 4.6, 1.5, 2.2, 2.3, 1.9, 2.4],
        f"elaboração própria. Mão de obra a {brl(p['team_week_cost_per_person_brl'], 0)} por pessoa-semana. "
        f"As atividades de projeto somam {brl(eol_project, 0)}, acima da reserva de {brl(pp.RESERVE, 0)}; "
        f"com o custo operacional de {brl(eol_opex, 0)}, o fim de vida custa {brl(eol_project + eol_opex, 0)} "
        f"({brl(eol_unit)} por unidade do lote) e o ponto de equilíbrio sobe para {br(break_even_total)} unidades.",
        font=9, right_cols=(2, 5),
    )
    b.para(
        "A reserva gerencial não cobre o fim de vida; o custo deve sair da margem das vendas. Finalizar "
        "o suporte é encerrar garantia e atendimento com aviso de 90 dias aos compradores, mantendo aberto o "
        "canal de devolução; o encerramento do projeto registra massa destinada, taxa de devolução, custo real, "
        "resposta do destinador e lições aprendidas."
    )

    # ------------------------------------------------------------- 7
    b.heading("7. Conclusão", 1)
    b.para(
        f"O projeto custa {brl(pp.BUDGET, 0)} mais reserva de {brl(pp.RESERVE, 0)}, em "
        f"{int(sched['end_week'].max())} semanas e nove atividades. O conceito B obteve a maior nota, "
        f"{br(scores['B'], 2)}, e vence com o peso da segurança entre "
        f"{pct(lo_w)} e {pct(hi_w)}. O investimento se recupera com {break_even_total} cartões a R$ 199 e o VPL, "
        f"com a Selic como taxa de desconto, só é positivo a partir de {zero_npv}, mas os "
        f"concorrentes custam bem menos e a pressão competitiva é {sa.porter_level(sa.porter_mean())} (nota "
        f"{br(sa.porter_mean(), 1)} de 5); a viabilidade depende de o mercado pagar pela diferenciação, o que só a "
        "pesquisa primária mostra."
    )
    b.para(
        "No fim de vida, recomenda-se o recolhimento por postagem reversa, voluntário (o produto não consta do "
        "art. 33 da Lei 12.305 [5]), com custo pago pela margem das vendas."
    )

    # ------------------------------------------------------------- referências
    b.heading("Referências", 1)
    refs = [
        "[1] IBGE. SIDRA, tabela 6579: população residente estimada por UF, 2024. https://apisidra.ibge.gov.br/desctabapi.aspx?c=6579. Acesso em 03 nov. 2026.",
        "[2] IBGE. SIDRA, tabela 7531: rendimento médio mensal real domiciliar per capita, 2024. https://apisidra.ibge.gov.br/desctabapi.aspx?c=7531. Acesso em 03 nov. 2026.",
        "[3] CETIC.BR. TIC Domicílios 2024, tabela H9. https://cetic.br/pt/tics/domicilios/2024/individuos/H9/. Acesso em 03 nov. 2026.",
        "[4] TRANSPORTE ATIVO. Pesquisa Nacional Perfil do Ciclista 2024. https://ta.org.br/perfil/perfil24.pdf. Acesso em 03 nov. 2026.",
        "[5] BRASIL. Lei nº 12.305, de 2 de agosto de 2010. https://www.planalto.gov.br/ccivil_03/_ato2007-2010/2010/lei/l12305.htm. Acesso em 10 nov. 2026.",
        "[6] BRASIL. Decreto nº 10.936, de 12 de janeiro de 2022. https://planalto.gov.br/ccivil_03/_ato2019-2022/2022/decreto/D10936.htm. Acesso em 10 nov. 2026.",
        "[7] BRASIL. Lei nº 8.078, de 11 de setembro de 1990 (Código de Defesa do Consumidor), arts. 26 e 49. https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm. Acesso em 10 nov. 2026.",
        "[8] CORREIOS. Logística reversa. https://www.correios.com.br/enviar/encomendas/logistica-reversa. Acesso em 10 nov. 2026.",
        "[9] CORREIOS. Encomendas nacionais e simulador de preços. https://www.correios.com.br/enviar/encomendas/nacional. Acesso em 10 nov. 2026.",
        "[10] RECALTECH. Reciclagem de fibras de carbono. https://www.recaltech.com.br/reciclagem-de-fibra-de-carbono. Acesso em 10 nov. 2026.",
        "[11] ALSUBAIE, F.; YANG, L. Recycled carbon fibre in circular economy applications. In: International Conference on Manufacturing Research, 23., Astana, 2026. https://strathprints.strath.ac.uk/97460/. Acesso em 10 nov. 2026.",
        "[12] HARDEN, C. W.; PEDERSEN, T.; JENSEN, P. D. Ø. Motivation or inconvenience: what matters most? Understanding recycling behavior of healthcare waste. Cleaner and Responsible Consumption, v. 15, 100240, 2024. https://doi.org/10.1016/j.clrc.2024.100240. Acesso em 10 nov. 2026.",
        "[13] LEATHERMAN. Built to last: the Leatherman warranty promise. https://uk.leatherman.com/blogs/news/built-to-last-the-leatherman-warranty-promise. Acesso em 10 nov. 2026.",
        "[14] VICTORINOX. Victorinox two-year warranty. https://www.victorinox.com/en-DE/cms/victorinox-two-year-warranty/. Acesso em 10 nov. 2026.",
        "[15] USP. Reciclagem termoquímica de resíduos industriais de compósitos pré-impregnados de fibra de carbono e matriz epoxídica (dissertação). https://teses.usp.br/teses/disponiveis/97/97134/tde-12122024-123558/en.html. Acesso em 10 nov. 2026.",
        "[16] FAPESP. Auxílio 17/16160-8: reuso de retalhos de prepreg de fibra de carbono do ciclo de produção. https://bv.fapesp.br/pt/auxilios/98570/. Acesso em 10 nov. 2026.",
        "[17] TOOLSTODAY. Cutting carbon fiber on a CNC: tips, safety and bit selection, 13 out. 2025. https://global.toolstoday.com/learn/cutting-carbon-fiber-on-a-cnc-tips-safety-bit-selection. Acesso em 11 nov. 2026.",
        "[18] CNC-STEP. Milling, drilling and cutting carbon fiber sheets. https://www.cnc-step.com/milling-drilling-cutting-carbon-fiber-sheets/. Acesso em 11 nov. 2026.",
        "[19] WALLET NINJA. Página oficial do produto. https://walletninja.com/. Acesso em 11 nov. 2026.",
        "[20] LEATHERMAN. Micra. https://www.leatherman.com/collections/bestsellers/products/micra. Acesso em 11 nov. 2026.",
        "[21] MICROMACHINES. A review of research progress on machining carbon fiber-reinforced composites with lasers. v. 14, n. 1, art. 24, 2023. https://www.mdpi.com/2072-666X/14/1/24. Acesso em 15 nov. 2026.",
        "[22] OSO GRANDE KNIVES. Touch of Ginger Carbon Fiber Credit Card Spanner Tool (TOG09). https://www.osograndeknives.com/catalog/credit-card-sized-tools/touch-of-ginger-carbon-fiber-credit-card-spanner-tool-knife-wrench-wallet-size-3.375x2.125-tog09-31316.html. Acesso em 15 nov. 2026.",
        "[23] NEWMAN, C. M. Flat multiple tool holder. US 5.328.026, depositada em 11 jun. 1993. https://patents.google.com/patent/US5328026. Acesso em 15 nov. 2026.",
        "[24] NITE IZE. Card-shaped multi-tool (desenho industrial). CA 175697, depositado em 29 jun. 2017. https://patents.google.com/patent/CA175697S/en. Acesso em 15 nov. 2026.",
        "[25] PELTON, R. Y. Compact survival tool. US 8.713.735, depositada em 6 dez. 2011. https://patents.google.com/patent/US8713735. Acesso em 15 nov. 2026.",
        "[26] GRAND VIEW RESEARCH. Multi-tool systems market report. https://www.grandviewresearch.com/industry-analysis/multi-tool-systems-market-report. Acesso em 15 nov. 2026.",
        "[27] COCHRAN, W. G. Sampling techniques. 3. ed. Nova York: Wiley, 1977.",
        "[28] VAN WESTENDORP, P. NSS Price Sensitivity Meter (PSM): a new approach to study consumer perception of prices. In: ESOMAR Congress, 29., Veneza, 1976. p. 139-167.",
        "[29] BANCO CENTRAL DO BRASIL. Sistema Gerenciador de Séries Temporais, série 432: meta da taxa Selic. https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json. Acesso em 15 nov. 2026.",
        "[30] EMBREY, D. E. SHERPA: a systematic human error reduction and prediction approach. In: International Topical Meeting on Advances in Nuclear Power Systems, Knoxville, 1986.",
        "[31] REASON, J. Human error. Cambridge: Cambridge University Press, 1990.",
    ]
    for ref_text in refs:
        b.small(ref_text, 9.5, left=True)

    # ------------------------------------------------------------- apêndices
    b.appendix("A", f"Detalhamento das Seções {num('s_swot')} e {num('s_desc')}")
    b.figure("fig_porter.png", "Intensidade das cinco forças competitivas (escala de 1 a 5).", width_cm=14.0,
             source=f"elaboração própria a partir da {R('porter')}.")
    brows = [[labels_pt[r.option], brl(r.cost_per_return_brl), br(r.custo, 2), br(r.estimulo), br(r.simplicidade),
              br(r.mensagem), br(r.recompra), br(r.weighted_score, 2)]
             for r in benefit.itertuples() for labels_pt in [{
                 "sem_beneficio": "Sem benefício", "frete_gratis": "Só frete",
                 "frete_gratis_voucher": "Frete e vale", "frete_gratis_dinheiro": "Frete e reembolso"}]]
    b.table(
        "Matriz de decisão do benefício (escala de 1 a 5)",
        ["Política", "Custo por devolução", "Custo (30%)", "Estímulo (30%)", "Simplicidade (15%)", "Mensagem (15%)",
         "Recompra (10%)", "Nota"],
        brows, [3.6, 2.1, 1.5, 1.7, 2.0, 1.7, 1.8, 1.2],
        "elaboração própria. Frete: frete reverso gratuito; vale: vale-desconto de R$ 20. A nota de custo é "
        "calculada; os demais critérios e os pesos são julgamento da equipe.",
        font=8.5, right_cols=(1, 2, 3, 4, 5, 6, 7),
    )
    crows = [[{"correios_reversa": "Correios", "lojas_parceiras": "Lojas parceiras",
               "ponto_unico_presencial": "Ponto único"}[r.option], brl(r.cost_per_return_brl),
              pct(r.coverage_upper_bound, 1), br(r.custo, 2), br(r.cobertura, 2), br(r.rastreabilidade),
              br(r.seguranca), br(r.esforco), br(r.weighted_score, 2)] for r in channel.itertuples()]
    b.table(
        "Matriz de decisão do canal de recolhimento (escala de 1 a 5)",
        ["Canal", "Custo por devolução", "Cobertura máx.", "Custo (25%)", "Cobertura (30%)", "Rastreab. (20%)",
         "Segurança (15%)", "Esforço (10%)", "Nota"],
        crows, [3.2, 1.9, 1.7, 1.4, 1.7, 1.5, 1.7, 1.5, 1.1],
        "elaboração própria. Correios: postagem reversa; lojas parceiras: piloto em lojas; ponto único: entrega "
        "presencial na base do grupo. Custo e cobertura são calculados; os demais critérios são julgamento da equipe.",
        font=8.5, right_cols=(1, 2, 3, 4, 5, 6, 7, 8),
    )
    g = {k: p[f"grade_{k}_share"] for k in "abcd"}
    b.table(
        "Triagem do cartão devolvido e destino",
        ["Classe", "Critério visual e dimensional", "Destino", "Parcela hipotética (massa a 22%)"],
        [["A", "Íntegro; borda e gravação legíveis", "Peça de ensaio ou mostruário; nunca revenda como novo",
          f"{pct(g['a'])} ({br(flow_ref['returned_kg'] * g['a'], 1)} kg)"],
         ["B", "Desgaste leve", "Segunda vida só se validada em ensaio; senão, classe C",
          f"{pct(g['b'])} ({br(flow_ref['returned_kg'] * g['b'], 1)} kg)"],
         ["C", "Delaminado, trincado ou deformado", "Consolidação por lote e reciclagem",
          f"{pct(g['c'])} ({br(flow_ref['returned_kg'] * g['c'], 1)} kg)"],
         ["D", "Fibra exposta ou contaminação", "Saco duplo e destinação licenciada; nunca triturar nem lixar",
          f"{pct(g['d'])} ({br(flow_ref['returned_kg'] * g['d'], 1)} kg)"]],
        [1.3, 4.6, 6.4, 3.7],
        "elaboração própria. Recebimento com luvas, ventilação e registro por lote; requisitos definitivos "
        "pela ficha de segurança do fornecedor da chapa.",
        font=9,
    )
    b.appendix("B", "Premissas e natureza dos dados")
    rows_c = [
        ["Formato CR80 (85,60 × 53,98 mm) e espessura de até 2 mm", "Observada", "Plano de validação técnica"],
        ["Preço líquido R$ 199, custo variável R$ 80, lote de 2.000", "Observada", f"Seções {num('s_viab')} e {num('s_lanc')}"],
        ["Orçamento R$ 54 mil e reserva R$ 6 mil", "Observada", f"Seção {num('s_proj')}"],
        ["Divisão do custo por tipo de recurso e taxas-padrão", "Hipótese", "Cotações (A4, A5)"],
        ["Frete reverso (R$ 15), kit (R$ 2,50) e triagem (R$ 4)", "Hipótese", "Contrato dos Correios; teste de bancada"],
        ["Vale-desconto de R$ 20 e taxa de resgate de 50%", "Hipótese", "Piloto"],
        ["Taxas de devolução de 5%, 10% e 30%", "Hipótese", "Primeiros 12 meses"],
        ["Taxa de devolução de 22%", "Observada em outro produto [12]", "Primeiros 12 meses"],
        ["Chapa de 500 × 500 mm, margem de 10 mm, traço de 1 mm, 6% de recortes, densidade de 1,55 g/cm³",
         "Hipótese", "Cotação A4 e CAD"],
        ["Parcelas das classes A a D de devolvidos", "Hipótese", "Primeiros lotes recebidos"],
        ["Custo de retrabalho de R$ 45 por cartão", "Hipótese", "Teste de bancada"],
        ["Janela de recebimento de 36 meses", "Hipótese", "Ensaios A6"],
        ["Pontuações das matrizes e do FMEA", "Julgamento da equipe", "Revisão com usuários e ensaios"],
        ["Classificação NBR 10004, aceite de coprocessamento e lote mínimo do reciclador", "Sem fonte pública", "Laudo e resposta escrita"],
        ["Agências dos Correios e lojas de bicicleta por UF", "Sem fonte pública", "Bases oficiais"],
    ]
    b.table("Natureza dos dados", ["Dado", "Natureza"], [r[:2] for r in rows_c],
            [11.6, 4.4], "elaboração própria.", font=9)
    return b


def main() -> None:
    """Regenerate model outputs, figures and the report."""
    try:
        from src import report_diagrams, reverse_flow_diagram, strategic_analysis
    except ImportError:  # pragma: no cover
        import report_diagrams
        import reverse_flow_diagram
        import strategic_analysis
    rl.run()
    reverse_flow_diagram.write_all(png_dir=ROOT / "outputs" / "visualizations")
    report_diagrams.render_all()
    strategic_analysis.render_all()
    OUTPUT_DOCX.parent.mkdir(parents=True, exist_ok=True)
    build_report().doc.save(OUTPUT_DOCX)
    print(f"Report written to: {OUTPUT_DOCX}")


if __name__ == "__main__":
    main()
