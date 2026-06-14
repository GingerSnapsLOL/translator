"""Tests for the languages endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.languages import SUPPORTED_LANGUAGES


def test_languages_lists_all_supported(client: TestClient) -> None:
    response = client.get("/languages")

    assert response.status_code == 200

    payload = response.json()
    assert "languages" in payload

    returned = {item["code"]: item["name"] for item in payload["languages"]}
    assert returned == SUPPORTED_LANGUAGES


def test_languages_includes_expected_codes(client: TestClient) -> None:
    response = client.get("/languages")

    codes = {item["code"] for item in response.json()["languages"]}
    assert {"eng_Latn", "ukr_Cyrl", "rus_Cyrl", "pol_Latn"}.issubset(codes)
