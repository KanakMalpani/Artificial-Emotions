"""Provider-agnostic OpenAI-compatible chat client.

Works with OpenAI, OpenRouter, Groq, Together, Fireworks, Azure-compatible
gateways, local Ollama (`http://localhost:11434/v1`), LM Studio, vLLM, etc.
Any service that exposes `/chat/completions` with a Bearer token (or none for
local) can be used via env vars — no vendor lock-in.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LLMSettings:
    api_key: str
    model: str
    base_url: str
    require_json_mode: bool = False


def resolve_llm_settings(
    *,
    model: str | None = None,
    base_url: str | None = None,
    api_key_env: str | None = None,
    judge: bool = False,
) -> LLMSettings | None:
    """
    Resolve credentials from environment.

    Precedence for key: explicit env name → LLM_API_KEY → OPENAI_API_KEY
    Precedence for base: arg → LLM_BASE_URL → OPENAI_BASE_URL → api.openai.com
    Precedence for model: arg → (LLM_JUDGE_MODEL if judge) → LLM_MODEL → OPENAI_MODEL → gpt-4o-mini
    """
    key = ""
    if api_key_env:
        key = os.environ.get(api_key_env, "") or key
    key = key or os.environ.get("LLM_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")

    url = (
        (base_url or "").strip()
        or os.environ.get("LLM_BASE_URL", "").strip()
        or os.environ.get("OPENAI_BASE_URL", "").strip()
        or "https://api.openai.com/v1"
    )
    judge_env = os.environ.get("LLM_JUDGE_MODEL", "").strip() if judge else ""
    mdl = (
        (model or "").strip()
        or judge_env
        or os.environ.get("LLM_MODEL", "").strip()
        or os.environ.get("OPENAI_MODEL", "").strip()
        or "gpt-4o-mini"
    )

    # Local servers often need no key; remote usually do.
    local = any(
        h in url.lower() for h in ("localhost", "127.0.0.1", "0.0.0.0", "host.docker.internal")
    )
    if not key and not local:
        return None

    return LLMSettings(
        api_key=key or "local",
        model=mdl,
        base_url=url.rstrip("/"),
        require_json_mode=os.environ.get("LLM_JSON_MODE", "").lower() in ("1", "true", "yes"),
    )


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("No JSON object in model response")
    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    return data


class LLMClient:
    """Minimal chat client — no SDK dependency."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        *,
        require_json_mode: bool = False,
        timeout_s: float = 90.0,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.require_json_mode = require_json_mode
        self.timeout_s = timeout_s

    @classmethod
    def from_settings(cls, settings: LLMSettings) -> LLMClient:
        try:
            from artificial_emotions.config import llm_timeout_s

            timeout = llm_timeout_s()
        except Exception:  # noqa: BLE001 — config optional at import time
            timeout = 90.0
        return cls(
            settings.api_key,
            settings.model,
            settings.base_url,
            require_json_mode=settings.require_json_mode,
            timeout_s=timeout,
        )

    @classmethod
    def from_env(
        cls,
        *,
        model: str | None = None,
        base_url: str | None = None,
        api_key_env: str | None = None,
        judge: bool = False,
    ) -> LLMClient | None:
        settings = resolve_llm_settings(
            model=model, base_url=base_url, api_key_env=api_key_env, judge=judge
        )
        return cls.from_settings(settings) if settings else None

    def chat(self, system: str, user: str, *, temperature: float = 0.7) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if self.require_json_mode:
            payload["response_format"] = {"type": "json_object"}

        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        # Helpful for OpenRouter; ignored elsewhere.
        if "openrouter.ai" in self.base_url:
            headers["HTTP-Referer"] = "https://github.com/artificial-emotions"
            headers["X-Title"] = "Artificial Emotions"

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # Retry without response_format if provider rejects it.
            if self.require_json_mode and exc.code in (400, 404, 422):
                payload.pop("response_format", None)
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    f"{self.base_url}/chat/completions",
                    data=data,
                    headers=headers,
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
            else:
                raise

        return body["choices"][0]["message"]["content"]

    def chat_json(self, system: str, user: str, *, temperature: float = 0.7) -> dict[str, Any]:
        # Soft JSON instruction so Ollama/Groq/etc. work without json_object mode.
        system_json = (
            system + "\n\nRespond with a single valid JSON object only. No markdown fences."
        )
        content = self.chat(system_json, user, temperature=temperature)
        return _extract_json(content)
