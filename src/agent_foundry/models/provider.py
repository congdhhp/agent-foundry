from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import quote
from urllib import error, request


class ChatModel(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> str:
        """Return assistant text for a chat-style request."""


class ModelUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class OpenAICompatibleChatModel:
    api_key: str
    model: str
    base_url: str = "https://api.openai.com/v1"
    timeout_seconds: int = 60
    temperature: float = 0.2
    max_retries: int = 2

    def complete(self, messages: list[dict[str, str]]) -> str:
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        payload = json.dumps(body).encode("utf-8")
        req = request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        raw = _send_with_retries(req, self.timeout_seconds, self.max_retries, "Model API")

        data = json.loads(raw)
        try:
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelUnavailableError(f"Unexpected model response shape: {raw[:500]}") from exc


@dataclass(frozen=True)
class GeminiGenerateContentChatModel:
    api_key: str
    model: str
    base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    timeout_seconds: int = 60
    temperature: float = 0.2
    max_retries: int = 2

    def complete(self, messages: list[dict[str, str]]) -> str:
        url = f"{self.base_url.rstrip('/')}/models/{quote(self.model, safe='')}:generateContent"
        body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": self._messages_to_prompt(messages)}],
                }
            ],
            "generationConfig": {
                "temperature": self.temperature,
            },
        }
        payload = json.dumps(body).encode("utf-8")
        req = request.Request(
            url,
            data=payload,
            headers={
                "x-goog-api-key": self.api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        raw = _send_with_retries(req, self.timeout_seconds, self.max_retries, "Gemini API")

        data = json.loads(raw)
        try:
            parts = data["candidates"][0]["content"]["parts"]
            return "".join(str(part.get("text", "")) for part in parts).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelUnavailableError(f"Unexpected Gemini response shape: {raw[:500]}") from exc

    def _messages_to_prompt(self, messages: list[dict[str, str]]) -> str:
        lines: list[str] = []
        for message in messages:
            role = message.get("role", "user").upper()
            content = message.get("content", "")
            lines.append(f"{role}:\n{content}")
        return "\n\n".join(lines)


def build_model_from_env(
    provider: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> ChatModel | None:
    provider_name = resolve_provider(provider)
    if provider_name is None:
        return None

    timeout = int(os.getenv("AGENT_FOUNDRY_MODEL_TIMEOUT", "60"))
    temperature = float(os.getenv("AGENT_FOUNDRY_TEMPERATURE", "0.2"))
    retries = int(os.getenv("AGENT_FOUNDRY_MODEL_RETRIES", "2"))

    if provider_name in {"openai", "openai-compatible"}:
        resolved_key = api_key or os.getenv("AGENT_FOUNDRY_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not resolved_key:
            return None
        return OpenAICompatibleChatModel(
            api_key=resolved_key,
            model=model or os.getenv("AGENT_FOUNDRY_MODEL", "gpt-4o-mini"),
            base_url=base_url or os.getenv("AGENT_FOUNDRY_BASE_URL", "https://api.openai.com/v1"),
            timeout_seconds=timeout,
            temperature=temperature,
            max_retries=retries,
        )

    if provider_name == "gemini":
        resolved_key = (
            api_key
            or os.getenv("AGENT_FOUNDRY_API_KEY")
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )
        if not resolved_key:
            return None
        return GeminiGenerateContentChatModel(
            api_key=resolved_key,
            model=model or os.getenv("AGENT_FOUNDRY_MODEL", "gemini-2.5-flash"),
            base_url=base_url or os.getenv("AGENT_FOUNDRY_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"),
            timeout_seconds=timeout,
            temperature=temperature,
            max_retries=retries,
        )

    raise ValueError(f"Unsupported model provider: {provider_name}")


def resolve_provider(provider: str | None = None) -> str | None:
    requested = provider or os.getenv("AGENT_FOUNDRY_PROVIDER")
    if requested:
        return requested.strip().lower()
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        return "gemini"
    if os.getenv("AGENT_FOUNDRY_API_KEY") or os.getenv("OPENAI_API_KEY"):
        return "openai-compatible"
    return None


def _send_with_retries(req: request.Request, timeout_seconds: int, max_retries: int, label: str) -> str:
    attempt = 0
    while True:
        try:
            with request.urlopen(req, timeout=timeout_seconds) as response:
                return response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            retryable = exc.code in {429, 500, 502, 503, 504}
            if retryable and attempt < max_retries:
                attempt += 1
                time.sleep(min(2**attempt, 5))
                continue
            raise ModelUnavailableError(f"{label} returned HTTP {exc.code}: {detail}") from exc
        except error.URLError as exc:
            if attempt < max_retries:
                attempt += 1
                time.sleep(min(2**attempt, 5))
                continue
            raise ModelUnavailableError(f"{label} unavailable: {exc.reason}") from exc
