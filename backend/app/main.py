from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.architecture import router as architecture_router
from app.api.routes.parse import router as parse_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.schemas.common import HealthResponse

configure_logging()
settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(parse_router)
app.include_router(architecture_router)


@app.get("/health", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
    return HealthResponse(service=settings.app_name)
