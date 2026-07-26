"""Provider-compat logic for the OpenAI-compatible client (offline, no sockets).

The "works with any OpenAI-compatible host" claim rests on three behaviours:
credential/model precedence, tolerant JSON extraction, and the retry that drops
`response_format` for providers that reject it. All three are exercised here
with a stubbed urlopen — nothing in this file touches the network.
"""

from __future__ import annotations

import json
import urllib.error
from typing import Any

import pytest

from artificial_emotions.llm import (
    LLMClient,
    LLMSettings,
    _extract_json,
    resolve_llm_settings,
)

_LLM_ENV = (
    "LLM_API_KEY",
    "LLM_BASE_URL",
    "LLM_MODEL",
    "LLM_JUDGE_MODEL",
    "LLM_JSON_MODE",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
)


@pytest.fixture
def clean_env(monkeypatch):
    for name in _LLM_ENV:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


# --- credential / model resolution -------------------------------------------------


def test_no_key_and_remote_host_yields_no_settings(clean_env):
    """Remote providers need a key — returning None is what makes the LLM optional."""
    assert resolve_llm_settings() is None


@pytest.mark.parametrize(
    "base_url",
    [
        "http://localhost:11434/v1",
        "http://127.0.0.1:1234/v1",
        "http://0.0.0.0:8000/v1",
        "http://host.docker.internal:11434/v1",
    ],
)
def test_local_hosts_need_no_api_key(clean_env, base_url: str):
    settings = resolve_llm_settings(base_url=base_url)
    assert settings is not None
    assert settings.api_key == "local"
    assert settings.base_url == base_url.rstrip("/")


def test_llm_api_key_takes_precedence_over_openai_alias(clean_env):
    clean_env.setenv("OPENAI_API_KEY", "openai-key")
    clean_env.setenv("LLM_API_KEY", "llm-key")
    assert resolve_llm_settings().api_key == "llm-key"


def test_openai_alias_is_still_honored(clean_env):
    clean_env.setenv("OPENAI_API_KEY", "openai-key")
    assert resolve_llm_settings().api_key == "openai-key"


def test_explicit_api_key_env_name_wins(clean_env):
    clean_env.setenv("LLM_API_KEY", "generic")
    clean_env.setenv("MY_PROVIDER_KEY", "specific")
    assert resolve_llm_settings(api_key_env="MY_PROVIDER_KEY").api_key == "specific"


def test_model_precedence_arg_over_env(clean_env):
    clean_env.setenv("LLM_API_KEY", "k")
    clean_env.setenv("LLM_MODEL", "from-env")
    assert resolve_llm_settings(model="from-arg").model == "from-arg"
    assert resolve_llm_settings().model == "from-env"


def test_judge_model_only_applies_when_judging(clean_env):
    clean_env.setenv("LLM_API_KEY", "k")
    clean_env.setenv("LLM_MODEL", "generator")
    clean_env.setenv("LLM_JUDGE_MODEL", "judge")
    assert resolve_llm_settings(judge=True).model == "judge"
    assert resolve_llm_settings(judge=False).model == "generator"


def test_base_url_defaults_to_openai_and_strips_trailing_slash(clean_env):
    clean_env.setenv("LLM_API_KEY", "k")
    assert resolve_llm_settings().base_url == "https://api.openai.com/v1"
    assert resolve_llm_settings(base_url="https://x.example/v1/").base_url == "https://x.example/v1"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("1", True), ("true", True), ("TRUE", True), ("yes", True), ("0", False), ("", False)],
)
def test_json_mode_env_parsing(clean_env, raw: str, expected: bool):
    clean_env.setenv("LLM_API_KEY", "k")
    clean_env.setenv("LLM_JSON_MODE", raw)
    assert resolve_llm_settings().require_json_mode is expected


def test_from_env_returns_none_without_credentials(clean_env):
    assert LLMClient.from_env() is None


def test_from_settings_carries_configuration():
    client = LLMClient.from_settings(
        LLMSettings(api_key="k", model="m", base_url="https://x/v1", require_json_mode=True)
    )
    assert (client.api_key, client.model, client.base_url) == ("k", "m", "https://x/v1")
    assert client.require_json_mode is True
    assert client.timeout_s > 0


# --- tolerant JSON extraction ------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        '{"questions": []}',
        '```json\n{"questions": []}\n```',
        '```\n{"questions": []}\n```',
        'Sure! Here you go:\n{"questions": []}\nHope that helps.',
        '   \n {"questions": []}  ',
    ],
)
def test_extract_json_tolerates_common_model_wrappers(text: str):
    assert _extract_json(text) == {"questions": []}


def test_extract_json_rejects_a_response_with_no_object():
    with pytest.raises(ValueError, match="No JSON object"):
        _extract_json("I cannot help with that.")


def test_extract_json_rejects_a_non_object_root():
    with pytest.raises(ValueError):
        _extract_json("[1, 2, 3]")


# --- HTTP behaviour (stubbed transport) --------------------------------------------


