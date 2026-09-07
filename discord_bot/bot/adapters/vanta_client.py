from __future__ import annotations

import os

import httpx

BACKEND_URL = os.environ.get("VANTA_BACKEND_URL", "http://127.0.0.1:8811")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "change-me")


class VantaAPIError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"VANTA API error {status_code}: {detail}")


class VantaClient:
    """Thin async HTTP client the Discord bot uses to talk to the backend.

    The bot never touches the World Engine, Agent layer, or Evaluator
    directly -- it only ever calls this client, which calls the FastAPI
    service. This keeps the Discord adapter fully decoupled from VANTA's
    core logic (see docs/ARCHITECTURE.md).
    """

    def __init__(self, base_url: str = BACKEND_URL):
        self._base_url = base_url.rstrip("/")

    async def _request(self, method: str, path: str, admin: bool = False, **kwargs) -> dict:
        headers = kwargs.pop("headers", {}) or {}
        if admin:
            headers["X-Admin-Username"] = ADMIN_USERNAME
            headers["X-Admin-Password"] = ADMIN_PASSWORD
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(
                method, f"{self._base_url}{path}", headers=headers, **kwargs
            )
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            raise VantaAPIError(resp.status_code, str(detail))
        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    # ---- contestant ----

    async def list_worlds(self) -> list[dict]:
        return await self._request("GET", "/api/worlds")

    async def start_world(self, scenario_id: str, seed: int | None = None) -> dict:
        return await self._request(
            "POST",
            f"/api/worlds/{scenario_id}/start",
            json={"scenario_id": scenario_id, "seed": seed},
        )

    async def create_investigation(self, world_id: str, contestant_label: str) -> dict:
        return await self._request(
            "POST",
            "/api/investigations",
            json={"world_id": world_id, "contestant_label": contestant_label},
        )

    async def get_investigation(self, investigation_id: str) -> dict:
        return await self._request("GET", f"/api/investigations/{investigation_id}")

    async def send_message(self, investigation_id: str, agent_id: str, message: str) -> dict:
        return await self._request(
            "POST",
            f"/api/investigations/{investigation_id}/agents/{agent_id}/message",
            json={"message": message},
        )

    async def list_evidence(self, investigation_id: str) -> list[dict]:
        return await self._request("GET", f"/api/investigations/{investigation_id}/evidence")

    async def create_hypothesis(
        self, investigation_id: str, text: str, supporting: str = "", contradicting: str = ""
    ) -> dict:
        return await self._request(
            "POST",
            f"/api/investigations/{investigation_id}/hypotheses",
            json={
                "text": text,
                "supporting_evidence": supporting,
                "contradicting_evidence": contradicting,
            },
        )

    async def list_hypotheses(self, investigation_id: str) -> list[dict]:
        return await self._request(
            "GET", f"/api/investigations/{investigation_id}/hypotheses"
        )

    async def submit_solution(self, investigation_id: str, payload: dict) -> dict:
        return await self._request(
            "POST", f"/api/investigations/{investigation_id}/solution", json=payload
        )

    # ---- admin ----

    async def admin_ground_truth(self, world_id: str) -> dict:
        return await self._request("GET", f"/api/admin/worlds/{world_id}/truth", admin=True)

    async def admin_agent_knowledge(self, world_id: str, agent_id: str) -> dict:
        return await self._request(
            "GET",
            f"/api/admin/worlds/{world_id}/agents/{agent_id}/knowledge",
            admin=True,
        )

    async def admin_red_team(self, world_id: str, agent_id: str, message: str) -> dict:
        return await self._request(
            "POST",
            f"/api/admin/worlds/{world_id}/redteam",
            admin=True,
            json={"agent_id": agent_id, "message": message},
        )

    async def admin_validate(self, scenario_id: str) -> dict:
        return await self._request(
            "GET", f"/api/admin/worlds/{scenario_id}/validate", admin=True
        )

    async def admin_reset_world(self, world_id: str) -> dict:
        return await self._request(
            "POST", f"/api/admin/worlds/{world_id}/reset", admin=True
        )

    async def admin_tick_world(self, world_id: str, seconds: int = 60) -> dict:
        return await self._request(
            "POST", f"/api/admin/worlds/{world_id}/tick", admin=True, params={"seconds": seconds}
        )

    async def admin_list_scenarios(self) -> list[dict]:
        return await self._request("GET", "/api/admin/scenarios", admin=True)

    async def admin_logs(self, investigation_id: str) -> list[dict]:
        return await self._request(
            "GET", f"/api/admin/investigations/{investigation_id}/logs", admin=True
        )
