"""Renderers for the reverse-logistics workflow diagrams (Mermaid, Graphviz).

One flow specification feeds two industry-standard "diagram as code" renderers:

* Mermaid (``docs/workflows/reverse_logistics_*.mmd``, English), which GitHub renders
  natively inside the README;
* Graphviz DOT (``docs/workflows/reverse_logistics_*.dot``, English); the
  Portuguese PNGs used in the report are rendered from the same specs
  (``src/flow_specs.py``).

Conventions (flowchart good practice, ISO 5807 style): rounded terminals,
diamonds only for decisions with every exit labelled, rectangles for actions,
cylinders for held stock, one reading direction (top to bottom), and every
arrow carries the condition or object it transports.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

try:
    from src.flow_specs import Edge, Flow, Node, build_flows  # noqa: F401
    from src import reverse_logistics_model as rl  # noqa: F401
except ImportError:  # pragma: no cover
    from flow_specs import Edge, Flow, Node, build_flows  # noqa: F401
    import reverse_logistics_model as rl  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / "docs" / "workflows"
DOT_CANDIDATES = (r"C:\Program Files\Graphviz\bin\dot.exe",)

DARK, ORANGE, LIGHT, RED = "#263238", "#ef6c00", "#eceff1", "#b71c1c"


def build_flow(p: dict | None = None, lang: str = "pt") -> Flow:
    """Return the end-of-life flow (single-flow convenience API)."""
    return build_flows(p, lang)["fim_de_vida"]


# ------------------------------------------------------------------ renderers
def _esc(text: str) -> str:
    return text.replace('"', "'")


def to_mermaid(flow: Flow) -> str:
    """Mermaid flowchart text (renders natively on GitHub)."""
    shape = {
        "start": '(["{}"])', "end": '(["{}"])', "decision": '{{"{}"}}',
        "process": '["{}"]', "highlight": '["{}"]', "store": '[("{}")]',
    }
    br = lambda s: _esc(s).replace("\n", "<br/>")  # noqa: E731
    lines = [f"flowchart {'LR' if flow.rankdir == 'LR' else 'TD'}"]
    lanes: dict[str, list[Node]] = {}
    for node in flow.nodes:
        lanes.setdefault(node.lane, []).append(node)

    def emit(node: Node, indent: str) -> str:
        return f"{indent}{node.ident}{shape[node.kind].format(br(node.label))}"

    for node in lanes.get("", []):
        lines.append(emit(node, "    "))
    for i, (lane, members) in enumerate(lanes.items()):
        if not lane:
            continue
        lines.append(f'    subgraph lane{i}["{lane}"]')  # ASCII ids: Mermaid-safe
        lines.append("        direction TB")
        lines += [emit(m, "        ") for m in members]
        lines.append("    end")
    for edge in flow.edges:
        arrow = "-.->" if edge.dashed else "-->"
        label = f'|"{br(edge.label)}"|' if edge.label else ""
        lines.append(f"    {edge.src} {arrow}{label} {edge.dst}")
    classes = {
        "hot": (f"fill:{ORANGE},stroke:{DARK},color:#fff", ("highlight",)),
        "term": (f"fill:{DARK},stroke:{DARK},color:#fff", ("start", "end")),
        "stock": (f"fill:{LIGHT},stroke:{DARK}", ("store",)),
    }
    for name, (css, kinds) in classes.items():
        members = [n.ident for n in flow.nodes if n.kind in kinds]
        if members:  # an empty `class  name;` line is invalid Mermaid
            lines.append(f"    classDef {name} {css};")
            lines.append(f"    class {','.join(members)} {name};")
    return "\n".join(lines) + "\n"


def to_dot(flow: Flow) -> str:
    """Graphviz DOT text, top-to-bottom, one cluster per return flow."""
    style = {
        "start": 'shape=box, style="rounded,filled", fillcolor="%s", fontcolor="white"' % DARK,
        "end": 'shape=box, style="rounded,filled", fillcolor="%s", fontcolor="white"' % DARK,
        "decision": 'shape=diamond, style=filled, fillcolor="white"',
        "process": 'shape=box, style="filled", fillcolor="white"',
        "highlight": 'shape=box, style="filled", fillcolor="%s", fontcolor="white"' % ORANGE,
        "store": 'shape=cylinder, style=filled, fillcolor="%s"' % LIGHT,
    }
    out = [
        "digraph reverse_logistics {",
        f'  graph [rankdir={flow.rankdir}, nodesep=0.35, ranksep=0.45, fontname="Arial", fontsize=13, '
        'labelloc=t, pad=0.3, newrank=true];',
        f'  node [fontname="Arial", fontsize=11, color="{DARK}", margin="0.14,0.08"];',
        f'  edge [fontname="Arial", fontsize=9.5, color="{DARK}", fontcolor="{DARK}"];',
    ]
    lanes: dict[str, list[Node]] = {}
    for node in flow.nodes:
        lanes.setdefault(node.lane, []).append(node)

    def emit(node: Node, indent: str) -> str:
        label = _esc(node.label).replace("\n", "\\n")
        return f'{indent}{node.ident} [label="{label}", {style[node.kind]}];'

    out += [emit(n, "  ") for n in lanes.get("", [])]
    for i, (lane, members) in enumerate(lanes.items()):
        if not lane:
            continue
        out.append(f"  subgraph cluster_{i} {{")
        out.append(f'    label="{lane}"; style="rounded,dashed"; color="{DARK}"; fontsize=12;')
        out += [emit(m, "    ") for m in members]
        out.append("  }")
    for edge in flow.edges:
        attrs = []
        if edge.label:
            attrs.append('label="%s"' % _esc(edge.label).replace("\n", "\\n"))
        if edge.dashed:
            attrs.append("style=dashed")
        out.append(f"  {edge.src} -> {edge.dst}" + (f" [{', '.join(attrs)}]" if attrs else "") + ";")
    out.append("}")
    return "\n".join(out) + "\n"


def find_dot() -> str | None:
    """Locate the Graphviz ``dot`` executable."""
    found = shutil.which("dot")
    if found:
        return found
    return next((c for c in DOT_CANDIDATES if Path(c).exists()), None)


def render_png(dot_text: str, png_path: Path, dpi: int = 170) -> bool:
    """Render DOT to PNG; return False when Graphviz is not installed."""
    dot = find_dot()
    if dot is None:
        return False
    png_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([dot, "-Tpng", f"-Gdpi={dpi}", "-o", str(png_path)], input=dot_text.encode("utf-8"),
                   check=True, timeout=60)
    return True


PNG_NAMES = {"motivo": "reverse_flow_motivo.png", "fim_de_vida": "reverse_flow.png",
             "fase": "reverse_flow_fase.png"}


def render_pngs(p: dict, png_dir: Path) -> bool:
    """Render the report PNGs in Portuguese; False when Graphviz is unavailable."""
    rendered = [render_png(to_dot(flow), png_dir / PNG_NAMES[name])
                for name, flow in build_flows(p, "pt").items()]
    return all(rendered)


def write_all(p: dict | None = None, workflow_dir: Path = WORKFLOW_DIR,
              png_dir: Path | None = None) -> dict[str, Path | None]:
    """Write English Mermaid/DOT sources and, when possible, the Portuguese PNGs.

    The sources in ``docs/workflows`` are English (README audience); the PNGs
    feed the Portuguese report. Returns ``"<flow>.<kind>" -> path`` (``None``
    for a PNG that could not be rendered because Graphviz is missing).
    """
    workflow_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Path | None] = {}
    for name, flow in build_flows(p, "en").items():
        mmd = workflow_dir / f"reverse_logistics_{name}.mmd"
        dot = workflow_dir / f"reverse_logistics_{name}.dot"
        mmd.write_text(to_mermaid(flow), encoding="utf-8")
        dot.write_text(to_dot(flow), encoding="utf-8")
        result[f"{name}.mermaid"], result[f"{name}.dot"] = mmd, dot
    for name, flow in build_flows(p, "pt").items():
        png = None
        if png_dir is not None and render_png(to_dot(flow), png_dir / PNG_NAMES[name]):
            png = png_dir / PNG_NAMES[name]
        result[f"{name}.png"] = png
    return result


README_PATH = ROOT / "README.md"


def readme_block(name: str, flow: Flow) -> str:
    """Marker-delimited Mermaid block that the README embeds for ``name``."""
    return (f"<!-- workflow:{name}:start -->\n```mermaid\n{to_mermaid(flow)}```\n"
            f"<!-- workflow:{name}:end -->")


def sync_readme(readme_path: Path = README_PATH, p: dict | None = None) -> bool:
    """Replace every marker-delimited (English) workflow block in the README."""
    import re

    text = original = readme_path.read_text(encoding="utf-8")
    for name, flow in build_flows(p, "en").items():
        pattern = re.compile(rf"<!-- workflow:{name}:start -->.*?<!-- workflow:{name}:end -->", re.S)
        if not pattern.search(text):
            raise ValueError(f"README is missing the workflow:{name} markers.")
        text = pattern.sub(lambda _m, n=name, f=flow: readme_block(n, f), text)
    if text != original:
        readme_path.write_text(text, encoding="utf-8")
    return text != original


def main() -> None:
    """Regenerate the workflow sources, the report PNGs and the README blocks."""
    for key, path in write_all(png_dir=ROOT / "outputs" / "visualizations").items():
        print(f"{key}: {path}")
    print("README updated:", sync_readme())


if __name__ == "__main__":
    main()
