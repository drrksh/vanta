from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes_admin import router as admin_router
from app.api.routes_contestant import router as contestant_router
from app.core.config import get_settings
from app.core.investigation_service import InvestigationService
from app.database.session import init_db
from app.scenarios.loader import ScenarioRegistry


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await init_db()
    registry = ScenarioRegistry(settings.scenarios_dir)
    app.state.registry = registry
    app.state.service = InvestigationService(registry, settings)
    yield


app = FastAPI(title="VANTA", version="0.1.0", lifespan=lifespan)
app.include_router(contestant_router)
app.include_router(admin_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
