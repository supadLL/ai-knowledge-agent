from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Protocol

from .models import RetrievalResult


class GenerationProvider(Protocol):
    name: str

    def generate(self, question: str, results: list[RetrievalResult]) -> str:
        """Generate an answer grounded in retrieved chunks."""


class LocalExtractiveGenerator:
    name = "local-extractive"

    def generate(self, question: str, results: list[RetrievalResult]) -> str:
        return answer_from_context(question, results)


class OpenAICompatibleChatGenerator:
    name = "openai-compatible-chat"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: int = 90,
        context_char_budget: int = 6000,
        name: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.context_char_budget = context_char_budget
        if name is not None:
            self.name = name

    def generate(self, question: str, results: list[RetrievalResult]) -> str:
        if not results:
            return answer_from_context(question, results)

        context = build_context(results, self.context_char_budget)
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Answer only from the provided local context. "
                        "Cite sources using the exact [filename#index] labels. "
                        "If the context is insufficient, say so plainly."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Question:\n{question}\n\nLocal context:\n{context}",
                },
            ],
            "temperature": 0.2,
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            message = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Generation request failed: HTTP {error.code} {message}") from error
        except urllib.error.URLError as error:
            raise RuntimeError(f"Generation request failed: {error.reason}") from error

        try:
            return str(body["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError(f"Generation response did not contain choices[0].message.content: {body}") from error


def create_generation_provider(
    provider: str,
    api_key: str | None = None,
    model: str = "gpt-4o-mini",
    base_url: str = "https://api.openai.com/v1",
    context_char_budget: int = 6000,
) -> GenerationProvider:
    normalized = provider.strip().lower()
    if normalized in {"local", "extractive", "local-extractive"}:
        return LocalExtractiveGenerator()
    if normalized in {"openai", "openai-compatible", "openai-compatible-chat"}:
        if api_key is None:
            raise ValueError(
                "AI_KNOWLEDGE_AGENT_GENERATION_API_KEY or OPENAI_API_KEY is required "
                "for the OpenAI-compatible generation provider."
            )
        return OpenAICompatibleChatGenerator(
            api_key=api_key,
            model=model,
            base_url=base_url,
            context_char_budget=context_char_budget,
        )
    raise ValueError(f"Unknown generation provider: {provider}")


def build_context(results: list[RetrievalResult], char_budget: int) -> str:
    remaining = max(0, char_budget)
    parts: list[str] = []
    for result in results:
        label = f"[{result.chunk.filename}#{result.chunk.index}]"
        content = result.chunk.content[:remaining]
        if not content:
            break
        part = f"{label}\n{content}"
        parts.append(part)
        remaining -= len(content)
    return "\n\n".join(parts)


def answer_from_context(question: str, results: list[RetrievalResult]) -> str:
    if not results:
        return (
            "I could not find relevant local context for that question. "
            "Index more documents or try a more specific query."
        )

    citations = [f"[{result.chunk.filename}#{result.chunk.index}]" for result in results]
    lead = (
        "Based on the indexed local documents, the most relevant evidence is "
        f"{', '.join(citations)}."
    )
    evidence = "\n\n".join(
        f"{citation} {result.chunk.content[:700]}"
        for citation, result in zip(citations, results, strict=False)
    )
    return f"{lead}\n\nQuestion: {question}\n\nEvidence:\n{evidence}"
