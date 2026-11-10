"""Gera tabelas e gráficos da análise regional do cartão multitool.

Os indicadores do IBGE são totais/estimativas oficiais por UF. A renda regional
é uma média ponderada descritiva, sem intervalo de confiança recalculado. Isso
evita atribuir incerteza amostral sem microdados, pesos e estratos do desenho
da pesquisa.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "dados"
FIGURES = ROOT / "dados" / "figuras"
SEED = 801


def main() -> None:
    regional = pd.read_csv(DATA / "indicadores_regiao_2024.csv")
    frame = regional.copy()
    population_state = pd.read_csv(DATA / "ibge_populacao_estados.csv")
    income_state = pd.read_csv(DATA / "ibge_renda_estados.csv")
    state = population_state[["D1C", "V"]].rename(
        columns={"D1C": "codigo_uf", "V": "populacao_uf"}
    )
    state["populacao_uf"] = pd.to_numeric(state["populacao_uf"])
    state = state.merge(
        income_state[["D1C", "V"]].rename(
            columns={"D1C": "codigo_uf", "V": "renda_uf"}
        ),
        on="codigo_uf",
    )
    state["renda_uf"] = pd.to_numeric(state["renda_uf"])
    region_by_uf = {
        uf: region
        for region, ufs in {
            "Norte": ["AC", "AP", "AM", "PA", "RO", "RR", "TO"],
            "Nordeste": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
            "Sudeste": ["ES", "MG", "RJ", "SP"],
            "Sul": ["PR", "RS", "SC"],
            "Centro-Oeste": ["DF", "GO", "MT", "MS"],
        }.items()
        for uf in ufs
    }
    uf_by_code = {
        11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO",
        21: "MA", 22: "PI", 23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL",
        28: "SE", 29: "BA", 31: "MG", 32: "ES", 33: "RJ", 35: "SP", 41: "PR",
        42: "SC", 43: "RS", 50: "MS", 51: "MT", 52: "GO", 53: "DF",
    }
    state["regiao"] = state["codigo_uf"].astype(int).map(uf_by_code).map(region_by_uf)

    required = {"codigo_uf", "populacao_uf", "renda_uf", "regiao"}
    if state[list(required)].isna().any().any():
        raise ValueError("Dados IBGE contêm valores ausentes nas colunas essenciais.")
    if state["codigo_uf"].duplicated().any() or len(state) != 27:
        raise ValueError("A junção IBGE não contém exatamente uma linha por UF.")
    frame.to_csv(DATA / "analise_regional_mercado_2024.csv", index=False, encoding="utf-8-sig")

    plt.figure(figsize=(10, 5.5))
    ax = plt.gca()
    bars = ax.bar(
        frame["regiao"],
        frame["rendimento_medio_ponderado_reais"],
        color="#263238",
    )
    ax.set(
        title="Rendimento domiciliar per capita por região: 2024",
        xlabel=None,
        ylabel="R$ por pessoa/mês (média ponderada)",
    )
    for bar, value in zip(bars, frame["rendimento_medio_ponderado_reais"]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 35,
            f"R$ {value:,.0f}".replace(",", "."),
            ha="center",
            va="bottom",
            fontsize=9,
        )
    plt.xticks(rotation=0)
    plt.tight_layout()
    FIGURES.mkdir(exist_ok=True)
    plt.savefig(FIGURES / "rendimento_regional_2024.png", dpi=180)
    plt.close()

    financial = pd.DataFrame(
        {
            "preco_liquido": [149, 199, 249],
            "custo_variavel_hipotetico": [80, 80, 80],
        }
    )
    financial["margem_contribuicao_unitaria"] = (
        financial["preco_liquido"] - financial["custo_variavel_hipotetico"]
    )
    financial["ponto_equilibrio_54000"] = np.ceil(
        54000 / financial["margem_contribuicao_unitaria"]
    ).astype(int)
    financial["ponto_equilibrio_60000"] = np.ceil(
        60000 / financial["margem_contribuicao_unitaria"]
    ).astype(int)
    financial.to_csv(DATA / "sensibilidade_financeira_planejamento.csv", index=False, encoding="utf-8-sig")

    fig, ax = plt.subplots(figsize=(9, 5.5))
    x = np.arange(len(financial))
    width = 0.36
    ax.bar(
        x - width / 2,
        financial["ponto_equilibrio_54000"],
        width,
        label="Orçamento planejado: R$ 54 mil",
        color="#37474f",
    )
    ax.bar(
        x + width / 2,
        financial["ponto_equilibrio_60000"],
        width,
        label="Limite com reserva: R$ 60 mil",
        color="#ef6c00",
    )
    ax.set(
        title="Unidades necessárias para recuperar o orçamento de desenvolvimento",
        xlabel="Preço líquido de venda por unidade (R$)",
        ylabel="Unidades no ponto de equilíbrio",
    )
    ax.set_xticks(x, [f"R$ {value:.0f}" for value in financial["preco_liquido"]])
    ax.legend()
    for bars in ax.containers:
        ax.bar_label(bars, fmt="%d", padding=3, fontsize=9)
    ax.text(
        0.02,
        0.98,
        "Hipótese: custo variável = R$ 80/unidade;\nsubstituir por cotação antes do piloto.",
        transform=ax.transAxes,
        va="top",
        fontsize=9,
        bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "#90a4ae"},
    )
    plt.tight_layout()
    plt.savefig(FIGURES / "ponto_equilibrio_sensibilidade.png", dpi=180)
    plt.close()

    activities = pd.DataFrame(
        [
            ["A1", "Requisitos e pesquisa primária", 1, 2, 2, "—", "Equipe (2)", 2500],
            ["A2", "Funções e matriz morfológica", 3, 1, 3, "A1", "Equipe (2)", 1500],
            ["A3", "CAD, arquitetura e tolerâncias", 4, 2, 5, "A2", "Projeto (2)", 5000],
            ["A4", "Cotação e compra de chapa", 3, 2, 4, "A1", "Compras (1)", 18000],
            ["A5", "Protótipos usinados", 6, 2, 7, "A3; A4", "Fornecedor", 6000],
            ["A6", "Testes e otimização", 8, 2, 9, "A5", "Equipe (2)", 4500],
            ["A7", "Processo, embalagem e inspeção", 10, 2, 11, "A6", "Produção (2)", 7000],
            ["A8", "Preparação do lote comercial", 12, 2, 13, "A7", "Produção (2)", 8000],
            ["A9", "Lançamento piloto e acompanhamento", 14, 2, 15, "A8", "Marketing (1)", 1500],
            ["A10", "Encerramento e lições aprendidas", 16, 1, 16, "A9", "Equipe (2)", 0],
        ],
        columns=["id", "atividade", "inicio_semana", "duracao_semanas", "termino_semana", "precedencia", "recursos", "custo_reais"],
    )
    activities.to_csv(DATA / "cronograma_precedencia_planejamento.csv", index=False, encoding="utf-8-sig")
    fig, ax = plt.subplots(figsize=(12, 7.5))
    y = np.arange(len(activities))
    critical_path = {"A1", "A2", "A3", "A5", "A6", "A7", "A8", "A9", "A10"}
    colors = [
        "#37474f" if activity_id in critical_path else "#90a4ae"
        for activity_id in activities["id"]
    ]
    ax.barh(
        y,
        activities["duracao_semanas"],
        left=activities["inicio_semana"] - 0.5,
        color=colors,
        edgecolor="#263238",
        height=0.62,
    )
    labels = [
        f'{activity_id}: {activity}'
        for activity_id, activity in zip(activities["id"], activities["atividade"])
    ]
    ax.set_yticks(y, labels=labels, fontsize=9)
    ax.invert_yaxis()
    ax.set(
        title="Cronograma-base do projeto",
        xlabel="Semana do projeto",
        ylabel="Atividade",
        xlim=(0.5, 16.5),
    )
    ax.set_xticks(np.arange(1, 17))
    ax.grid(axis="x", alpha=0.3)
    ax.set_axisbelow(True)
    ax.legend(
        handles=[
            plt.Rectangle((0, 0), 1, 1, color="#37474f"),
            plt.Rectangle((0, 0), 1, 1, color="#90a4ae"),
        ],
        labels=["Caminho crítico preliminar", "Atividade paralela"],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.08),
        ncol=2,
        fontsize=9,
    )
    fig.subplots_adjust(left=0.36, right=0.98, top=0.9, bottom=0.18)
    plt.savefig(FIGURES / "cronograma_gantt_planejamento.png", dpi=180)
    plt.close()

    print(f"Tabela salva em {DATA / 'analise_regional_mercado_2024.csv'}")
    print(f"Gráficos salvos em {FIGURES}")


if __name__ == "__main__":
    main()
