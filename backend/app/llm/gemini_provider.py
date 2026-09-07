from __future__ import annotations

import httpx

from app.llm.base import LLMMessage, LLMProvider, LLMProviderError

GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise LLMProviderError("Gemini API key not configured")
        self._api_key = api_key
        self._model = model

    async def generate(
        self,
        system_prompt: str,
        messages: list[LLMMessage],
        temperature: float = 0.7,
    ) -> str:
        contents = [
            {
                "role": "user" if m.role == "user" else "model",
                "parts": [{"text": m.content}],
            }
            for m in messages
        ]
        payload = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "generationConfig": {"temperature": temperature, "maxOutputTokens": 500},
        }
        url = GEMINI_ENDPOINT.format(model=self._model)
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    url,
                    params={"key": self._api_key},
                    json=payload,
                )
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise LLMProviderError("Gemini returned no candidates")
            parts = candidates[0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts).strip()
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"Gemini request failed: {exc}") from exc
        except (KeyError, IndexError) as exc:
            raise LLMProviderError(f"Gemini returned unexpected shape: {exc}") from exc
