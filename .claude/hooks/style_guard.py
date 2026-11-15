"""PostToolUse hook for Edit and Write: flag the mistakes this project has already paid for.

Claude Code passes the finished tool call as JSON on stdin. Exit code 2 sends stderr to the agent so it fixes the
file right away; any other exit code stays silent. Checks (each one comes from a real failure):

* report sources must contain no em or en dash (the report uses a colon);
* Python files must not use f-string forms that only Python 3.12 accepts (the CI also runs 3.10 and 3.11);
* README math must survive GitHub's Markdown pass: ``math`` fences and ``$`...`$`` only, no ``R$``.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT_SOURCES = {"src/generate_report_docx.py", "src/docx_builder.py", "src/strategic_analysis.py"}
DASHES = ("—", "–")


def f_string_problems(source: str) -> list[str]:
    spec = importlib.util.spec_from_file_location("compat", ROOT / "tests" / "test_python_compatibility.py")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(ROOT))
    spec.loader.exec_module(module)
    return [f"line {line}: {reason}" for line, reason in module.fstring_problems(source)]


def readme_problems(text: str) -> list[str]:
    problems = []
    if "$$" in text:
        problems.append("`$$` blocks break on GitHub: use ```math fences")
    fenced, in_math = False, False
    for number, line in enumerate(text.splitlines(), start=1):
        if line.strip() == "```math":
            fenced = in_math = True
            continue
        if line.lstrip().startswith("```"):
            fenced = not fenced
            in_math = False
            continue
        if in_math and ("*" in line or "%" in line):
            problems.append(f"line {number}: `*` or `%` inside a math fence (use \\star, or write the value without %)")
        if not fenced and "$" in re.sub(r"\$`[^`]+`\$", "", line):
            problems.append(f"line {number}: a stray `$` (write inline math as $`...`$ and amounts as BRL, never R$)")
    return problems


def main() -> int:
    try:
        event = json.load(sys.stdin)
        path = Path(event["tool_input"]["file_path"]).resolve()
        relative = path.relative_to(ROOT).as_posix()
    except (ValueError, KeyError, TypeError):
        return 0
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8", errors="replace")
    problems: list[str] = []
    if relative in REPORT_SOURCES:
        for number, line in enumerate(text.splitlines(), start=1):
            if any(d in line for d in DASHES):
                problems.append(f"line {number}: em or en dash in report text (use a colon)")
    if path.suffix == ".py" and relative.split("/")[0] in {"src", "tests", "scripts"}:
        import tokenize
        if hasattr(tokenize, "FSTRING_START"):
            problems += [f"f-string for Python 3.12 only, {item}" for item in f_string_problems(text)]
    if relative == "README.md":
        problems += readme_problems(text)
    if problems:
        print(f"{relative}: fix before going on (.claude/hooks/style_guard.py):\n  " + "\n  ".join(problems[:12]),
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
