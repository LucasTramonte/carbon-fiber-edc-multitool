"""PreToolUse hook for Bash: stop ``git commit`` and ``git push`` while the project checks fail.

Claude Code runs this before every Bash call and passes the call as JSON on stdin. Exit code 2 blocks the call
and shows stderr to the agent; any other exit code lets it through.

* ``git commit``: the whole test suite must pass (a red suite is never committed) and ignored or private files
  (.docx, .pdf, course material, local team data) must not be forced into the index.
* ``git push``: the CI steps must also pass on the oldest supported Python without Graphviz
  (``scripts/ci_local.py``), because a push triggers a CI run that fails for reasons invisible on this machine.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = re.compile(r"\.(docx|pdf)$|assets/courses/|report/team\.local\.json|report/local_assets/", re.IGNORECASE)


def project_python() -> str:
    venv = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return str(venv) if venv.exists() else sys.executable


def run(command: list[str], timeout: int) -> tuple[int, str]:
    try:
        done = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 1, f"timed out after {timeout} s: {' '.join(command)}"
    return done.returncode, (done.stdout + done.stderr)[-1800:]


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    command = event.get("tool_input", {}).get("command", "")
    is_commit = bool(re.search(r"\bgit\b[^;&|\n]*\bcommit\b", command))
    is_push = bool(re.search(r"\bgit\b[^;&|\n]*\bpush\b", command))
    if not (is_commit or is_push):
        return 0
    problems: list[str] = []

    if re.search(r"\bgit\b[^;&|\n]*\badd\b[^;&|\n]*(\s-f\b|--force)", command):
        problems.append("`git add --force` would bypass .gitignore; .docx, .pdf and course files stay local.")
    code, staged = run(["git", "diff", "--cached", "--name-only"], 30)
    # the English report in docs/report is published on purpose; every other .pdf and .docx is private
    forbidden = [name for name in staged.splitlines() if PRIVATE.search(name) and not name.startswith("docs/report/")]
    if forbidden:
        problems.append("private or generated files are staged: " + ", ".join(forbidden))

    code, output = run([project_python(), "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider"], 600)
    if code != 0:
        problems.append("the test suite fails:\n" + output)
    if is_push and not problems:
        code, output = run([project_python(), "scripts/ci_local.py"], 900)
        if code != 0:
            problems.append("the CI steps fail on Python 3.10 without Graphviz (scripts/ci_local.py):\n" + output)

    if problems:
        print("Blocked by .claude/hooks/git_gate.py. Fix this before the git command:\n\n" + "\n\n".join(problems),
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
