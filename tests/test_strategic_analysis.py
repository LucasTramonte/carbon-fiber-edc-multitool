"""SWOT and Porter's five forces: data integrity and figure rendering."""

from __future__ import annotations

import pytest

from src import strategic_analysis as sa


def test_swot_has_the_four_quadrants_with_five_items_each() -> None:
    assert set(sa.SWOT) == {"FORÇAS", "FRAQUEZAS", "OPORTUNIDADES", "AMEAÇAS"}
    assert all(len(items) == 5 for items in sa.SWOT.values())
    assert all(item.strip() for items in sa.SWOT.values() for item in items)


def test_porter_has_five_forces_scored_from_one_to_five() -> None:
    assert len(sa.PORTER) == 5
    assert all(1 <= score <= 5 for _, score, _ in sa.PORTER)
    assert all(why.strip() for _, _, why in sa.PORTER)


def test_porter_mean_matches_the_value_used_in_the_report() -> None:
    assert sa.porter_mean() == pytest.approx(3.6)
    assert sa.porter_level(3.6) == "média-alta"


@pytest.mark.parametrize("mean, level", [(4.2, "alta"), (3.5, "média-alta"), (3.0, "média"), (2.0, "baixa")])
def test_porter_level_bands(mean: float, level: str) -> None:
    assert sa.porter_level(mean) == level


def test_cost_share_cited_for_suppliers_is_consistent_with_the_project_budget() -> None:
    from src import project_plan as pp

    supplier_text = next(why for name, _, why in sa.PORTER if "fornecedores" in name)
    assert "44%" in supplier_text and "24.000" in supplier_text
    assert round(24_000 / pp.BUDGET * 100) == 44
    new_entrants = next(why for name, _, why in sa.PORTER if "entrantes" in name)
    assert f"{pp.BUDGET:,.0f}".replace(",", ".") in new_entrants


def test_texts_do_not_use_dashes() -> None:
    texts = [i for items in sa.SWOT.values() for i in items] + [why for _, _, why in sa.PORTER]
    assert not any(ch in text for text in texts for ch in "—–")


def test_figures_render(tmp_path) -> None:
    swot = sa.swot_figure(tmp_path / "swot.png")
    porter = sa.porter_figure(tmp_path / "porter.png")
    assert swot.stat().st_size > 10_000 and porter.stat().st_size > 10_000
