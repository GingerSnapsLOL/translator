"""Translation service backed by ``facebook/nllb-200-distilled-600M``.

The service exposes a thread-safe singleton that loads the tokenizer and model
exactly once and reuses them for every translation request.
"""

from __future__ import annotations

import logging
import threading
from functools import lru_cache

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class TranslationService:
    """Loads an NLLB seq2seq model once and translates text thread-safely.

    The heavy model/tokenizer are created lazily on the first call to
    :meth:`load` (or implicitly on the first :meth:`translate`). Loading is
    guarded by a lock so that, even under concurrent access, the model is only
    instantiated a single time. A second lock serializes inference because the
    tokenizer's ``src_lang`` is mutable shared state.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._device = torch.device(self._settings.device)

        self._load_lock = threading.Lock()
        self._inference_lock = threading.Lock()

        self._tokenizer: AutoTokenizer | None = None
        self._model: AutoModelForSeq2SeqLM | None = None

    @property
    def is_loaded(self) -> bool:
        """Return ``True`` once the model and tokenizer are in memory."""
        return self._model is not None and self._tokenizer is not None

    def load(self) -> None:
        """Load the tokenizer and model, at most once (thread-safe).

        Subsequent calls are no-ops. Intended to be invoked during application
        startup so the first request does not pay the loading cost.
        """
        if self.is_loaded:
            return

        with self._load_lock:
            # Double-checked: another thread may have loaded while we waited.
            if self.is_loaded:
                return

            model_name = self._settings.model_name
            logger.info("Loading translation model '%s' on device '%s'...", model_name, self._device)

            self._tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            model.to(self._device)
            model.eval()
            self._model = model

            logger.info("Translation model '%s' loaded successfully.", model_name)

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate ``text`` from ``source_lang`` to ``target_lang``.

        ``source_lang`` and ``target_lang`` are NLLB language codes such as
        ``eng_Latn``, ``fra_Latn`` or ``spa_Latn``.

        Returns the translated string. Raises :class:`ValueError` for empty
        input or an unknown target language code.
        """
        if not text or not text.strip():
            raise ValueError("`text` must be a non-empty string.")

        if not self.is_loaded:
            self.load()

        assert self._tokenizer is not None and self._model is not None  # for type checkers

        logger.debug("Translating %d chars: %s -> %s", len(text), source_lang, target_lang)

        # The tokenizer's `src_lang` and the subsequent encode/generate calls
        # share mutable state, so serialize inference for thread safety.
        with self._inference_lock:
            self._tokenizer.src_lang = source_lang

            forced_bos_token_id = self._tokenizer.convert_tokens_to_ids(target_lang)
            if forced_bos_token_id == self._tokenizer.unk_token_id:
                raise ValueError(f"Unknown target language code: {target_lang!r}")

            inputs = self._tokenizer(text, return_tensors="pt", truncation=True)
            inputs = {key: value.to(self._device) for key, value in inputs.items()}

            with torch.inference_mode():
                generated_tokens = self._model.generate(
                    **inputs,
                    forced_bos_token_id=forced_bos_token_id,
                    max_length=512,
                )

            translation = self._tokenizer.batch_decode(
                generated_tokens, skip_special_tokens=True
            )[0]

        return translation


@lru_cache(maxsize=1)
def get_translation_service() -> TranslationService:
    """Return the process-wide singleton :class:`TranslationService`.

    Cached so the same instance (and therefore the same loaded model) is shared
    across the whole application.
    """
    return TranslationService(get_settings())
