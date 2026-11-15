---
name: ship
description: Commit and push this repository safely and confirm the CI result. Use whenever the user asks to commit, push or "deixar o repositório atualizado".
---

# Ship

The local machine differs from the CI (Python 3.12 with Graphviz versus Python 3.10 to 3.13 without Graphviz), so a
green local run is not enough.

1. `git status` and `git diff --stat`: confirm that only intended files changed and that nothing private is
   staged (`.docx`, `.pdf`, `assets/courses/`, `report/team.local.json`, `report/local_assets/`).
2. `python -m pytest -q` must pass. The `git_gate` hook also runs it before every commit.
3. **Before a push**: `python scripts/ci_local.py` (Python 3.10, no Graphviz). The hook runs it before every push.
   Add `3.13` to check the newest version as well.
4. Commit with an English message that says what and why, ending with the Co-Authored-By trailer from the harness.
   Use the identity already in the repository history (the GitHub noreply address).
5. **Push only when the user asked.** It needs the `gh` account `LucasTramonte`: check `gh auth status`; if the
   account is read-only, say so and stop; do not open a fork or a pull request on your own.
6. **After a push**: `gh run list --limit 3`; wait for the runs (`gh run watch <id>`); if one fails,
   `gh run view <id> --log-failed`, fix the cause, and say plainly that the first push failed.
7. Report what was verified and where: local tests, Python 3.10 run, CI result.
