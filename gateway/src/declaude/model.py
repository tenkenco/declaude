"""Model backend client. The gateway speaks OpenAI-compatible chat completions,
which covers vLLM, Ollama (/v1), and most open-source serving stacks."""
from abc import ABC, abstractmethod

import httpx


class ModelClient(ABC):
    @abstractmethod
    async def complete(self, system: str, prompt: str) -> str: ...


class OpenAICompatClient(ModelClient):
    def __init__(self, base_url: str, model: str, api_key: str = "unused", timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = httpx.AsyncClient(timeout=timeout, headers={"Authorization": f"Bearer {api_key}"})

    async def complete(self, system: str, prompt: str) -> str:
        # A translation is roughly input-length; 2x headroom bounds tail latency
        # without ever truncating a reasonable rewrite. ~4 chars/token heuristic.
        max_tokens = max(256, min(8192, len(prompt) // 2))
        r = await self._client.post(
            f"{self.base_url}/chat/completions",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": max_tokens,
            },
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
