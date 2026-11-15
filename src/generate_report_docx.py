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
    from src import strategic_analysis as sa
    from src.docx_builder import Builder, br, brl, load_team, pct
    from src.regional_market_analysis import build_regional_analysis, load_state_indicators
except ImportError:  # pragma: no cover
    import project_plan as pp
    import reverse_logistics_model as rl
    import strategic_analysis as sa
    from docx_builder import Builder, br, brl, load_team, pct
    from regional_market_analysis import build_regional_analysis, load_state_indicators

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


def build_report() -> Builder:
    p = rl.load_assumptions()
    sched, costs, base = pp.schedule(), pp.cost_table(), pp.weekly_baseline()
    regional = build_regional_analysis(load_state_indicators())
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

    b = Builder()
    b.cover("CARTÃO MULTITOOL EM FIBRA DE CARBONO", "Relatório de Desenvolvimento de Produto: ER801A", load_team())

    # ----------------------------------------------------------- Resumo
    b.heading("Resumo", 1)
    b.para(
        "Este relatório planeja o desenvolvimento, o lançamento e a descontinuidade de um cartão multitool "
        "plano, no formato CR80, em fibra de carbono, para usuários de carregamento cotidiano (EDC, do inglês "
        "everyday carry) e ciclistas urbanos. As seções seguem as normas do trabalho e os capítulos 4, 5, 7, 8, "
        "10 e 12 da disciplina, com análise SWOT e das cinco forças de Porter. Os números vêm de modelos reproduzíveis com premissas rotuladas como observadas, "
        f"derivadas ou hipotéticas. O projeto custa {brl(pp.BUDGET, 0)} em {int(sched['end_week'].max())} semanas, "
        f"com reserva de {brl(pp.RESERVE, 0)}. O recolhimento de fim de vida é viável por postagem reversa, com "
        "benefício modesto ao cliente; a remanufatura do cartão não é viável. A Seção 7 conclui e lista as "
        "informações que ainda faltam para validar o projeto."
    )

    # ------------------------------------------------------------- 1
    b.heading("1. Planejamento estratégico do produto", 1)
    b.heading("1.1 Posicionamento da empresa", 2)
    b.para(
        "A Tabela 1 responde, nesta ordem, às sete perguntas do roteiro de planejamento estratégico do "
        "Capítulo 4. Missão, posicionamento e competências são propostas do grupo; mercado e "
        "recursos usam dados do projeto."
    )
    b.table(
        "Planejamento estratégico do produto (roteiro do Capítulo 4)",
        ["Elemento", "Resposta", "Natureza"],
        [
            ["Missão", "Oferecer uma ferramenta plana, leve e discreta para pequenos imprevistos cotidianos, "
             "com desempenho comprovado por ensaio.", "Proposta"],
            ["Segmentação", "Usuários EDC e ciclistas urbanos; Sudeste e Sul concentram "
             f"{pct(se_s_share, 1)} da população e renda per capita de R$ 2.377 a R$ 2.488 [1][2].", "Derivada"],
            ["Tendências tecnológicas", "Corte a frio de compósitos (jato d'água abrasivo ou usinagem CNC) e "
             "fabricação sob demanda; concorrentes metálicos já consolidados.", "A validar"],
            ["Posicionamento", "Pioneiro em forma (CR80) e material, competindo por diferenciação e não por custo.",
             "Proposta"],
            ["Metas", f"Recuperar o investimento de {brl(pp.BUDGET, 0)}: {be(54000, 199)} unidades ao preço-base "
             f"({be(60000, 199)} com a reserva); sem meta de participação de mercado antes da pesquisa primária.",
             "Derivada"],
            ["Competências", "Projeto em CAD, inspeção dimensional, atendimento e venda digital; usinagem "
             "terceirizada.", "Proposta"],
            ["Recursos necessários", f"Orçamento de {brl(pp.BUDGET, 0)} mais reserva de {brl(pp.RESERVE, 0)}; "
             "equipe de três discentes; chapa curada; bancada de ensaio.", "Observada"],
        ],
        [3.2, 10.3, 2.5],
        "elaboração própria a partir de [1] e [2].",
    )
    b.heading("1.2 Inovação do produto", 2)
    b.para(
        "A inovação proposta é de forma e de material: uma ferramenta de peça única, no formato de cartão de "
        "crédito, em fibra de carbono, com funções integradas (chave sextavada, abertura de embalagem por "
        "chanfro rombo e escala) e sem peças móveis. Frente às ferramentas metálicas de carteira, o ganho "
        "esperado é massa e volume menores com aparência diferenciada. É uma hipótese: resistência, segurança "
        "das bordas e custo ainda dependem dos ensaios da atividade A6."
    )
    b.heading("1.3 Concorrentes", 2)
    b.table(
        "Concorrentes de referência",
        ["Concorrente", "Categoria", "Garantia declarada", "Preço, material e dimensões"],
        [
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
        "Os concorrentes custam muito menos que o preço-base de R$ 199 (a Wallet Ninja, de mesmo formato, "
        "US$ 20): o cartão só se sustenta por diferenciação de material, massa e acabamento, o que o experimento "
        "de preço da Seção 1.4 deve testar."
    )
    b.heading("1.4 Mercado e pesquisa primária", 2)
    reg_names = {"North": "Norte", "Northeast": "Nordeste", "Southeast": "Sudeste", "South": "Sul",
                 "Central-West": "Centro-Oeste"}
    b.table(
        "Indicadores territoriais, 2024",
        ["Região", "População", "Participação", "Renda per capita (R$)"],
        [[reg_names[r.region], br(r.population_2024), f"{br(r.population_share_percent, 1)}%",
          br(r.weighted_mean_income_brl, 2)] for r in regional.itertuples()],
        [4.0, 3.5, 3.5, 5.0],
        "elaboração própria com IBGE/SIDRA, tabelas 6579 e 7531, 2024 [1][2]. A renda regional é a média "
        "ponderada pela população das UFs. São indicadores territoriais, não demanda por multitools.",
        right_cols=(1, 2, 3),
    )
    b.para(
        "Os dados secundários (IBGE e Cetic.br [1][2][3]) não caracterizam o público do produto. A Pesquisa Nacional Perfil do Ciclista 2024 "
        "(11.956 entrevistas nas cidades pesquisadas) contextualiza hábitos, mas não é convertida em tamanho de "
        "mercado [4]. Seguindo a orientação de perguntar sobre "
        "hábitos e locais de uso, e não sobre o tamanho desejado, o plano de pesquisa primária "
        "tem quatro etapas: triagem por entrevistas (20 a 30), teste de conceito com cotas por região (100 a "
        "150 respostas), teste de uso observado (10 a 15) e experimento de preço. Nenhuma delas autoriza "
        "estimar o mercado nacional; servem para validar hipóteses."
    )
    b.heading("1.5 Economia preliminar", 2)
    b.table(
        "Ponto de equilíbrio do orçamento de desenvolvimento (custo variável hipotético de R$ 80)",
        ["Cenário", "Preço líquido", "Margem unitária", "Unidades (R$ 54 mil)", "Unidades (R$ 60 mil)"],
        [[n, brl(pr, 0), brl(pr - 80, 0), br(be(54000, pr)), br(be(60000, pr))]
         for n, pr in (("Conservador", 149), ("Base", 199), ("Premium", 249))],
        [3.0, 3.0, 3.2, 3.4, 3.4],
        "elaboração própria. Preço e custo variável são hipóteses a substituir por cotação, impostos, taxas "
        "da plataforma, frete e devoluções. O ponto de equilíbrio é um requisito econômico de validação, "
        "não uma previsão.",
        right_cols=(1, 2, 3, 4),
    )
    b.para(
        "No piloto, o funil de indicadores deve registrar visitas, carrinhos, compras, conversão, ticket médio, "
        "margem de contribuição, custo de aquisição, devoluções e defeitos por lote, com os eventos de "
        "comércio eletrônico configurados antes de comparar canais."
    )

    b.heading("1.6 Análise do ambiente: SWOT e cinco forças de Porter", 2)
    b.para(
        "A matriz SWOT cruza fatores internos (forças e fraquezas) e externos (oportunidades e ameaças); as "
        "cinco forças de Porter medem a pressão competitiva do setor. Classificações e notas são julgamento da "
        "equipe, a revisar após a pesquisa primária e os ensaios da atividade A6."
    )
    b.figure("fig_swot.png", "Matriz SWOT do cartão multitool em fibra de carbono.", width_cm=11.5,
             source="elaboração própria.")
    b.para(
        "A principal força, o pioneirismo em forma e material, é também o ponto mais exposto: a arquitetura "
        "simples e a usinagem terceirizável facilitam a imitação."
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
    b.figure("fig_porter.png", "Intensidade das cinco forças competitivas (escala de 1 a 5).", width_cm=11.5,
             source="elaboração própria a partir da Tabela 5.")
    b.para(
        f"A média de {br(mean_force, 1)} indica pressão competitiva {sa.porter_level(mean_force)}. As três forças "
        "mais intensas (novos entrantes, fornecedores e substitutos) mostram que o produto não deve competir por "
        "preço: a defesa está na diferenciação comprovada por ensaio, na construção de marca no nicho EDC e "
        "ciclista e na negociação com mais de um fornecedor de chapa e de usinagem, coerente com o "
        "posicionamento por diferenciação da Tabela 1."
    )

    # ------------------------------------------------------------- 2
    b.heading("2. Planejamento do projeto", 1)
    b.heading("2.1 Termo de abertura (Project Charter)", 2)
    b.para("A Tabela 6 segue os campos do modelo do Capítulo 5.")
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
            ["Escopo do produto", "Cartão CR80 (85,60 × 53,98 mm), espessura de até 2 mm, peça única de fibra "
             "de carbono, com recorte sextavado, chanfro, escala e gravação de lote."],
            ["Escopo do projeto", "Entregas 1.0 a 7.0 da Figura 3. Fora do escopo: certificação de segurança ou "
             "de transporte aéreo e produção em escala."],
            ["Premissas", "Chapa curada disponível; corte por jato d'água ou CNC; venda inicial digital."],
            ["Restrições", "Segurança das bordas, custo, espessura de carteira, capacidade de usinagem."],
            ["Equipe", "Três discentes: projeto e ensaios; produção e qualidade; vendas e atendimento."],
            ["Riscos", "Delaminação, baixa utilidade percebida, custo alto, atraso de fornecedor e rejeição "
             "em inspeção."],
            ["Aprovações", "Avanço de fase só com requisitos aprovados, protótipo funcional e ensaios sem "
             "falha crítica (ponto de decisão do docente)."],
        ],
        [3.6, 12.4],
        "elaboração própria.",
    )
    b.heading("2.2 Estrutura analítica do projeto (EAP)", 2)
    b.figure("fig_eap.png", "EAP em três níveis: produto do projeto, entregas e pacotes de trabalho (atividades A1 a A9).",
             width_cm=12.5, source="elaboração própria.")
    b.heading("2.3 Atividades, precedências e custos", 2)
    b.para(
        "A Tabela 7 reproduz o formato da planilha do professor (ID, atividade, início, duração, término, "
        "precedência) acrescido dos custos por tipo de recurso. Prazos estão em semanas do projeto, e não "
        "em dias corridos. Os totais por atividade são as estimativas originais do grupo; a divisão por tipo é "
        "premissa até haver cotações (Tabela 8)."
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
    std_rows = [[code, name, kind, brl(rate, 0)] for code, (name, kind, rate) in pp.STANDARD_COST.items()]
    b.table(
        "Custo padrão e legenda das siglas",
        ["Sigla", "Especificação", "Tipo", "Custo (R$/pessoa-semana)"],
        std_rows + [["Equip. e serviços", "Licença de CAD, bancada de ensaio e usinagem terceirizada", "Serviço", "Cotação"],
                    ["Insumos", "Chapa curada, corpos de prova, embalagem", "Material", "Cotação"]],
        [3.2, 7.0, 2.4, 3.4],
        "elaboração própria. As taxas são hipóteses de planejamento e substituem-se por valores de cotação.",
        right_cols=(3,),
    )
    b.heading("2.4 Cronograma, caminho crítico e linha de base", 2)
    b.figure("fig_gantt_curva_s.png", "Curva S de custo acumulado e Gantt do projeto, em semanas.", width_cm=13.0,
             source="elaboração própria a partir da Tabela 7.")
    b.para(
        f"O caminho crítico é {critical}, com {int(sched['end_week'].max())} semanas; a atividade A4 tem folga de "
        f"uma semana. A curva S concentra {pct(s4)} do orçamento até a semana 4, porque A4 (chapa, "
        f"{brl(cost_by_id.loc['A4', 'inputs_brl'], 0)} em insumos) é a maior compra. O desvio de prazo e de custo "
        "será medido por SPI e CPI (valor agregado), com a linha de base acima. As rotinas de venda e de "
        "atendimento da Seção 5 são desenvolvidas dentro de A7 e A8, antes do lançamento."
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
        "Matriz morfológica (linhas na ordem do diagrama de blocos)",
        ["Função", "Princípio 1", "Princípio 2", "Princípio 3"],
        [["F1 Posicionar e encaixar", "Contorno com recortes", "Ranhura lateral", "Guia em relevo"],
         ["F2 Transmitir torque", "Hexágonos no contorno", "Inserto metálico", "Ranhura chata"],
         ["F3 Abrir embalagem", "Lâmina exposta", "Chanfro rombo", "Serrilha"],
         ["F4 Medir", "Escala gravada", "Sem escala", "Escala em etiqueta"],
         ["F5 Proteger o usuário", "Borda viva", "Raio e chanfro com inspeção", "Capa protetora"]],
        [4.2, 3.9, 4.2, 3.7],
        "elaboração própria.",
    )
    b.table(
        "Alternativas de solução e nota ponderada (escala de 1 a 5)",
        ["Critério", "Peso", "A: lâmina", "B: chanfro", "C: inserto"],
        [[crit, pct(w), *[str(SCORES[k][i]) for k in "ABC"]] for i, (crit, w) in enumerate(CRITERIA.items())]
        + [["Nota ponderada", "100%", *[br(scores[k], 2) for k in "ABC"]]],
        [4.6, 2.0, 3.1, 3.1, 3.2],
        "elaboração própria. A: F2 hexágonos, F3 lâmina, F4 escala, F5 borda viva. B: F2 hexágonos, F3 chanfro, "
        "F4 escala, F5 raio e chanfro. C: F2 inserto, F3 chanfro, F4 sem escala, F5 capa. Pesos e notas são "
        "julgamento da equipe.",
        bold_rows=(5,), right_cols=(1, 2, 3, 4),
    )
    b.para(
        f"O conceito B obtém {br(scores['B'], 2)}, contra {br(scores['A'], 2)} de A e {br(scores['C'], 2)} de C. "
        f"Variando o peso da segurança de {pct(lo_w)} a {pct(hi_w)}, B "
        f"{'vence em todos os casos' if b_always else 'nem sempre vence'}; os pesos devem ser revisados com "
        "usuários na etapa de teste de conceito."
    )
    b.heading("3.3 Arquitetura e características estéticas", 2)
    b.figure("fig_croqui.png", "Croqui da arquitetura integral: uma placa de fibra de carbono com funções usinadas "
             "e gravadas.", width_cm=10.0, source="elaboração própria; ilustrativo.")
    b.table(
        "Interfaces críticas da arquitetura",
        ["Interface", "Requisito"],
        [["Usuário e borda", "Chanfro rombo contínuo; nenhuma aresta viva após o acabamento"],
         ["Ferramenta e porca", "Recorte sextavado sem escorregamento nem fratura no torque definido em ensaio"],
         ["Cartão e carteira", "Formato CR80 e espessura de até 2 mm, com borda protegida em transporte"],
         ["Peça e processo de corte", "Corte a frio, sem delaminação; inspeção de borda por lote"]],
        [4.2, 11.8],
        "elaboração própria, a partir dos critérios do plano de validação técnica do projeto.",
    )
    b.table(
        "Características estéticas (forma, superfície, cor, estilo e semântica)",
        ["Atributo", "Decisão", "Justificativa"],
        [["Forma", "Retângulo CR80 com cantos arredondados", "Compatível com carteira e leitor de cartão"],
         ["Superfície", "Trama da fibra aparente, acabamento fosco", "Diferenciação visual e menor reflexo"],
         ["Cor", "Preto da própria fibra, gravação em baixo relevo", "Discrição; sem tinta que descasque"],
         ["Estilo", "Minimalista, de uso cotidiano (EDC)", "Coerência com o público e a concorrência"],
         ["Semântica", "Leve, técnico, seguro", "Mensagem a ser confirmada em teste de uso"]],
        [2.6, 6.2, 7.2],
        "elaboração própria. A avaliação de erro humano considera corte na "
        "borda, torque excessivo, delaminação por flexão e perda do cartão.",
    )

    # ------------------------------------------------------------- 4
    b.heading("4. Projeto detalhado", 1)
    b.heading("4.1 Subconjuntos e itens a fabricar ou comprar", 2)
    b.figure("fig_estrutura.png", "Estrutura do produto em três subsistemas; itens fabricados em vermelho e comprados em preto.",
             width_cm=8.5, source="elaboração própria.")
    b.table(
        "Lista de materiais e decisão de fazer ou comprar",
        ["Código", "Item", "Qtd.", "Material", "Decisão", "Critério"],
        [["P1", "Chapa curada", "1/40 de chapa", "Fibra de carbono e epóxi", "Comprar", "Certificado, espessura e lote"],
         ["P2", "Cartão recortado e usinado", "1", "Fibra de carbono", "Fazer (terceirizar a usinagem)", "Corte a frio, sem delaminação"],
         ["P3", "Chanfro e acabamento", "1", "Fibra de carbono", "Fazer", "Segurança da borda"],
         ["P4", "Hexágonos e recortes", "1 conjunto", "Fibra de carbono", "Fazer", "Torque em ensaio"],
         ["P5", "Escala gravada", "1", "Fibra de carbono", "Fazer", "Legibilidade"],
         ["P6", "Gravação de lote", "1", "Fibra de carbono", "Fazer ou terceirizar", "Rastreabilidade"],
         ["P7", "Envelope ou berço", "1", "Papel ou plástico reciclável", "Comprar", "Protege a borda"],
         ["P8", "Caixa externa", "1", "Papelão", "Comprar", "Identificação do lote"],
         ["P9", "Manual e etiqueta", "1", "Papel", "Comprar", "Instruções e limites de uso"]],
        [1.2, 3.6, 1.8, 3.2, 3.2, 3.0],
        "elaboração própria. Custos unitários dependem das cotações da atividade A4 e do fornecedor de usinagem; "
        "a decisão considera custo, prazo, capacidade e competência.",
        font=9,
    )
    b.heading("4.2 Plano macro do processo produtivo", 2)
    b.table(
        "Plano macro do processo (sequência, posto, descrição e controle)",
        ["Seq.", "Posto", "Descrição", "Tempo", "Controle"],
        [["10", "Recebimento", "Receber a chapa e conferir o certificado", "Cronometrar em A5", "Lote e espessura"],
         ["20", "Bancada", "Inspecionar o lote", "Cronometrar em A5", "Visual e dimensional"],
         ["30", "Corte", "Fixar a chapa na mesa", "Cronometrar em A5", "Fixação sem folga"],
         ["40", "Corte", "Cortar o perfil", "0,9 a 1,2 min [17][18]", "Dimensão externa"],
         ["50", "Corte", "Usinar recortes e escala", "0,9 a 1,2 min [17][18]", "Geometria das funções"],
         ["60", "Bancada", "Chanfrar e lixar, com proteção respiratória", "Cronometrar em A5", "Rugosidade e borda"],
         ["70", "Bancada", "Limpar e inspecionar", "Cronometrar em A5", "Delaminação após o corte"],
         ["80", "Gravação", "Gravar a identificação do lote", "Cronometrar em A5", "Rastreabilidade"],
         ["90", "Embalagem", "Embalar", "Cronometrar em A5", "Proteção da borda"],
         ["100", "Expedição", "Liberar o lote", "Cronometrar em A5", "Registro de inspeção"]],
        [1.1, 2.2, 5.4, 3.3, 4.0],
        "elaboração própria. Os tempos de corte são derivados de parâmetros "
        "publicados (ver texto); os demais saem dos protótipos (A5) e dos testes (A6).",
        font=9,
    )
    b.para(
        "Os tempos de corte derivam de parâmetros públicos de fresagem CNC: 1.000 a 1.500 mm/min e 0,5 mm por "
        "passe em chapa de 2 mm [17]; 900 mm/min em chapa de 1,5 mm [18]. O contorno CR80 tem cerca de 279 mm; com "
        "quatro passes, são 1.117 mm de trajetória, ou 0,9 a 1,2 min por operação (recortes internos supostos "
        "iguais ao contorno, hipótese). O total de 2 a 2,5 min por cartão equivale a 62 a 83 horas-máquina no "
        "lote de 2.000. As etapas manuais não têm dado público e serão cronometradas no protótipo."
    )
    b.heading("4.3 Embalagem e análise de modos de falha", 2)
    b.para(
        "As seis tarefas de embalagem do Capítulo 8 resultam em: envio por correio em envelope "
        "rígido (distribuição); marcação de lote, material, limites de uso e garantia (formas e marcações); a "
        "borda como elemento crítico; berço interno que impede o contato com outros produtos (adaptação); caixa "
        "externa identificada (projeto); e embalagem em bancada, com conferência do lote (processo)."
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
    b.figure("fig_lancamento.png", "Os quatro processos de apoio começam antes da fase de lançamento.", width_cm=10.0,
             source="elaboração própria.")
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
        "O fluxo é: pedido, confirmação de pagamento, separação, inspeção final, embalagem, postagem, rastreio e "
        "confirmação de entrega. O piloto usa lote pequeno antes do lote de 2.000 unidades. O envio é pelos "
        "Correios, a partir da base do grupo; um centro de distribuição próprio não se justifica nesse volume."
    )
    b.heading("5.2 Atendimento ao cliente e assistência", 2)
    b.table(
        "Processos de atendimento, responsáveis e níveis de serviço propostos",
        ["Processo", "Canal", "Responsável", "Nível de serviço"],
        [["Dúvidas antes da compra", "Formulário e mensagens da plataforma", "Vendas e atendimento", "1ª resposta em 1 dia útil"],
         ["Pedido e entrega", "Plataforma e rastreio", "Vendas e atendimento", "Envio em até 2 dias úteis"],
         ["Arrependimento (7 dias)", "Formulário", "Vendas e atendimento", "Reembolso imediato [7]"],
         ["Defeito ou vício", "Formulário com fotos e lote", "Produção e qualidade", "Triagem técnica em 5 dias úteis"],
         ["Fim de vida", "Formulário e código de postagem", "Vendas e atendimento", "Ver Seção 6"]],
        [3.8, 4.4, 3.6, 4.2],
        "elaboração própria. Os níveis de serviço são propostas do grupo, "
        "revisáveis após o piloto.",
    )
    b.para(
        "Cada ocorrência é registrada em uma base única de clientes, com pedido, lote, motivo, evidência, "
        "decisão e prazo; casos de borda, delaminação ou falha funcional retornam ao projeto como pedido de "
        "mudança de engenharia. A garantia legal é de 90 dias para vício aparente em produto "
        "durável [7, art. 26]; o grupo propõe garantia contratual de 12 meses contra defeito de fabricação, a "
        "confirmar. O produto não tem peças substituíveis: a assistência é troca ou reembolso. O custo da fase é "
        f"de {brl(cost_by_id.loc['A8', 'activity_cost_brl'], 0)} (atividade A8), com {brl(cost_by_id.loc['A8', 'inputs_brl'], 0)} "
        "em insumos e material de divulgação e o restante em mão de obra de marketing."
    )

    # ------------------------------------------------------------- 6
    b.heading("6. Descontinuidade do produto", 1)
    b.heading("6.1 Fim de vida e logística reversa", 2)
    b.figure("fig_ciclo_vida.png", "Posição da descontinuidade no ciclo de vida: cada cliente devolve o cartão em "
             "um momento diferente.", width_cm=12.5, source="elaboração própria; esquemático, sem escala.")
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
        f"{pct(voucher_wins_until)}; o resultado é apertado e depende de pesos da equipe. A taxa de {pct(ref)} vem "
        "de um programa de recolhimento de outro produto, sem recompensa, que registrou cerca de 22% de devolução "
        "apesar de 92% de intenção declarada [12]; é cenário, não previsão. Recolhimento: os Correios vencem "
        f"enquanto o custo pesar até {pct(mail_wins_until)}; o serviço exige contrato do vendedor, quem autoriza a "
        "postagem paga [8] e o preço contratual só sai do contrato ou do simulador [9]. Reaproveitamento: o maior volume a destinar são os retalhos de usinagem "
        f"({br(flow_ref['machining_scrap_kg'], 1)} kg por lote, {br(flow_ref['scrap_to_returned_ratio'], 1)} vez a massa devolvida no cenário de {pct(ref)}); "
        "eles são segregados por lote e parte serve de corpo de prova. No Brasil só se localizou uma empresa "
        "com processo de recuperação de fibra de compósito curado, que não divulga lote mínimo nem preço [10]; "
        "por isso o material é estocado por lote até haver destinador confirmado, e a fibra de carbono não é "
        "apresentada como reciclável de forma automática. A reciclagem térmica retém cerca de 75% da resistência "
        "da fibra e a química, valores próximos aos da fibra virgem; a mecânica gera fibra curta, de baixo valor [11]. "
        "Há pesquisa brasileira em [15] e [16]."
    )
    b.heading("6.3 Operação, encerramento e custo", 2)
    b.para(
        f"O recolhimento é considerado encerrado quando forem recebidas {pct(mid)} das unidades vendidas "
        f"({br(p['lot_units'] * mid)} cartões do lote de {br(p['lot_units'])}) ou {br(p['horizon_months'])} meses "
        "após o fim das vendas, o que ocorrer primeiro, com revisão aos 12 meses. O fluxo completo está na Figura A.1; a Figura 10 "
        "e a Tabela 19 mostram dependências, prazos e custos."
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
        f"{int(sched['end_week'].max())} semanas e nove atividades. O conceito B (chanfro, escala gravada e "
        f"hexágonos no contorno) obteve a maior nota, {br(scores['B'], 2)}, e vence com o peso da segurança entre "
        f"{pct(lo_w)} e {pct(hi_w)}. O investimento se recupera com {be(54000, 199)} unidades a R$ 199, mas os "
        f"concorrentes custam bem menos e a pressão competitiva é {sa.porter_level(sa.porter_mean())} (nota "
        f"{br(sa.porter_mean(), 1)} de 5); a viabilidade depende de o mercado pagar pela diferenciação, o que só a "
        "pesquisa primária mostra."
    )
    b.para(
        "No fim de vida, recomenda-se o recolhimento por postagem reversa, voluntário (o produto não consta do "
        "art. 33 da Lei 12.305 [5]), com custo pago pela margem das vendas. A Tabela 20 lista as informações "
        "que ainda faltam para validar o projeto e a atividade em que cada uma será obtida."
    )
    b.table(
        "Informações que ainda faltam para validar o projeto",
        ["Informação", "O que já se sabe", "O que falta"],
        [["Preço da chapa de 500 × 500 × 2 mm (chapa e usinagem somam R$ 24 mil, 44% do custo)",
          "No varejo europeu: € 136,07 por chapa com IVA e € 111,58 em compras de 25 a 99 unidades [21]",
          "Cotação nacional em reais, com frete e impostos (A4 e A5)"],
         ["Tempo de cada operação", "Corte: 0,9 a 1,2 min por operação, calculado com parâmetros publicados [17][18]",
          "Tempos das etapas manuais, medidos no protótipo (A5)"],
         ["Preço dos concorrentes", "Wallet Ninja (US$ 20) e Leatherman Micra (US$ 49,95) [19][20]",
          "Preço da Victorinox SwissCard e preços em reais (A1)"],
         ["Obrigatoriedade do recolhimento (Lei 12.305)", "O produto não consta da lista do art. 33 [5]",
          "Parecer jurídico, sobretudo se o cartão tiver chip eletrônico"],
         ["Taxas de mão de obra, licença de CAD e bancada de ensaio", "Valores internos, sem fonte pública",
          "Definir com a instituição (A1 e A3)"],
         ["Origem do limite de R$ 60 mil", "Sem fonte pública", "Confirmar com o gerente do projeto"],
         ["Utilidade percebida e pesos das matrizes", "Sem dado ainda",
          "Entrevistas, teste de conceito e teste de uso (A1 e A6)"],
         ["Segurança e vida útil", "Sem dado ainda", "Ensaios de torque, borda e delaminação (A6)"],
         ["Frete reverso dos Correios (até 300 g)", "O preço depende de contrato e dos CEPs de origem e destino [8][9]",
          "Contrato ou simulador (A7)"],
         ["Destino dos retalhos e dos cartões devolvidos", "Sem resposta ainda do reciclador",
          "Aceite, lote mínimo, preço por kg e licença do reciclador; laudo do resíduo (A7)"]],
        [5.2, 5.8, 5.0],
        "elaboração própria. Preços consultados em 11 nov. 2026.",
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
        "[21] CARBONWEBSHOP. Carbon Panel 500x500x2mm. https://www.carbonwebshop.com/carbon-fiber-sheets/standard/carbon-panel-500x500x2mm/. Acesso em 11 nov. 2026.",
    ]
    for ref_text in refs:
        b.small(ref_text, 9.5, left=True)

    # ------------------------------------------------------------- apêndices
    b.appendix("A", "Detalhamento da Seção 6")
    b.figure("reverse_flow.png", "Fluxo de fim de vida: triagem, estoque por lote e destinação; os retalhos de usinagem entram "
             "no mesmo estoque do material devolvido.", width_cm=9.0, source="elaboração própria.")
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
        ["Preço líquido R$ 199, custo variável R$ 80, lote de 2.000", "Observada", "Seções 1.5 e 5"],
        ["Orçamento R$ 54 mil e reserva R$ 6 mil", "Observada", "Seção 2"],
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
            [11.6, 4.4], "elaboração própria. Como cada dado será fechado: Tabela 20.", font=9)
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
