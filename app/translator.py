"""Translation service backed by ``facebook/nllb-200-distilled-600M``.

The service exposes a thread-safe singleton that loads the tokenizer and model
exactly once and reuses them for every translation request.
"""

from __future__ import annotations

import gc
import logging
import threading
from functools import lru_cache

import torch
from transformers import (
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    PreTrainedModel,
    PreTrainedTokenizerBase,
)

from app.config import Settings, get_settings
from app.exceptions import ModelNotReadyError, UnsupportedLanguageError
from app.languages import is_supported

logger = logging.getLogger(__name__)


class TranslationService:
    """Loads an NLLB seq2seq model once and translates text thread-safely.

    The heavy model/tokenizer are created in :meth:`load` (typically during
    application startup). Loading is guarded by a lock so that, even under
    concurrent access, the model is only instantiated a single time. A second
    lock serializes inference because the tokenizer's ``src_lang`` is mutable
    shared state.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._device = torch.device(self._settings.device)

        self._load_lock = threading.Lock()
        self._inference_lock = threading.Lock()

        self._tokenizer: PreTrainedTokenizerBase | None = None
        self._model: PreTrainedModel | None = None

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
            logger.info(
                "Loading translation model",
                extra={"model_name": model_name, "device": str(self._device)},
            )

            self._tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            model.to(self._device)
            model.eval()
            self._model = model

            logger.info("Translation model loaded", extra={"model_name": model_name})

    def unload(self) -> None:
        """Release the model/tokenizer and free device memory (thread-safe).

        Used for graceful shutdown so resources are reclaimed deterministically.
        """
        with self._load_lock:
            if not self.is_loaded:
                return

            logger.info("Unloading translation model")
            self._model = None
            self._tokenizer = None

            if self._device.type == "cuda":
                torch.cuda.empty_cache()
            gc.collect()

            logger.info("Translation model unloaded")

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate ``text`` from ``source_lang`` to ``target_lang``.

        ``source_lang`` and ``target_lang`` are FLORES-200 codes such as
        ``eng_Latn`` or ``ukr_Cyrl``.

        Raises:
            ValueError: if ``text`` is empty or blank.
            UnsupportedLanguageError: if a language code is not supported.
            ModelNotReadyError: if the model has not been loaded.
        """
        if not text or not text.strip():
            raise ValueError("`text` must be a non-empty string.")

        for code in (source_lang, target_lang):
            if not is_supported(code):
                raise UnsupportedLanguageError(code)

        if not self.is_loaded:
            raise ModelNotReadyError

        tokenizer = self._tokenizer
        model = self._model
        assert tokenizer is not None and model is not None  # narrowed by is_loaded

        logger.debug(
            "Translating text",
            extra={
                "chars": len(text),
                "source_lang": source_lang,
                "target_lang": target_lang,
            },
        )

        # The tokenizer's `src_lang` and the subsequent encode/generate calls
        # share mutable state, so serialize inference for thread safety.
        with self._inference_lock:
            tokenizer.src_lang = source_lang

            forced_bos_token_id = tokenizer.convert_tokens_to_ids(target_lang)
            if forced_bos_token_id == tokenizer.unk_token_id:
                raise UnsupportedLanguageError(target_lang)

            encoded = tokenizer(text, return_tensors="pt", truncation=True)
            inputs = {key: value.to(self._device) for key, value in encoded.items()}

            with torch.inference_mode():
                generated_tokens = model.generate(
                    **inputs,
                    forced_bos_token_id=forced_bos_token_id,
                    max_length=self._settings.max_output_tokens,
                )

            translation: str = tokenizer.batch_decode(
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
