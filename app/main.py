import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.config import get_settings
from app.languages import SUPPORTED_LANGUAGES
from app.schemas import (
    Language,
    LanguagesResponse,
    TranslationRequest,
    TranslationResponse,
)
from app.translator import get_translation_service

logging.basicConfig(level=logging.INFO)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the translation model once, during startup.
    get_translation_service().load()
    yield


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/languages", response_model=LanguagesResponse)
def languages() -> LanguagesResponse:
    return LanguagesResponse(
        languages=[
            Language(code=code, name=name)
            for code, name in SUPPORTED_LANGUAGES.items()
        ]
    )


@app.post("/translate", response_model=TranslationResponse)
def translate(request: TranslationRequest) -> TranslationResponse:
    service = get_translation_service()
    try:
        translation = service.translate(
            text=request.text,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return TranslationResponse(translation=translation)