class _FakeResponse:
    def __init__(self, body: dict[str, Any]):
        self._body = json.dumps(body).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _completion(content: str) -> dict[str, Any]:
    return {"choices": [{"message": {"content": content}}]}


def _install_urlopen(monkeypatch, handler):
    import artificial_emotions.llm as llm_mod

    monkeypatch.setattr(llm_mod.urllib.request, "urlopen", handler)


def test_chat_posts_system_and_user_messages(monkeypatch):
    seen: dict[str, Any] = {}

    def handler(req, timeout=None):
        seen["url"] = req.full_url
        seen["auth"] = req.headers.get("Authorization")
        seen["payload"] = json.loads(req.data.decode("utf-8"))
        return _FakeResponse(_completion("hello"))

    _install_urlopen(monkeypatch, handler)
    client = LLMClient("secret", "m", "https://api.example/v1")
    assert client.chat("SYS", "USR") == "hello"
    assert seen["url"] == "https://api.example/v1/chat/completions"
    assert seen["auth"] == "Bearer secret"
    roles = [m["role"] for m in seen["payload"]["messages"]]
    assert roles == ["system", "user"]
    assert "response_format" not in seen["payload"]


def test_json_mode_sends_response_format(monkeypatch):
    seen: dict[str, Any] = {}

    def handler(req, timeout=None):
        seen["payload"] = json.loads(req.data.decode("utf-8"))
        return _FakeResponse(_completion("{}"))

    _install_urlopen(monkeypatch, handler)
    LLMClient("k", "m", "https://api.example/v1", require_json_mode=True).chat("s", "u")
    assert seen["payload"]["response_format"] == {"type": "json_object"}


@pytest.mark.parametrize("status", [400, 404, 422])
def test_json_mode_retries_without_response_format_when_provider_rejects_it(monkeypatch, status):
    """Many local/OSS providers 400 on response_format — one retry keeps them usable."""
    attempts: list[dict[str, Any]] = []

    def handler(req, timeout=None):
        payload = json.loads(req.data.decode("utf-8"))
        attempts.append(payload)
        if len(attempts) == 1:
            raise urllib.error.HTTPError(req.full_url, status, "rejected", {}, None)
        return _FakeResponse(_completion('{"ok": true}'))

    _install_urlopen(monkeypatch, handler)
    client = LLMClient("k", "m", "https://api.example/v1", require_json_mode=True)
    assert client.chat_json("s", "u") == {"ok": True}
    assert len(attempts) == 2
    assert "response_format" in attempts[0]
    assert "response_format" not in attempts[1]


def test_other_http_errors_are_not_retried(monkeypatch):
    attempts: list[int] = []

    def handler(req, timeout=None):
        attempts.append(1)
        raise urllib.error.HTTPError(req.full_url, 500, "server error", {}, None)

    _install_urlopen(monkeypatch, handler)
    client = LLMClient("k", "m", "https://api.example/v1", require_json_mode=True)
    with pytest.raises(urllib.error.HTTPError):
        client.chat("s", "u")
    assert len(attempts) == 1


def test_no_retry_when_json_mode_is_off(monkeypatch):
    attempts: list[int] = []

    def handler(req, timeout=None):
        attempts.append(1)
        raise urllib.error.HTTPError(req.full_url, 400, "bad request", {}, None)

    _install_urlopen(monkeypatch, handler)
    with pytest.raises(urllib.error.HTTPError):
        LLMClient("k", "m", "https://api.example/v1").chat("s", "u")
    assert len(attempts) == 1


def test_openrouter_gets_attribution_headers(monkeypatch):
    seen: dict[str, Any] = {}

    def handler(req, timeout=None):
        seen["headers"] = {k.lower(): v for k, v in req.headers.items()}
        return _FakeResponse(_completion("ok"))

    _install_urlopen(monkeypatch, handler)
    LLMClient("k", "m", "https://openrouter.ai/api/v1").chat("s", "u")
    assert "http-referer" in seen["headers"]
    assert "x-title" in seen["headers"]


def test_non_openrouter_hosts_get_no_attribution_headers(monkeypatch):
    seen: dict[str, Any] = {}

    def handler(req, timeout=None):
        seen["headers"] = {k.lower(): v for k, v in req.headers.items()}
        return _FakeResponse(_completion("ok"))

    _install_urlopen(monkeypatch, handler)
    LLMClient("k", "m", "https://api.openai.com/v1").chat("s", "u")
    assert "http-referer" not in seen["headers"]


def test_chat_json_appends_a_json_only_instruction(monkeypatch):
    seen: dict[str, Any] = {}

    def handler(req, timeout=None):
        seen["payload"] = json.loads(req.data.decode("utf-8"))
        return _FakeResponse(_completion('```json\n{"a": 1}\n```'))

    _install_urlopen(monkeypatch, handler)
    result = LLMClient("k", "m", "https://api.example/v1").chat_json("SYS", "USR")
    assert result == {"a": 1}
    system_message = seen["payload"]["messages"][0]["content"]
    assert system_message.startswith("SYS")
    assert "JSON" in system_message
