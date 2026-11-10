"""Tests for the public IBGE fetcher error contract."""

from pathlib import Path

import pytest

from src import fetch_ibge


class FakeResponse:
    """Minimal response double for the requests client."""

    def __init__(self, payload: object, error: Exception | None = None) -> None:
        self.payload = payload
        self.error = error

    def raise_for_status(self) -> None:
        """Raise the configured HTTP error."""
        if self.error:
            raise self.error

    def json(self) -> object:
        """Return the configured JSON payload."""
        return self.payload


def test_sidra_query_propagates_http_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    error = RuntimeError("HTTP 403")
    monkeypatch.setattr(
        fetch_ibge.requests,
        "get",
        lambda *args, **kwargs: FakeResponse([], error),
    )

    with pytest.raises(RuntimeError, match="HTTP 403"):
        fetch_ibge.sidra_query("6579", "9324", "2024")


def test_sidra_query_rejects_non_tabular_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        fetch_ibge.requests,
        "get",
        lambda *args, **kwargs: FakeResponse({"error": "invalid"}),
    )

    with pytest.raises(ValueError, match="Unexpected SIDRA response"):
        fetch_ibge.sidra_query("6579", "9324", "2024")


def test_save_json_creates_utf8_payload(tmp_path: Path) -> None:
    target = tmp_path / "payload.json"

    fetch_ibge.save_json(target, [{"label": "São Paulo"}])

    assert "São Paulo" in target.read_text(encoding="utf-8")
