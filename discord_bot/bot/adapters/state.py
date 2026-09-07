from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

STATE_PATH = Path(os.environ.get("VANTA_BOT_STATE_PATH", "./bot_state.json"))


@dataclass
class InvestigationChannels:
    investigation_id: str
    world_id: str
    scenario_id: str
    guild_id: int
    category_id: int
    briefing_channel_id: int
    evidence_channel_id: int
    hypotheses_channel_id: int
    solution_channel_id: int
    # agent_id -> channel_id
    agent_channels: dict[str, int] = field(default_factory=dict)

    def agent_id_for_channel(self, channel_id: int) -> str | None:
        for agent_id, cid in self.agent_channels.items():
            if cid == channel_id:
                return agent_id
        return None


class BotState:
    """
    Tracks the mapping from Discord structures to VANTA investigations.

    Persisted to a small JSON file so the bot can restart without losing
    track of active investigation channels. This is intentionally simple
    (spec section 42: don't overengineer) -- durable investigation data
    itself lives in the VANTA backend's database, not here.
    """

    def __init__(self):
        self.investigations: dict[str, InvestigationChannels] = {}
        # guild_id -> admin category id (locked to admin role)
        self.admin_categories: dict[int, int] = {}
        self._load()

    def _load(self) -> None:
        if STATE_PATH.exists():
            try:
                raw = json.loads(STATE_PATH.read_text())
                for inv_id, data in raw.get("investigations", {}).items():
                    self.investigations[inv_id] = InvestigationChannels(**data)
                self.admin_categories = {
                    int(k): v for k, v in raw.get("admin_categories", {}).items()
                }
            except Exception:
                pass  # Corrupt/missing state file -- start fresh.

    def save(self) -> None:
        raw = {
            "investigations": {
                inv_id: vars(ic) for inv_id, ic in self.investigations.items()
            },
            "admin_categories": self.admin_categories,
        }
        STATE_PATH.write_text(json.dumps(raw, indent=2))

    def add_investigation(self, ic: InvestigationChannels) -> None:
        self.investigations[ic.investigation_id] = ic
        self.save()

    def find_by_channel(self, channel_id: int) -> tuple[InvestigationChannels, str] | None:
        """Returns (investigation_channels, agent_id) if channel_id is an agent channel."""
        for ic in self.investigations.values():
            agent_id = ic.agent_id_for_channel(channel_id)
            if agent_id:
                return ic, agent_id
        return None

    def find_by_category(self, category_id: int) -> InvestigationChannels | None:
        for ic in self.investigations.values():
            if ic.category_id == category_id:
                return ic
        return None

    def is_admin_category(self, guild_id: int, category_id: int) -> bool:
        return self.admin_categories.get(guild_id) == category_id
