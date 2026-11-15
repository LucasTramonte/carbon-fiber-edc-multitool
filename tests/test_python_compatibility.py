"""Guard against syntax that only works on the newest Python.

The CI matrix runs Python 3.10 to 3.13, but a developer machine often runs only the newest one. Before
Python 3.12 (PEP 701) an f-string replacement field could not contain a backslash, could not reuse the quote
character of the f-string, and could not hold a comment. Code using those forms runs on 3.12 and fails with a
``SyntaxError`` on 3.10 and 3.11, so the CI fails while every local test passes. This test reads the source
with the 3.12 tokenizer and reports those forms.
"""

from __future__ import annotations

import io
import sys
import tokenize
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCES = sorted([*ROOT.glob("src/**/*.py"), *ROOT.glob("tests/**/*.py"), *ROOT.glob("scripts/**/*.py"),
                 *ROOT.glob(".claude/hooks/*.py")])

pytestmark = pytest.mark.skipif(
    not hasattr(tokenize, "FSTRING_START"), reason="f-string tokens exist only on Python 3.12 and later"
)


def fstring_problems(source: str) -> list[tuple[int, str]]:
    """Return (line, reason) for every f-string replacement field that older Pythons reject."""
    problems: list[tuple[int, str]] = []
    stack: list[dict] = []  # one entry per f-string being read
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        kind, text, (line, _), _, _ = token
        if kind == tokenize.FSTRING_START:
            stack.append({"quote": text[-3:] if text.endswith(('"""', "'''")) else text[-1], "depth": 0})
            continue
        if kind == tokenize.FSTRING_END:
            stack.pop()
            continue
        if not stack:
            continue
        top = stack[-1]
        if kind == tokenize.OP and text == "{":
            top["depth"] += 1
        elif kind == tokenize.OP and text == "}":
            top["depth"] -= 1
        elif top["depth"] > 0:
            if kind == tokenize.COMMENT:
                problems.append((line, "comment inside an f-string expression"))
            elif kind == tokenize.STRING:
                body = text.lstrip("rRbBuUfF")
                if "\\" in text:
                    problems.append((line, f"backslash inside an f-string expression: {text}"))
                if body.startswith(top["quote"]):
                    problems.append((line, f"quote {top['quote']} reused inside an f-string expression"))
    return problems


def test_checker_detects_the_forms_that_break_python_310_and_311() -> None:
    assert fstring_problems('x = f"{a}"\n') == []
    assert fstring_problems("x = f'{a!r:>5}'\n") == []
    assert fstring_problems('x = f"{d[\'k\']}"\n') == []  # a different quote is allowed
    assert fstring_problems('x = f"{\'\\n\'.join(a)}"\n')  # backslash in the expression
    assert fstring_problems('x = f"{d["k"]}"\n')  # same quote reused
    assert fstring_problems('x = f"{a  # note\n}"\n')  # comment


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: str(p.relative_to(ROOT)))
def test_source_has_no_f_string_syntax_that_needs_python_312(path: Path) -> None:
    found = fstring_problems(path.read_text(encoding="utf-8"))
    assert not found, "\n".join(f"{path.name}:{line}: {reason}" for line, reason in found)


def test_running_python_is_not_the_only_one_supported() -> None:
    """Remind whoever reads a green local run that the CI also covers older versions."""
    assert sys.version_info >= (3, 10)
