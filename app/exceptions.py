"""Domain-specific exceptions for the translation service.

Each exception carries the HTTP status code it should map to, so the API layer
can translate them into responses with a single generic handler.
"""

from __future__ import annotations


class TranslationError(Exception):
    """Base class for recoverable, client-facing translation errors."""

    status_code: int = 400

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class UnsupportedLanguageError(TranslationError):
    """Raised when a requested language code is not supported."""

    status_code: int = 422

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"Unsupported language code: {code!r}")


class ModelNotReadyError(TranslationError):
    """Raised when a translation is requested before the model is available."""

    status_code: int = 503

    def __init__(self, message: str = "Translation model is not ready.") -> None:
        super().__init__(message)
