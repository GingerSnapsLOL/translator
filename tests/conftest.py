"""Shared pytest fixtures.

The API tests must never load the real ~600M NLLB model, so the translation
service is replaced with a mock. The mock is injected by patching the
``get_translation_service`` reference used inside ``app.main`` (both the
startup hook and the ``/translate`` endpoint resolve it there).
"""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app

EXPECTED_TRANSLATION = "Привіт світ"


@pytest.fixture
def mock_service() -> MagicMock:
    """A stand-in for ``TranslationService`` with no real model behind it."""
    service = MagicMock(name="TranslationService")
    service.load.return_value = None
    service.is_loaded = True
    service.translate.return_value = EXPECTED_TRANSLATION
    return service


@pytest.fixture
def client(mock_service: MagicMock, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """A ``TestClient`` (httpx-backed) wired to the mocked service."""
    monkeypatch.setattr(main_module, "get_translation_service", lambda: mock_service)

    # Entering the context manager runs the lifespan startup, which now calls
    # the mock's no-op ``load()`` instead of downloading the real model.
    with TestClient(app) as test_client:
        yield test_client
