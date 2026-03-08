"""LLM provider abstraction. Supports Anthropic native + any OpenAI-compatible API."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    text: str


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, system: str, user: str, max_tokens: int = 4096) -> LLMResponse:
        ...


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-20250514") -> None:
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        self.model = model

    def complete(self, system: str, user: str, max_tokens: int = 4096) -> LLMResponse:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return LLMResponse(text=response.content[0].text)


class OpenAICompatibleProvider(LLMProvider):
    """Works with OpenAI, DeepSeek, Gemini, Ollama, vLLM, and any OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o",
        base_url: str | None = None,
    ) -> None:
        from openai import OpenAI
        kwargs: dict = {}
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url
        self.client = OpenAI(**kwargs)
        self.model = model

    def complete(self, system: str, user: str, max_tokens: int = 4096) -> LLMResponse:
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return LLMResponse(text=response.choices[0].message.content)


# Well-known provider presets: (base_url, default_model, env_var_for_key)
PRESETS: dict[str, tuple[str | None, str, str]] = {
    "anthropic": (None, "claude-sonnet-4-20250514", "ANTHROPIC_API_KEY"),
    "openai":    (None, "gpt-4o", "OPENAI_API_KEY"),
    "deepseek":  ("https://api.deepseek.com", "deepseek-chat", "DEEPSEEK_API_KEY"),
    "gemini":    ("https://generativelanguage.googleapis.com/v1beta/openai/", "gemini-2.0-flash", "GEMINI_API_KEY"),
}


def create_provider(
    provider: str = "openai",
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
) -> LLMProvider:
    """Create an LLM provider by name or custom config.

    Args:
        provider: One of "anthropic", "openai", "deepseek", "gemini",
                  or any custom name (will use OpenAI-compatible).
        api_key:  API key. If None, reads from the preset's env var.
        model:    Model name override.
        base_url: Base URL override (for custom OpenAI-compatible endpoints).
    """
    import os

    preset = PRESETS.get(provider)

    if provider == "anthropic":
        preset_model = preset[1] if preset else "claude-sonnet-4-20250514"
        env_var = preset[2] if preset else "ANTHROPIC_API_KEY"
        return AnthropicProvider(
            api_key=api_key or os.environ.get(env_var),
            model=model or preset_model,
        )

    # Everything else goes through OpenAI-compatible
    if preset:
        preset_url, preset_model, env_var = preset
        return OpenAICompatibleProvider(
            api_key=api_key or os.environ.get(env_var),
            model=model or preset_model,
            base_url=base_url or preset_url,
        )

    # Fully custom provider
    return OpenAICompatibleProvider(
        api_key=api_key,
        model=model or "gpt-4o",
        base_url=base_url,
    )
