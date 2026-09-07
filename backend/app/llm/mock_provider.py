"""
Mock provider.

Used when MOCK_LLM=true, or as the final link in the fallback chain.
It never calls out to the network. It renders whatever facts were already
retrieved and injected into the prompt by the Agent layer -- it does not
invent anything, which incidentally makes it an extremely useful tool for
testing the Information Firewall in isolation from real model behaviour.

The "system_prompt" passed in already contains:
  - the agent's persona
  - the list of facts the agent is authorized to state
  - the contestant's latest message

We do simple deterministic text assembly: acknowledge the question, then
surface facts whose tags/text loosely match keywords in the question, else
give a generic "I don't know" grounded in the persona.
"""
from __future__ import annotations

import re

from app.llm.base import LLMMessage, LLMProvider


_STOPWORDS = {
    "the",
    "a",
    "an",
    "is",
    "are",
    "was",
    "were",
    "did",
    "do",
    "does",
    "what",
    "why",
    "how",
    "when",
    "where",
    "who",
    "to",
    "of",
    "in",
    "on",
    "at",
    "and",
    "or",
    "you",
    "your",
    "know",
    "about",
    "there",
    "any",
    "anything",
    "recently",
    "happened",
    "i",
    "it",
    "that",
    "this",
    "can",
    "tell",
    "me",
}


def _keywords(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


class MockProvider(LLMProvider):
    name = "mock"

    async def generate(
        self,
        system_prompt: str,
        messages: list[LLMMessage],
        temperature: float = 0.7,
    ) -> str:
        # Facts are injected by the agent layer as lines starting with "FACT:"
        fact_lines = [
            line[len("FACT:") :].strip()
            for line in system_prompt.splitlines()
            if line.strip().startswith("FACT:")
        ]
        persona_line = next(
            (
                line
                for line in system_prompt.splitlines()
                if line.strip().startswith("PERSONA:")
            ),
            "PERSONA: a helpful person",
        )

        last_user_msg = ""
        for m in reversed(messages):
            if m.role == "user":
                last_user_msg = m.content
                break

        q_keywords = _keywords(last_user_msg)

        scored = []
        for fact in fact_lines:
            f_keywords = _keywords(fact)
            overlap = q_keywords & f_keywords
            if overlap:
                # Score favors more overlapping keywords, then longer overlap
                # relative to the fact's own keyword count (specificity),
                # so a precisely-relevant fact outranks a loosely-related one.
                specificity = len(overlap) / max(1, len(f_keywords))
                scored.append((len(overlap), specificity, fact))

        if not q_keywords:
            return "Could you clarify what you're asking?"

        if scored:
            scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
            matched = [fact for _, _, fact in scored]
            if len(matched) == 1:
                return f"{matched[0]}."
            bullet = " Also, ".join(matched[:2])
            return f"{bullet}."

        return (
            "I'm not sure about that -- it's outside what I've observed. "
            "You might want to ask someone else."
        )
