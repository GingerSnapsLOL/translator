"""FastAPI application for the translation service."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.exceptions import TranslationError
from app.languages import SUPPORTED_LANGUAGES
from app.logging_config import configure_logging
from app.schemas import (
    ErrorResponse,
    Language,
    LanguagesResponse,
    TranslationRequest,
    TranslationResponse,
)
from app.translator import get_translation_service

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Load the model on startup and release it on shutdown."""
    settings = get_settings()
    logger.info(
        "Starting application",
        extra={"title": settings.api_title, "version": settings.api_version},
    )

    service = get_translation_service()
    service.load()
    try:
        yield
    finally:
        logger.info("Shutting down; releasing model resources")
        service.unload()


def create_app() -> FastAPI:
    """Application factory: configure logging, routes, and error handling."""
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        lifespan=lifespan,
    )

    _register_exception_handlers(app)
    _register_routes(app)
    return app


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(TranslationError)
    async def _handle_translation_error(
        request: Request, exc: TranslationError
    ) -> JSONResponse:
        logger.warning(
            "Translation error",
            extra={"path": request.url.path, "detail": exc.message},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(detail=exc.message).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = jsonable_encoder(exc.errors())
        logger.info(
            "Request validation failed",
            extra={"path": request.url.path, "errors": errors},
        )
        return JSONResponse(status_code=422, content={"detail": errors})

    @app.exception_handler(Exception)
    async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception", extra={"path": request.url.path})
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(detail="Internal server error").model_dump(),
        )


def _register_routes(app: FastAPI) -> None:
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

    @app.post(
        "/translate",
        response_model=TranslationResponse,
        responses={
            422: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    def translate(request: TranslationRequest) -> TranslationResponse:
        translation = get_translation_service().translate(
            text=request.text,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
        )
        return TranslationResponse(translation=translation)


app = create_app()
