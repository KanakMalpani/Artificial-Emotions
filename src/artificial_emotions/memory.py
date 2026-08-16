"""Persistent memory across processes — CLI continuity only.

What survives the process. Deliberately small and inspectable: JSON on disk,
human-readable, hand-editable. No database.

Guards:
- Opt-out via ``CURIOSITY_NO_MEMORY=1`` (no read, no write — today unchanged).
- Never on by default for MCP/HTTP; library ``explore`` defaults off.
- CLI explore may enable persistence; forgetting is easy and complete.

This records usage on the user's machine. See ``docs/LIMITS.md``.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from artificial_emotions.timeutil import utc_now_iso

__all__ = [
    "DEFAULT_MEMORY_DIR",
    "DEFAULT_MEMORY_PATH",
    "ENV_NO_MEMORY",
    "MAX_SESSIONS",
    "SCHEMA_VERSION",
    "MoodState",
    "PersistentMemory",
    "PreviousStepSnapshot",
    "SessionRecord",
    "default_memory_path",
    "memory_disabled",
    "persist_explore_if_enabled",
    "scars_plain",
    "affinities_plain",
]

SCHEMA_VERSION = "persistent_memory.v1"
ENV_NO_MEMORY = "CURIOSITY_NO_MEMORY"
MAX_SESSIONS = 200
DEFAULT_MEMORY_DIR = Path.home() / ".artificial_emotions"
DEFAULT_MEMORY_PATH = DEFAULT_MEMORY_DIR / "memory.json"

_PRIVACY_NOTICE = (
    "This file records Artificial Emotions CLI explore usage on this machine "
    "(session summaries, question encounter counts). It is local JSON you can "
    "read, edit, or delete. Opt out: CURIOSITY_NO_MEMORY=1. "
    "Commands: emotions memory show | forget <what> | reset. "
    "Never enabled by default on MCP/HTTP surfaces."
)

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def memory_disabled() -> bool:
    """True when ``CURIOSITY_NO_MEMORY`` opts out of all persistence."""
    return (os.environ.get(ENV_NO_MEMORY) or "").strip().lower() in _TRUTHY


def default_memory_path() -> Path:
    """Resolve the on-disk path (honours ``CURIOSITY_MEMORY_PATH`` override)."""
    override = (os.environ.get("CURIOSITY_MEMORY_PATH") or "").strip()
    if override:
        return Path(override).expanduser()
    return DEFAULT_MEMORY_PATH


@dataclass
class MoodState:
    """PAD carryover across processes (A2). Decays exponentially toward neutral."""

    pleasure: float = 0.0
    arousal: float = 0.0
    dominance: float = 0.0
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "pleasure": float(self.pleasure),
            "arousal": float(self.arousal),
            "dominance": float(self.dominance),
            "updated_at": self.updated_at,
        }

    def is_neutral(self, *, eps: float = 1e-6) -> bool:
        return abs(self.pleasure) <= eps and abs(self.arousal) <= eps and abs(self.dominance) <= eps

    def decayed(
        self,
        *,
        at: datetime | None = None,
        half_life_hours: float | None = None,
    ) -> MoodState:
        """Return PAD after exponential decay toward neutral (does not mutate)."""
        from artificial_emotions.affect import MOOD_HALF_LIFE_HOURS, decay_mood_pad

        half = MOOD_HALF_LIFE_HOURS if half_life_hours is None else float(half_life_hours)
        p, a, d, _factor = decay_mood_pad(
            self.pleasure,
            self.arousal,
            self.dominance,
            self.updated_at,
            now=at,
            half_life_hours=half,
        )
        return MoodState(
            pleasure=p,
            arousal=a,
            dominance=d,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_pad(
        cls,
        pad: dict[str, Any] | None,
        *,
        updated_at: str | None = None,
    ) -> MoodState:
        """Build from felt_simulation mood / mix pad / bare PAD dict."""
        from artificial_emotions.affect import pad_from_felt_or_mix

        axes = pad_from_felt_or_mix(pad) if pad else None
        if not axes:
            return cls(updated_at=updated_at)
        return cls(
            pleasure=float(axes["P"]),
            arousal=float(axes["A"]),
            dominance=float(axes["D"]),
            updated_at=updated_at,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> MoodState:
        if not data:
            return cls()
        # Accept both pleasure/arousal/dominance and P/A/D spellings.
        if "pleasure" in data or "arousal" in data or "dominance" in data:
            return cls(
                pleasure=float(data.get("pleasure") or 0.0),
                arousal=float(data.get("arousal") or 0.0),
                dominance=float(data.get("dominance") or 0.0),
                updated_at=data.get("updated_at"),
            )
        return cls.from_pad(data, updated_at=data.get("updated_at"))


@dataclass
class PreviousStepSnapshot:
    """Last explore step's features for the next session's step 1."""

    max_risk: float = 0.0
    hubris: float = 0.0
    top_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_risk": float(self.max_risk),
            "hubris": float(self.hubris),
            "top_id": str(self.top_id or ""),
        }

    def is_empty(self) -> bool:
        return (
            float(self.max_risk) == 0.0 and float(self.hubris) == 0.0 and not str(self.top_id or "")
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> PreviousStepSnapshot:
        if not data:
            return cls()
        return cls(
            max_risk=float(data.get("max_risk") or 0.0),
            hubris=float(data.get("hubris") or 0.0),
            top_id=str(data.get("top_id") or ""),
        )


@dataclass
class SessionRecord:
    """One completed CLI explore session (capped history)."""

    session_id: str
    started_at: str
    domain: str
    topic: str = ""
    steps_taken: int = 0
    primary_feeling: str = ""
    question_ids: list[str] = field(default_factory=list)
    best_question_id: str | None = None
    stopped_because: str = ""
    # B5 / dream: session-local trajectory excerpts for offline reanalysis.
    dead_ends: list[str] = field(default_factory=list)
    terms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "domain": self.domain,
            "topic": self.topic,
            "steps_taken": int(self.steps_taken),
            "primary_feeling": self.primary_feeling,
            "question_ids": list(self.question_ids),
            "best_question_id": self.best_question_id,
            "stopped_because": self.stopped_because,
            "dead_ends": list(self.dead_ends),
            "terms": list(self.terms),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionRecord:
        return cls(
            session_id=str(data.get("session_id") or ""),
            started_at=str(data.get("started_at") or ""),
            domain=str(data.get("domain") or ""),
            topic=str(data.get("topic") or ""),
            steps_taken=int(data.get("steps_taken") or 0),
            primary_feeling=str(data.get("primary_feeling") or ""),
            question_ids=[str(q) for q in (data.get("question_ids") or [])],
            best_question_id=data.get("best_question_id"),
            stopped_because=str(data.get("stopped_because") or ""),
            dead_ends=[str(d) for d in (data.get("dead_ends") or []) if d],
            terms=[str(t) for t in (data.get("terms") or []) if t],
        )


@dataclass
class PersistentMemory:
    """What survives the process. Deliberately small and inspectable."""

    path: Path = field(default_factory=default_memory_path)
    sessions: list[SessionRecord] = field(default_factory=list)
    mood_carryover: MoodState = field(default_factory=MoodState)
    previous_step: PreviousStepSnapshot = field(default_factory=PreviousStepSnapshot)
    scars: list[dict[str, Any]] = field(default_factory=list)
    affinities: list[dict[str, Any]] = field(default_factory=list)
    encounters: dict[str, int] = field(default_factory=dict)
    selections: dict[str, int] = field(default_factory=dict)
    privacy_ack: bool = False
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def load(cls, path: Path | str | None = None) -> PersistentMemory:
        """Load from disk, or return an empty memory if missing / disabled."""
        resolved = Path(path) if path is not None else default_memory_path()
        mem = cls(path=resolved)
        if memory_disabled():
            return mem
        if not resolved.is_file():
            return mem
        try:
            raw = json.loads(resolved.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            corrupt = resolved.with_name(resolved.stem + ".corrupt" + resolved.suffix)
            try:
                os.replace(resolved, corrupt)
            except OSError:
                # Still return empty mem; warn even if we could not move the file.
                print(
                    f"warning: corrupt memory at {resolved} ({exc}); "
                    f"could not preserve as {corrupt}",
                    file=sys.stderr,
                    flush=True,
                )
            else:
                print(
                    f"warning: corrupt memory at {resolved} ({exc}); preserved as {corrupt}",
                    file=sys.stderr,
                    flush=True,
                )
            return mem
        if not isinstance(raw, dict):
            return mem
        mem.schema_version = str(raw.get("schema_version") or SCHEMA_VERSION)
        mem.privacy_ack = bool(raw.get("privacy_ack"))
        mem.sessions = [
            SessionRecord.from_dict(s) for s in (raw.get("sessions") or []) if isinstance(s, dict)
        ]
        mem.mood_carryover = MoodState.from_dict(
            raw.get("mood_carryover") if isinstance(raw.get("mood_carryover"), dict) else None
        )
        mem.previous_step = PreviousStepSnapshot.from_dict(
            raw.get("previous_step") if isinstance(raw.get("previous_step"), dict) else None
        )
        mem.scars = [s for s in (raw.get("scars") or []) if isinstance(s, dict)]
        mem.affinities = [a for a in (raw.get("affinities") or []) if isinstance(a, dict)]
        enc = raw.get("encounters") or {}
        if isinstance(enc, dict):
            mem.encounters = {str(k): int(v) for k, v in enc.items()}
        if "selections" in raw and isinstance(raw.get("selections"), dict):
            mem.selections = {str(k): int(v) for k, v in raw["selections"].items()}
        else:
            # Pre-A6 files: rebuild picks from session bests.
            mem.selections = mem._selections_from_sessions()
        mem._cap_sessions()
        return mem

    def _selections_from_sessions(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for session in self.sessions:
            qid = session.best_question_id
            if qid:
                key = str(qid)
                counts[key] = counts.get(key, 0) + 1
        return counts

    def _cap_sessions(self) -> None:
        if len(self.sessions) > MAX_SESSIONS:
            self.sessions = self.sessions[-MAX_SESSIONS:]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version or SCHEMA_VERSION,
            "privacy_notice": _PRIVACY_NOTICE,
            "privacy_ack": bool(self.privacy_ack),
            "sessions": [s.to_dict() for s in self.sessions],
            "mood_carryover": self.mood_carryover.to_dict(),
            "previous_step": self.previous_step.to_dict(),
            "scars": list(self.scars),
            "affinities": list(self.affinities),
            "encounters": dict(sorted(self.encounters.items())),
            "selections": dict(sorted(self.selections.items())),
            "max_sessions": MAX_SESSIONS,
            "path": str(self.path),
        }

    def save(self) -> bool:
        """Write JSON to disk. Returns False when memory is disabled (no-op)."""
        if memory_disabled():
            return False
        self._cap_sessions()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        first_write = not self.path.is_file()
        if first_write or not self.privacy_ack:
            self.privacy_ack = True
        payload = self.to_dict()
        # path is runtime metadata — keep the file self-describing without it
        payload.pop("path", None)
        text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, self.path)
        if first_write:
            print(
                f"privacy: wrote local memory at {self.path}\n  {_PRIVACY_NOTICE}",
                file=sys.stderr,
                flush=True,
            )
        return True

    def record_session(
        self,
        *,
        domain: str,
        topic: str = "",
        steps_taken: int = 0,
        primary_feeling: str = "",
        question_ids: list[str] | None = None,
        best_question_id: str | None = None,
        stopped_because: str = "",
        session_id: str | None = None,
        started_at: str | None = None,
        dead_ends: list[str] | None = None,
        terms: list[str] | None = None,
    ) -> SessionRecord:
        """Append a session, update encounters, enforce the session cap."""
        qids = [str(q) for q in (question_ids or []) if q]
        record = SessionRecord(
            session_id=session_id or uuid.uuid4().hex[:12],
            started_at=started_at or utc_now_iso(),
            domain=str(domain),
            topic=str(topic or ""),
            steps_taken=int(steps_taken),
            primary_feeling=str(primary_feeling or ""),
            question_ids=qids,
            best_question_id=best_question_id,
            stopped_because=str(stopped_because or ""),
            dead_ends=[str(d) for d in (dead_ends or []) if d],
            terms=[str(t) for t in (terms or []) if t],
        )
        self.sessions.append(record)
        for qid in qids:
            self.encounters[qid] = self.encounters.get(qid, 0) + 1
        if record.best_question_id:
            bid = str(record.best_question_id)
            self.selections[bid] = self.selections.get(bid, 0) + 1
        self._cap_sessions()
        return record

    def record_explore_result(self, result: dict[str, Any]) -> SessionRecord | None:
        """Fold an ``explore()`` return value into memory. No-op if disabled."""
        if memory_disabled():
            return None
        trail = result.get("trajectory") or {}
        qids: list[str] = []
        for step in trail.get("steps") or []:
            for qid in step.get("new_question_ids") or []:
                if qid and qid not in qids:
                    qids.append(str(qid))
            top = step.get("top_question_id")
            if top and top not in qids:
                qids.append(str(top))
        dead_ends = [str(d) for d in (trail.get("dead_ends") or []) if d]
        terms: list[str] = []
        for entry in trail.get("mined_terms") or []:
            if isinstance(entry, dict) and entry.get("term"):
                t = str(entry["term"])
                if t and t not in terms:
                    terms.append(t)
            elif isinstance(entry, str) and entry and entry not in terms:
                terms.append(entry)
        best = result.get("best_found") or {}
        mix = result.get("final_mix") or {}
        record = self.record_session(
            domain=str(result.get("domain_started") or ""),
            topic=str(result.get("topic") or ""),
            steps_taken=int(result.get("steps_taken") or 0),
            primary_feeling=str(mix.get("primary") or ""),
            question_ids=qids,
            best_question_id=best.get("question_id"),
            stopped_because=str(result.get("stopped_because") or ""),
            dead_ends=dead_ends,
            terms=terms,
        )
        # A2: session-end mood → mood_carryover with wall-clock timestamp.
        felt = result.get("final_feeling")
        pad_src: dict[str, Any] | None = felt if isinstance(felt, dict) else None
        if pad_src is None and isinstance(result.get("final_mix"), dict):
            pad_src = result.get("final_mix")
        # Prefer explicit pad on the result when tests / callers stash it.
        if isinstance(result.get("pad"), dict):
            pad_src = result["pad"]
        elif isinstance(felt, dict) and isinstance(felt.get("mood"), dict):
            pad_src = felt["mood"]
        if pad_src is not None:
            self.mood_carryover = MoodState.from_pad(pad_src, updated_at=utc_now_iso())
        # A4: fold session outcome into scars / affinities (domain-level).
        from artificial_emotions.scars import update_from_explore_result

        self.scars, self.affinities = update_from_explore_result(
            self.scars, self.affinities, result
        )
        return record

    def opening_mood(
        self,
        *,
        at: datetime | None = None,
        half_life_hours: float | None = None,
    ) -> MoodState:
        """Decayed carryover for the start of a new session."""
        return self.mood_carryover.decayed(at=at, half_life_hours=half_life_hours)

    def forget(self, what: str) -> dict[str, Any]:
        """Remove something. ``what`` is a session id, question id, or keyword.

        Keywords: ``sessions``, ``encounters``, ``selections``, ``mood``,
        ``scars``, ``affinities``.
        """
        target = (what or "").strip()
        if not target:
            return {"forgot": False, "reason": "empty target"}

        lower = target.lower()
        removed: dict[str, Any] = {"forgot": True, "target": target}

        if lower in {"sessions", "session"}:
            removed["sessions"] = len(self.sessions)
            self.sessions = []
            return removed
        if lower == "encounters":
            removed["encounters"] = len(self.encounters)
            self.encounters = {}
            return removed
        if lower == "selections":
            removed["selections"] = len(self.selections)
            self.selections = {}
            return removed
        if lower == "mood":
            self.mood_carryover = MoodState()
            removed["mood"] = True
            return removed
        if lower == "scars":
            removed["scars"] = len(self.scars)
            self.scars = []
            return removed
        if lower == "affinities":
            removed["affinities"] = len(self.affinities)
            self.affinities = []
            return removed

        before_sessions = len(self.sessions)
        self.sessions = [s for s in self.sessions if s.session_id != target]
        if len(self.sessions) != before_sessions:
            removed["kind"] = "session"
            removed["session_id"] = target
            return removed

        if target in self.encounters or target in self.selections:
            removed["kind"] = "encounter"
            removed["count"] = self.encounters.pop(target, 0)
            removed["selections"] = self.selections.pop(target, 0)
            # also strip from session question lists
            for session in self.sessions:
                session.question_ids = [q for q in session.question_ids if q != target]
                if session.best_question_id == target:
                    session.best_question_id = None
            return removed

        before_scars = len(self.scars)
        self.scars = [s for s in self.scars if str(s.get("target") or "") != target]
        before_aff = len(self.affinities)
        self.affinities = [a for a in self.affinities if str(a.get("target") or "") != target]
        if len(self.scars) != before_scars or len(self.affinities) != before_aff:
            removed["kind"] = "scar_or_affinity"
            removed["scars_removed"] = before_scars - len(self.scars)
            removed["affinities_removed"] = before_aff - len(self.affinities)
            return removed

        return {"forgot": False, "reason": f"nothing matched '{target}'"}

    def reset(self) -> None:
        """Wipe all remembered state (and delete the file when saved)."""
        self.sessions = []
        self.mood_carryover = MoodState()
        self.previous_step = PreviousStepSnapshot()
        self.scars = []
        self.affinities = []
        self.encounters = {}
        self.selections = {}
        self.privacy_ack = False
        self.schema_version = SCHEMA_VERSION

    def delete_file(self) -> bool:
        """Remove the on-disk file if present. Returns True if deleted."""
        if memory_disabled():
            return False
        if self.path.is_file():
            self.path.unlink()
            return True
        return False

    def show(self) -> dict[str, Any]:
        """Human/JSON summary for ``emotions memory show``."""
        payload = self.to_dict()
        payload["scars_plain"] = scars_plain(self.scars)
        payload["affinities_plain"] = affinities_plain(self.affinities)
        return payload


def scars_plain(scars: list[dict[str, Any]]) -> list[str]:
    """Plain-language scar lines for CLI show."""
    from artificial_emotions.scars import decayed_strength, plain_scar

    lines: list[str] = []
    for entry in scars or []:
        if not isinstance(entry, dict):
            continue
        strength, _ = decayed_strength(float(entry.get("strength") or 0.0), entry.get("updated_at"))
        lines.append(plain_scar(entry, strength=strength))
    return lines


def affinities_plain(affinities: list[dict[str, Any]]) -> list[str]:
    """Plain-language affinity lines for CLI show."""
    from artificial_emotions.scars import decayed_strength, plain_affinity

    lines: list[str] = []
    for entry in affinities or []:
        if not isinstance(entry, dict):
            continue
        strength, _ = decayed_strength(float(entry.get("strength") or 0.0), entry.get("updated_at"))
        lines.append(plain_affinity(entry, strength=strength))
    return lines


def persist_explore_if_enabled(
    result: dict[str, Any],
    *,
    enabled: bool,
    path: Path | str | None = None,
    previous_step: PreviousStepSnapshot | None = None,
) -> PersistentMemory | None:
    """Save an explore result when persistence is requested and not opted out."""
    if not enabled or memory_disabled():
        return None
    mem = PersistentMemory.load(path)
    mem.record_explore_result(result)
    if previous_step is not None:
        mem.previous_step = previous_step
    mem.save()
    return mem
