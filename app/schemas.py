"""Pydantic v2 request/response schemas for the translation API."""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator

from app.languages import is_supported

# NLLB / FLORES-200 language codes look like ``eng_Latn`` or ``ukr_Cyrl``:
# three lowercase letters, an underscore, then a capitalized 4-letter script.
LANG_CODE_PATTERN = r"^[a-z]{3}_[A-Z][a-z]{3}$"


class TranslationRequest(BaseModel):
    """Incoming payload for ``POST /translate``."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Text to translate.",
        examples=["Hello world"],
    )
    source_lang: str = Field(
        ...,
        pattern=LANG_CODE_PATTERN,
        description="Source language as a FLORES-200 code, e.g. 'eng_Latn'.",
        examples=["eng_Latn"],
    )
    target_lang: str = Field(
        ...,
        pattern=LANG_CODE_PATTERN,
        description="Target language as a FLORES-200 code, e.g. 'ukr_Cyrl'.",
        examples=["ukr_Cyrl"],
    )

    @field_validator("text")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value

    @model_validator(mode="after")
    def _languages_supported(self) -> Self:
        for field_name, code in (
            ("source_lang", self.source_lang),
            ("target_lang", self.target_lang),
        ):
            if not is_supported(code):
                raise ValueError(f"{field_name} '{code}' is not a supported language")
        return self


class TranslationResponse(BaseModel):
    """Response body for ``POST /translate``."""

    translation: str = Field(..., examples=["Привіт світ"])


class Language(BaseModel):
    """A single supported language."""

    code: str = Field(..., examples=["eng_Latn"])
    name: str = Field(..., examples=["English"])


class LanguagesResponse(BaseModel):
    """Response body for ``GET /languages``."""

    languages: list[Language]


class ErrorResponse(BaseModel):
    """Standard error envelope returned by the API's exception handlers."""

    detail: str = Field(..., examples=["Unsupported language code: 'xyz_Zzzz'"])
