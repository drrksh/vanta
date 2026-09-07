from __future__ import annotations

from typing import AsyncIterator

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.investigation_service import InvestigationService
from app.database.session import get_sessionmaker
from app.scenarios.loader import ScenarioRegistry
from app.security.guards import check_admin_credentials


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_registry(request: Request) -> ScenarioRegistry:
    return request.app.state.registry


def get_service(request: Request) -> InvestigationService:
    return request.app.state.service


async def require_admin(
    x_admin_username: str = Header(default=""),
    x_admin_password: str = Header(default=""),
    settings: Settings = Depends(get_settings),
) -> None:
    if not check_admin_credentials(x_admin_username, x_admin_password, settings):
        raise HTTPException(status_code=401, detail="Admin authentication required")
