"""Run the CI steps on this machine, on the oldest supported Python and without Graphviz.

The GitHub runner uses Python 3.10 to 3.13 on Linux and has no Graphviz. A developer machine usually has one
newer Python and Graphviz, so code can pass every local test and still fail the CI (a backslash inside an
f-string expression is valid on 3.12 and a ``SyntaxError`` on 3.10 and 3.11). This script builds a throwaway
environment per version with ``uv`` under ``.ci-venvs/`` (git-ignored), then runs the two CI steps there:

    python scripts/ci_local.py              # Python 3.10, the oldest in the matrix
    python scripts/ci_local.py 3.10 3.13    # several versions
    python scripts/ci_local.py --rebuild    # recreate the environments

Exit code 0 means the CI steps pass on every requested version.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENVS = ROOT / ".ci-venvs"

# pytest with Graphviz hidden: the runner cannot find ``dot``, so figures fall back to the tracked PNG files
WITHOUT_GRAPHVIZ = (
    "import sys, pytest; import src.reverse_flow_diagram as r; r.find_dot = lambda: None; "
    "sys.exit(pytest.main(['-q', '-p', 'no:cacheprovider']))"
)


def run(command: list[str], quiet: bool = False) -> int:
    if not quiet:
        print("$", " ".join(command), flush=True)
    return subprocess.run(command, cwd=ROOT).returncode


def interpreter(version: str) -> Path:
    folder = VENVS / f"py{version.replace('.', '')}"
    return folder / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def ensure_environment(version: str, rebuild: bool) -> Path:
    python = interpreter(version)
    if rebuild and python.parent.parent.exists():
        shutil.rmtree(python.parent.parent)
    if python.exists():
        return python
    uv = [sys.executable, "-m", "uv"]
    if subprocess.run([*uv, "--version"], capture_output=True).returncode != 0:
        run([sys.executable, "-m", "pip", "install", "-q", "uv"])
    for step in (
        [*uv, "python", "install", version],
        [*uv, "venv", "--python", version, str(python.parent.parent)],
        [*uv, "pip", "install", "-q", "--python", str(python), "-r", "requirements.txt"],
    ):
        if run(step) != 0:
            raise SystemExit(f"could not prepare Python {version}")
    return python


def check(version: str, rebuild: bool) -> bool:
    python = ensure_environment(version, rebuild)
    print(f"\n=== Python {version} ===", flush=True)
    compiled = run([str(python), "-m", "compileall", "-q", "src", "tests", "scripts"]) == 0
    tested = run([str(python), "-c", WITHOUT_GRAPHVIZ]) == 0
    print(f"Python {version}: compile {'ok' if compiled else 'FAILED'}, tests {'ok' if tested else 'FAILED'}")
    return compiled and tested


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("versions", nargs="*", default=["3.10"], help="Python versions (default: 3.10)")
    parser.add_argument("--rebuild", action="store_true", help="recreate the environments")
    args = parser.parse_args()
    results = {version: check(version, args.rebuild) for version in args.versions}
    print("\n" + ", ".join(f"{v}: {'PASS' if ok else 'FAIL'}" for v, ok in results.items()))
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
