"""Registry of languages supported by the translation service.

Codes are FLORES-200 identifiers (e.g. ``eng_Latn``) as used by the
``facebook/nllb-200-distilled-600M`` model.
"""

from __future__ import annotations

# Mapping of FLORES-200 code -> human-readable language name.
SUPPORTED_LANGUAGES: dict[str, str] = {
    "eng_Latn": "English",
    "ukr_Cyrl": "Ukrainian",
    "rus_Cyrl": "Russian",
    "pol_Latn": "Polish",
    "deu_Latn": "German",
    "fra_Latn": "French",
    "spa_Latn": "Spanish",
}


def is_supported(code: str) -> bool:
    """Return ``True`` if ``code`` is a supported language code."""
    return code in SUPPORTED_LANGUAGES
