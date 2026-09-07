from __future__ import annotations

from app.core.config import Settings
from app.core.enums import LLMProviderName
from app.llm.base import LLMMessage, LLMProvider, LLMProviderError
from app.llm.gemini_provider import GeminiProvider
from app.llm.groq_provider import GroqProvider
from app.llm.mock_provider import MockProvider


def build_provider(name: str, settings: Settings) -> LLMProvider:
    if name == LLMProviderName.GEMINI.value:
        return GeminiProvider(settings.gemini_api_key or "", settings.gemini_model)
    if name == LLMProviderName.GROQ.value:
        return GroqProvider(settings.groq_api_key or "", settings.groq_model)
    if name == LLMProviderName.MOCK.value:
        return MockProvider()
    raise ValueError(f"Unknown provider '{name}'")


class FallbackLLM:
    """
    Wraps an agent's preferred provider with a fallback chain:

        preferred provider -> settings.provider_fallback_order -> mock

    Mock is always the final, guaranteed-to-succeed link so the system never
    crashes purely because of an LLM outage (spec section 41).
    """

    def __init__(self, preferred: str, settings: Settings):
        self._settings = settings
        chain = [preferred] + [
            p for p in settings.provider_fallback_order if p != preferred
        ]
        if LLMProviderName.MOCK.value not in chain:
            chain.append(LLMProviderName.MOCK.value)
        self._chain = chain

    async def generate(
        self,
        system_prompt: str,
        messages: list[LLMMessage],
        temperature: float = 0.7,
    ) -> tuple[str, str]:
        """Returns (response_text, provider_name_actually_used)."""
        if self._settings.mock_llm:
            provider = build_provider(LLMProviderName.MOCK.value, self._settings)
            text = await provider.generate(system_prompt, messages, temperature)
            return text, LLMProviderName.MOCK.value

        last_error: Exception | None = None
        for name in self._chain:
            try:
                provider = build_provider(name, self._settings)
                text = await provider.generate(system_prompt, messages, temperature)
                return text, name
            except LLMProviderError as exc:
                last_error = exc
                continue
        # Should be unreachable since mock never raises, but keep it safe.
        raise LLMProviderError(f"All providers failed. Last error: {last_error}")
