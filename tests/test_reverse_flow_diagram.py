"""Tests for the workflow diagram generator (Mermaid, Graphviz, README sync)."""

import re
from pathlib import Path

import pytest

from src import reverse_flow_diagram as rfd

MERMAID_RESERVED = {"end", "graph", "subgraph", "flowchart", "default", "class", "style", "click"}
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module", params=["pt", "en"])
def flows(request) -> dict:
    return rfd.build_flows(lang=request.param)


def test_every_edge_endpoint_exists_and_ids_are_mermaid_safe(flows: dict) -> None:
    for flow in flows.values():
        ids = {n.ident for n in flow.nodes}
        assert len(ids) == len(flow.nodes)
        for edge in flow.edges:
            assert edge.src in ids and edge.dst in ids
        for ident in ids:
            assert re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", ident)
            assert ident.lower() not in MERMAID_RESERVED


def test_every_decision_exit_is_labelled(flows: dict) -> None:
    for flow in flows.values():
        for node in (n for n in flow.nodes if n.kind == "decision"):
            exits = [e for e in flow.edges if e.src == node.ident]
            assert len(exits) >= 2 and all(e.label for e in exits)


def test_flows_are_acyclic(flows: dict) -> None:
    for flow in flows.values():
        graph = {n.ident: [e.dst for e in flow.edges if e.src == n.ident] for n in flow.nodes}
        indegree = {k: 0 for k in graph}
        for targets in graph.values():
            for t in targets:
                indegree[t] += 1
        queue = [k for k, v in indegree.items() if v == 0]
        seen = 0
        while queue:
            node = queue.pop()
            seen += 1
            for t in graph[node]:
                indegree[t] -= 1
                if indegree[t] == 0:
                    queue.append(t)
        assert seen == len(graph)  # topological order reached every node: no cycle


def test_mermaid_and_dot_contain_same_labels(flows: dict) -> None:
    for flow in flows.values():
        mermaid, dot = rfd.to_mermaid(flow), rfd.to_dot(flow)
        assert mermaid.startswith("flowchart") and dot.startswith("digraph")
        for node in flow.nodes:
            first_line = node.label.split("\n")[0]
            assert first_line in mermaid and first_line in dot


def test_mermaid_never_emits_empty_class_assignments(flows: dict) -> None:
    for flow in flows.values():
        for line in rfd.to_mermaid(flow).splitlines():
            if line.strip().startswith("class "):
                assert len(line.split()) == 3, line  # class <ids> <name>;


def test_end_of_life_flow_uses_model_numbers() -> None:
    labels = " ".join(n.label for n in rfd.build_flows(lang="pt")["fim_de_vida"].nodes)
    assert "11,8 kg" in labels and "15,4 kg" in labels and "R$ 20" in labels


def test_english_flows_have_no_portuguese_and_same_structure() -> None:
    pt, en = rfd.build_flows(lang="pt"), rfd.build_flows(lang="en")
    portuguese_markers = ("ç", "ã", "õ", "é", "í", "ú", "Cartão", "Estoque", "Recebimento")
    for name in pt:
        assert [n.ident for n in pt[name].nodes] == [n.ident for n in en[name].nodes]
        assert [(e.src, e.dst, e.dashed) for e in pt[name].edges] == [(e.src, e.dst, e.dashed) for e in en[name].edges]
        text = " ".join([n.label + n.lane for n in en[name].nodes] + [e.label for e in en[name].edges])
        assert not any(marker in text for marker in portuguese_markers), text
    assert "11.8 kg" in " ".join(n.label for n in en["fim_de_vida"].nodes)


def test_phase_flow_mirrors_chapter_12_dependencies() -> None:
    edges = {(e.src, e.dst) for e in rfd.build_flows(lang="pt")["fase"].edges}
    assert edges == {("D1", "D2"), ("D2", "D3"), ("D3", "D4"), ("D2", "D5"), ("D5", "D6"),
                     ("D2", "D6"), ("D4", "D7"), ("D6", "D7")}


def test_png_renders_when_graphviz_is_available(tmp_path: Path) -> None:
    if rfd.find_dot() is None:
        pytest.skip("Graphviz is not installed")
    assert rfd.render_png(rfd.to_dot(rfd.build_flows()["motivo"]), tmp_path / "x.png")
    assert (tmp_path / "x.png").stat().st_size > 1000


def test_readme_blocks_are_in_sync_with_the_flow_spec() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for name, flow in rfd.build_flows(lang="en").items():
        assert rfd.readme_block(name, flow) in readme, (
            f"README block '{name}' is stale; run python src/reverse_flow_diagram.py")


def test_sync_readme_requires_markers(tmp_path: Path) -> None:
    path = tmp_path / "README.md"
    path.write_text("no markers here", encoding="utf-8")
    with pytest.raises(ValueError, match="markers"):
        rfd.sync_readme(path)
