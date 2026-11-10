# Contributing

## Development workflow

1. Create a focused branch from `main`.
2. Add or update tests before changing behavior.
3. Keep public data, generated outputs, and source code in their designated
   directories.
4. Run the local validation commands before opening a pull request.
5. Describe data sources, assumptions, and limitations in the pull request.

## Local checks

```powershell
python -m compileall -q src tests
python -m pytest -q
```

## Data and privacy

Only public, sanitized, traceable data belongs in the repository. Do not add
credentials, personal data, course materials, private marketplace exports, or
unpublished reports.
