"""FastAPI application entry point."""
from fastapi import FastAPI

from app.config import get_settings

settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="API for repository quality-engineering workflows.",
)


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Report that the API process is responding."""
    return {"status": "ok", "application": settings.app_name}
