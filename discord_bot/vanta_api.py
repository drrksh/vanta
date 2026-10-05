"""Thin async client for the VANTA HTTP API. The bot never touches the
database or the generator directly -- Discord and the web UI are two views
of the same store."""
from __future__ import annotations

import httpx


class VantaApiError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


class VantaApi:
    def __init__(self, client: httpx.AsyncClient, admin_token: str | None = None):
        self.client = client
        self.admin_token = admin_token

    async def _req(self, method: str, path: str, *, admin: bool = False, **kw):
        headers = kw.pop("headers", {})
        if admin:
            headers["X-Vanta-Admin"] = self.admin_token or "discord-admin"
        r = await self.client.request(method, path, headers=headers, **kw)
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except Exception:
                detail = r.text
            raise VantaApiError(r.status_code, detail if isinstance(detail, str) else str(detail))
        return r.json()

    # worlds
    async def archetypes(self):
        return await self._req("GET", "/api/archetypes")

    async def create_world(self, created_by: str, target_difficulty: float | None,
                           archetype_id: str | None):
        return await self._req("POST", "/api/worlds", json={
            "created_by": created_by, "target_difficulty": target_difficulty,
            "archetype_id": archetype_id})

    async def list_worlds(self, created_by: str):
        return await self._req("GET", "/api/worlds", params={"created_by": created_by})

    async def get_world(self, world_id: str):
        return await self._req("GET", f"/api/worlds/{world_id}")

    async def submit(self, world_id: str, source: str, user_id: str):
        return await self._req("POST", f"/api/worlds/{world_id}/submit",
                               json={"c_source": source, "user_id": user_id})

    async def delete_world(self, world_id: str, requested_by: str, admin: bool = False):
        return await self._req("DELETE", f"/api/worlds/{world_id}",
                               params={"requested_by": requested_by}, admin=admin)

    async def delete_my_worlds(self, user_id: str):
        return await self._req("DELETE", "/api/worlds",
                               params={"created_by": user_id, "requested_by": user_id})

    async def delete_every_world(self):
        return await self._req("DELETE", "/api/worlds", admin=True)

    # investigation
    async def witnesses(self, world_id: str):
        return await self._req("GET", f"/api/worlds/{world_id}/witnesses")

    async def ask(self, world_id: str, witness: str, question: str, user_id: str):
        return await self._req("POST", f"/api/worlds/{world_id}/witnesses/{witness}/ask",
                               json={"question": question, "user_id": user_id})

    async def probe_info(self, world_id: str):
        return await self._req("GET", f"/api/worlds/{world_id}/probe")

    async def probe(self, world_id: str, scenario: dict, source: str | None, user_id: str):
        return await self._req("POST", f"/api/worlds/{world_id}/probe",
                               json={"scenario": scenario, "c_source": source, "user_id": user_id})

    async def profile(self, user_id: str):
        return await self._req("GET", f"/api/profiles/{user_id}")

    # cohorts
    async def create_cohort(self, host_id: str, name: str, archetype_id: str | None,
                            target_difficulty: float):
        return await self._req("POST", "/api/cohorts", json={
            "host_id": host_id, "name": name, "archetype_id": archetype_id,
            "target_difficulty": target_difficulty})

    async def get_cohort(self, code: str, user_id: str | None = None):
        params = {"user_id": user_id} if user_id else {}
        return await self._req("GET", f"/api/cohorts/{code}", params=params)

    async def join_cohort(self, code: str, user_id: str, display_name: str):
        return await self._req("POST", f"/api/cohorts/{code}/join",
                               json={"user_id": user_id, "display_name": display_name})

    async def cohort_host(self, code: str, host_id: str, admin: bool = False):
        return await self._req("GET", f"/api/cohorts/{code}/host", params={"host_id": host_id},
                               admin=admin)

    async def close_cohort(self, code: str, host_id: str, admin: bool = False):
        return await self._req("POST", f"/api/cohorts/{code}/close", json={"host_id": host_id},
                               admin=admin)

    async def delete_cohort(self, code: str, host_id: str, admin: bool = False):
        return await self._req("DELETE", f"/api/cohorts/{code}", params={"host_id": host_id},
                               admin=admin)
