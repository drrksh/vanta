from __future__ import annotations

from app.agents.agent import _looks_like_injection  # single source of truth
from app.core.config import Settings


def is_suspicious_message(text: str) -> bool:
    return _looks_like_injection(text)


def check_admin_credentials(username: str, password: str, settings: Settings) -> bool:
    # Simple constant-ish comparison; fine for a prototype's single admin
    # account gated behind a private Discord role/category, not a public
    # auth system per spec section 42 (don't overengineer auth).
    return username == settings.admin_username and password == settings.admin_password
