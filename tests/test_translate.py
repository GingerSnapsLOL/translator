"""Tests for the translation endpoint (using a mocked translation service)."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.exceptions import UnsupportedLanguageError


def test_translate_success(client: TestClient, mock_service: MagicMock) -> None:
    payload = {
        "text": "Hello world",
        "source_lang": "eng_Latn",
        "target_lang": "ukr_Cyrl",
    }

    response = client.post("/translate", json=payload)

    assert response.status_code == 200
    assert response.json() == {"translation": mock_service.translate.return_value}

    mock_service.translate.assert_called_once_with(
        text="Hello world",
        source_lang="eng_Latn",
        target_lang="ukr_Cyrl",
    )


def test_translate_blank_text_rejected(client: TestClient, mock_service: MagicMock) -> None:
    payload = {"text": "   ", "source_lang": "eng_Latn", "target_lang": "ukr_Cyrl"}

    response = client.post("/translate", json=payload)

    assert response.status_code == 422
    mock_service.translate.assert_not_called()


def test_translate_missing_field_rejected(client: TestClient) -> None:
    response = client.post("/translate", json={"text": "Hello world"})

    assert response.status_code == 422


def test_translate_malformed_language_code_rejected(
    client: TestClient, mock_service: MagicMock
) -> None:
    payload = {"text": "Hello world", "source_lang": "en", "target_lang": "ukr_Cyrl"}

    response = client.post("/translate", json=payload)

    assert response.status_code == 422
    mock_service.translate.assert_not_called()


def test_translate_unsupported_language_maps_to_422(
    client: TestClient, mock_service: MagicMock
) -> None:
    mock_service.translate.side_effect = UnsupportedLanguageError("ukr_Cyrl")

    payload = {"text": "Hello world", "source_lang": "eng_Latn", "target_lang": "ukr_Cyrl"}
    response = client.post("/translate", json=payload)

    assert response.status_code == 422
    assert "ukr_Cyrl" in response.json()["detail"]
