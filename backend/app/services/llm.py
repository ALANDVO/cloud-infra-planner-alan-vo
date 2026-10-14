# backend/app/services/llm.py
"""Multi-provider LLM adapters with deterministic offline fallback."""
import os
import json
import httpx
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from ..core.config import settings


@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str
    usage: Optional[Dict[str, int]] = None


class LLMAdapter(ABC):
    """Abstract base for LLM adapters."""

    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 2048) -> LLMResponse:
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        pass


class OpenAICompatibleAdapter(LLMAdapter):
    """OpenAI-compatible adapter (OpenAI, LiteLLM, OpenRouter, Ollama, vLLM)."""

    def __init__(self):
        self.api_key = settings.llm_api_key or os.environ.get("OPENAI_API_KEY")
        self.base_url = settings.llm_base_url.rstrip("/")
        self.model = settings.llm_model

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 2048) -> LLMResponse:
        if not self.is_configured():
            raise RuntimeError("OpenAI-compatible adapter not configured: missing API key")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            provider="openai-compatible",
            model=self.model,
            usage=data.get("usage"),
        )


class AnthropicAdapter(LLMAdapter):
    """Anthropic Messages API adapter."""

    def __init__(self):
        self.api_key = settings.llm_api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.base_url = settings.llm_base_url.rstrip("/") or "https://api.anthropic.com"
        self.model = settings.llm_model

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 2048) -> LLMResponse:
        if not self.is_configured():
            raise RuntimeError("Anthropic adapter not configured: missing API key")

        # Convert messages format
        system = ""
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                anthropic_messages.append({"role": msg["role"], "content": msg["content"]})

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{self.base_url}/v1/messages", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        return LLMResponse(
            content=data["content"][0]["text"],
            provider="anthropic",
            model=self.model,
            usage={"input_tokens": data.get("usage", {}).get("input_tokens"), "output_tokens": data.get("usage", {}).get("output_tokens")},
        )


class GeminiAdapter(LLMAdapter):
    """Google Gemini generateContent adapter."""

    def __init__(self):
        self.api_key = settings.llm_api_key or os.environ.get("GEMINI_API_KEY")
        self.base_url = settings.llm_base_url.rstrip("/") or "https://generativelanguage.googleapis.com"
        self.model = settings.llm_model

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 2048) -> LLMResponse:
        if not self.is_configured():
            raise RuntimeError("Gemini adapter not configured: missing API key")

        # Convert to Gemini format
        contents = []
        for msg in messages:
            role = "user" if msg["role"] in ("user", "system") else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/v1beta/models/{self.model}:generateContent?key={self.api_key}",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        return LLMResponse(
            content=data["candidates"][0]["content"]["parts"][0]["text"],
            provider="gemini",
            model=self.model,
            usage=data.get("usageMetadata"),
        )


class OfflineAdapter(LLMAdapter):
    """Deterministic offline adapter for testing and demo mode."""

    def is_configured(self) -> bool:
        return True

    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 2048) -> LLMResponse:
        # Return deterministic response based on last user message
        last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        return LLMResponse(
            content=f"[OFFLINE] Generated template for: {last_user[:100]}",
            provider="offline",
            model="deterministic",
            usage={"prompt_tokens": len(last_user), "completion_tokens": 50},
        )


def get_llm_adapter() -> LLMAdapter:
    """Factory for LLM adapter based on configuration."""
    provider = settings.llm_provider.lower()

    if settings.demo_mode or provider == "offline":
        return OfflineAdapter()

    if provider in ("openai", "openrouter", "litellm", "ollama", "vllm"):
        return OpenAICompatibleAdapter()
    elif provider == "anthropic":
        return AnthropicAdapter()
    elif provider == "gemini":
        return GeminiAdapter()
    else:
        # Default to OpenAI-compatible
        return OpenAICompatibleAdapter()