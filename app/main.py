from fastapi import FastAPI

from app.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.api_title, version=settings.api_version)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
