"""LLMClient shim: routes LoopGym prompts to cursor-agent in an isolated bwrap sandbox.

Validity caveat: cursor-agent is an agent wrapper, not a raw model. Each call runs in ask mode
with tmpfs mounts for /workspace and /tmp plus an ephemeral ~/.cursor, so the agent cannot read
the repo, hidden tests, reference fixes, evaluator temp dirs, or other local agent state.
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

CURSOR_BIN = os.environ.get("CURSOR_AGENT_BIN", str(Path.home() / ".local/bin/cursor-agent"))
SANDBOX = Path(os.environ.get("CURSOR_LLM_SANDBOX", "/workspace/cursor-llm-sandbox"))
DEFAULT_MODEL = os.environ.get("CURSOR_LLM_MODEL", "gpt-5.3-codex")
ISOLATE = os.environ.get("CURSOR_LLM_ISOLATE", "1") != "0"
# Extra attempts after the first. Infra failures only; model content is never retried.
INFRA_RETRIES = int(os.environ.get("CURSOR_LLM_INFRA_RETRIES", "2"))
_LOG_LOCK = threading.Lock()


class InfraError(RuntimeError):
    """No model result after the infra retries are exhausted."""


def _classify_attempt(
    stdout: str, returncode: int,
) -> tuple[str, dict | None, BaseException | None]:
    """Classify one cursor-agent process. 'ok' is a model reply and is never retried."""
    text = (stdout or "").strip()
    data: dict | None = None
    parse_error: json.JSONDecodeError | None = None
    if text:
        try:
            parsed = json.loads(text.splitlines()[-1])
        except json.JSONDecodeError as exc:
            parse_error = exc
        else:
            if isinstance(parsed, dict):
                data = parsed
    if data is not None and data.get("is_error"):
        return "process_error", None, RuntimeError(f"cursor-agent error: {data}")
    if data is not None:
        return "ok", data, None
    if returncode != 0:
        if parse_error is not None:
            err: BaseException = parse_error
        elif not text:
            err = RuntimeError(f"cursor-agent exited {returncode} with no output")
        else:
            err = RuntimeError(f"cursor-agent exited {returncode} with no JSON")
        return "process_error", None, err
    if not text:
        return "no_output", None, RuntimeError("cursor-agent returned no output")
    if parse_error is not None:
        return "bad_json", None, parse_error
    return "bad_json", None, RuntimeError("cursor-agent returned no JSON object")


class CursorAgentLLM:
    def __init__(
        self,
        model: str | None = None,
        timeout: int = 180,
        *,
        log_path: Path | str | None = None,
        run_id: str | None = None,
    ) -> None:
        self.model = model if model is not None else DEFAULT_MODEL
        self.timeout = timeout
        self.tokens_used = 0
        self.calls: list[dict] = []
        self.infra_failures = 0
        self.log_path = Path(log_path) if log_path is not None else None
        self.run_id = run_id
        SANDBOX.mkdir(parents=True, exist_ok=True)

    def _prepare_workspace(self, role: str) -> Path:
        """Per-call workspace. The role is the instruction layer, not the user prompt."""
        SANDBOX.mkdir(parents=True, exist_ok=True)
        work = Path(tempfile.mkdtemp(prefix="call-", dir=SANDBOX))
        text = f"{role.rstrip()}\n"
        (work / "AGENTS.md").write_text(text, encoding="utf-8")
        rules = work / ".cursor" / "rules"
        rules.mkdir(parents=True)
        (rules / "role.mdc").write_text(
            f"---\nalwaysApply: true\n---\n\n{text}",
            encoding="utf-8",
        )
        return work

    def _run_once(self, cmd: list[str], cwd: Path | None = None) -> tuple[str, int]:
        """One sandboxed cursor-agent process. Fresh temp home. Raises TimeoutExpired on timeout."""
        work = cwd or SANDBOX
        run_cmd = cmd
        tmp_home: Path | None = None
        if ISOLATE:
            home = str(Path.home())
            tmp_home = Path(tempfile.mkdtemp(prefix=".home-", dir=SANDBOX))
            cursor_dir = tmp_home / ".cursor"
            cursor_dir.mkdir(parents=True, exist_ok=True)
            cfg = Path(home) / ".cursor" / "cli-config.json"
            if cfg.exists():
                shutil.copy2(cfg, cursor_dir / "cli-config.json")
            bind = ["--bind", str(SANDBOX), str(SANDBOX)]
            if work.resolve() != SANDBOX.resolve():
                bind += ["--bind", str(work), str(work)]
            run_cmd = [
                "bwrap", "--dev-bind", "/", "/", "--tmpfs", "/workspace", "--tmpfs", "/tmp",
                "--tmpfs", home, "--ro-bind", f"{home}/.local/bin", f"{home}/.local/bin",
                "--ro-bind", f"{home}/.local/share/cursor-agent", f"{home}/.local/share/cursor-agent",
                "--bind", f"{home}/.config/cursor", f"{home}/.config/cursor",
                "--bind", str(cursor_dir), f"{home}/.cursor",
                # Host public-plugin cache only; without it cursor-agent downloads plugins and hangs.
                *(
                    ["--ro-bind", f"{home}/.cursor/plugins", f"{home}/.cursor/plugins"]
                    if (Path(home) / ".cursor" / "plugins").is_dir()
                    else []
                ),
                *bind, "--chdir", str(work),
                "--setenv", "HOME", home, "--die-with-parent",
            ] + cmd
        try:
            proc = subprocess.Popen(
                run_cmd,
                cwd=work,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
            )
            try:
                stdout, _stderr = proc.communicate(timeout=self.timeout)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.communicate()
                raise
        finally:
            if tmp_home is not None:
                shutil.rmtree(tmp_home, ignore_errors=True)
        code = proc.returncode
        return stdout or "", 1 if code is None else code

    def _log_attempt(self, call_index: int, n: int, outcome: str, seconds: float) -> None:
        if self.log_path is None:
            return
        ident = self.run_id if self.run_id else "-"
        line = (
            f"{datetime.now(UTC).isoformat()} {ident} call={call_index} "
            f"attempt={n} outcome={outcome} seconds={seconds}\n"
        )
        with _LOG_LOCK:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(line)

    def _append_call(
        self,
        role: str,
        attempts: list[dict],
        usage: dict | None,
        reply: str,
        temperature: float | None,
    ) -> None:
        self.calls.append({
            "role": role,
            "reply": reply,
            "seconds": round(sum(a["seconds"] for a in attempts), 1),
            "usage": usage,
            "isolated": ISOLATE,
            "attempts": attempts,
            "temperature_requested": temperature,
            "temperature_applied": False,
        })

    def complete(
        self,
        prompt: str,
        role: str = "default",
        temperature: float | None = None,
    ) -> str:
        call_index = len(self.calls)
        work = self._prepare_workspace(role)
        cmd = [CURSOR_BIN, "-p", "--trust", "--mode", "ask", "--output-format", "json"]
        if self.model:
            cmd += ["--model", self.model]
        cmd.append(prompt)
        # No result: timeout, no output, unparsable output, or process error. Retry those.
        # A parsed model reply with content is final, including a non-zero exit that still
        # returned JSON without is_error. Temperature cannot be passed to cursor-agent.
        attempts: list[dict] = []
        last_error: BaseException | None = None
        try:
            for n in range(1, INFRA_RETRIES + 2):
                t0 = time.monotonic()
                try:
                    stdout, returncode = self._run_once(cmd, work)
                except subprocess.TimeoutExpired as exc:
                    seconds = round(time.monotonic() - t0, 1)
                    attempts.append({"n": n, "seconds": seconds, "outcome": "timeout"})
                    self._log_attempt(call_index, n, "timeout", seconds)
                    self.infra_failures += 1
                    last_error = exc
                    continue
                seconds = round(time.monotonic() - t0, 1)
                outcome, data, err = _classify_attempt(stdout, returncode)
                if outcome != "ok" or data is None:
                    attempts.append({"n": n, "seconds": seconds, "outcome": outcome})
                    self._log_attempt(call_index, n, outcome, seconds)
                    self.infra_failures += 1
                    last_error = err or RuntimeError(f"cursor-agent infra failure ({outcome})")
                    continue
                u = data.get("usage") or {}
                self.tokens_used += int(u.get("inputTokens", 0)) + int(u.get("outputTokens", 0))
                reply = data.get("result", "")
                if reply is None:
                    reply = ""
                elif not isinstance(reply, str):
                    reply = str(reply)
                attempts.append({"n": n, "seconds": seconds, "outcome": "ok"})
                self._log_attempt(call_index, n, "ok", seconds)
                self._append_call(role, attempts, u, reply, temperature)
                return reply
            if last_error is None:
                last_error = RuntimeError("cursor-agent infra retry produced no result")
            self._append_call(role, attempts, None, "", temperature)
            raise InfraError(str(last_error)) from last_error
        finally:
            shutil.rmtree(work, ignore_errors=True)
