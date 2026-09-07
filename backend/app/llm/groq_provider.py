from __future__ import annotations

import httpx

from app.llm.base import LLMMessage, LLMProvider, LLMProviderError

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"


class GroqProvider(LLMProvider):
    name = "groq"

    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise LLMProviderError("Groq API key not configured")
        self._api_key = api_key
        self._model = model

    async def generate(
        self,
        system_prompt: str,
        messages: list[LLMMessage],
        temperature: float = 0.7,
    ) -> str:
        chat_messages = [{"role": "system", "content": system_prompt}]
        for m in messages:
            role = "user" if m.role == "user" else "assistant"
            chat_messages.append({"role": role, "content": m.content})

        payload = {
            "model": self._model,
            "messages": chat_messages,
            "temperature": temperature,
            "max_tokens": 500,
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(GROQ_ENDPOINT, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"Groq request failed: {exc}") from exc
        except (KeyError, IndexError) as exc:
            raise LLMProviderError(f"Groq returned unexpected shape: {exc}") from exc
