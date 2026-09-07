from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMMessage:
    role: str  # "user" | "assistant"
    content: str


class LLMProviderError(Exception):
    """Raised when a provider fails to produce a response."""


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        messages: list[LLMMessage],
        temperature: float = 0.7,
    ) -> str:
        raise NotImplementedError
