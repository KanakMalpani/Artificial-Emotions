"""A5 Temperament — a ``.toml`` personality that makes *this* instance diverge.

Presets and custom fields bias appraisal swing, search breadth, risk ceilings
(tighten only), and skepticism — never inventing evidence, never loosening
safety. Default ``explore(..., temperament=None)`` is a no-op so
``CURIOSITY_NO_MEMORY`` / fresh-install paths stay byte-identical.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from artificial_emotions.models import CuriosityConfig

__all__ = [
    "DEFAULT_TEMPERAMENT_DIR",
    "DEFAULT_TEMPERAMENT_PATH",
    "ENV_TEMPERAMENT_PATH",
    "PRESETS",
    "PRESET_NAMES",
    "BaselineMood",
    "Temperament",
    "TemperamentApplication",
    "apply_to_config",
    "bias_signal_weights",
    "decay_frustration",
    "default_temperament_path",
    "disclosure_payload",
    "ensure_default_file",
    "get_preset",
    "load_temperament",
    "mood_bias_from_temperament",
    "resolve_temperament",
    "scale_appraisal_signals",
]

DEFAULT_TEMPERAMENT_DIR = Path.home() / ".artificial_emotions"
DEFAULT_TEMPERAMENT_PATH = DEFAULT_TEMPERAMENT_DIR / "temperament.toml"
ENV_TEMPERAMENT_PATH = "CURIOSITY_TEMPERAMENT_PATH"

#: Reactivity of 0.5 leaves appraisal weights unchanged (factor = 1.0).
_NEUTRAL_REACTIVITY = 0.5
#: Novelty of 0.5 leaves candidate breadth / diversity alone.
_NEUTRAL_NOVELTY = 0.5


@dataclass(frozen=True)
class BaselineMood:
    """PAD-shaped baseline (PLAN_ALIVE: valence / arousal / dominance)."""

    valence: float = 0.0
    arousal: float = 0.0
    dominance: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {
            "valence": round(float(self.valence), 4),
            "arousal": round(float(self.arousal), 4),
            "dominance": round(float(self.dominance), 4),
        }

    @classmethod
    def from_mapping(cls, raw: dict[str, Any] | None) -> BaselineMood:
        if not isinstance(raw, dict):
            return cls()
        return cls(
            valence=float(raw.get("valence", raw.get("pleasure", 0.0)) or 0.0),
            arousal=float(raw.get("arousal", 0.0) or 0.0),
            dominance=float(raw.get("dominance", 0.0) or 0.0),
        )


@dataclass(frozen=True)
class Temperament:
    """Instance personality — biases search / appraisal, never fabricates evidence."""

    name: str = "custom"
    baseline_mood: BaselineMood = field(default_factory=BaselineMood)
    reactivity: float = 0.5
    recovery_rate: float = 0.5
    skepticism_bias: float = 0.0
    novelty_seeking: float = 0.5
    risk_aversion: float = 0.0

    def clamped(self) -> Temperament:
        """Clamp continuous fields into ``[0, 1]`` (mood into roughly ``[-1, 1]``)."""

        def _unit(x: float) -> float:
            return max(0.0, min(1.0, float(x)))

        def _pad(x: float) -> float:
            return max(-1.0, min(1.0, float(x)))

        mood = BaselineMood(
            valence=_pad(self.baseline_mood.valence),
            arousal=_pad(self.baseline_mood.arousal),
            dominance=_pad(self.baseline_mood.dominance),
        )
        return replace(
            self,
            baseline_mood=mood,
            reactivity=_unit(self.reactivity),
            recovery_rate=_unit(self.recovery_rate),
            skepticism_bias=_unit(self.skepticism_bias),
            novelty_seeking=_unit(self.novelty_seeking),
            risk_aversion=_unit(self.risk_aversion),
        )

    @property
    def is_neutral(self) -> bool:
        """True when applying this temperament would not change behaviour."""
        t = self.clamped()
        mood = t.baseline_mood
        return (
            abs(mood.valence) < 1e-6
            and abs(mood.arousal) < 1e-6
            and abs(mood.dominance) < 1e-6
            and abs(t.reactivity - _NEUTRAL_REACTIVITY) < 1e-6
            and abs(t.recovery_rate - 0.5) < 1e-6
            and t.skepticism_bias < 1e-6
            and abs(t.novelty_seeking - _NEUTRAL_NOVELTY) < 1e-6
            and t.risk_aversion < 1e-6
        )

    def to_dict(self) -> dict[str, Any]:
        t = self.clamped()
        return {
            "name": t.name,
            "baseline_mood": t.baseline_mood.to_dict(),
            "reactivity": round(t.reactivity, 4),
            "recovery_rate": round(t.recovery_rate, 4),
            "skepticism_bias": round(t.skepticism_bias, 4),
            "novelty_seeking": round(t.novelty_seeking, 4),
            "risk_aversion": round(t.risk_aversion, 4),
            "honesty": (
                "computational temperament — biases thresholds and search knobs; "
                "does not feel; never loosens a safety gate"
            ),
        }

    def to_toml(self) -> str:
        """Serialize as the on-disk temperament.toml shape from PLAN_ALIVE."""
        t = self.clamped()
        m = t.baseline_mood
        return (
            "# Artificial Emotions temperament (A5).\n"
            "# Biases appraisal swing and search knobs. Annotation only — does not feel.\n"
            "# Edit freely; delete this file to return to neutral defaults.\n"
            "\n"
            "[temperament]\n"
            f'name               = "{t.name}"\n'
            f"baseline_mood      = {{ valence = {m.valence}, "
            f"arousal = {m.arousal}, dominance = {m.dominance} }}\n"
            f"reactivity         = {t.reactivity}   "
            f"# how hard appraisal swings (0.5 = unchanged)\n"
            f"recovery_rate      = {t.recovery_rate}   "
            f"# how fast frustration / mood residual fades\n"
            f"skepticism_bias    = {t.skepticism_bias}\n"
            f"novelty_seeking    = {t.novelty_seeking}\n"
            f"risk_aversion      = {t.risk_aversion}\n"
        )


#: Named presets — same corpus, measurably different trajectories.
PRESETS: dict[str, Temperament] = {
    "restless": Temperament(
        name="restless",
        baseline_mood=BaselineMood(valence=0.15, arousal=0.55, dominance=0.1),
        reactivity=0.95,
        recovery_rate=0.25,
        skepticism_bias=0.15,
        novelty_seeking=0.95,
        risk_aversion=0.2,
    ),
    "cautious": Temperament(
        name="cautious",
        baseline_mood=BaselineMood(valence=-0.1, arousal=-0.15, dominance=-0.2),
        reactivity=0.3,
        recovery_rate=0.55,
        skepticism_bias=0.9,
        novelty_seeking=0.1,
        risk_aversion=0.95,
    ),
    "dogged": Temperament(
        name="dogged",
        baseline_mood=BaselineMood(valence=0.05, arousal=0.2, dominance=0.4),
        reactivity=0.4,
        recovery_rate=0.9,
        skepticism_bias=0.45,
        novelty_seeking=0.2,
        risk_aversion=0.4,
    ),
    "flighty": Temperament(
        name="flighty",
        baseline_mood=BaselineMood(valence=0.25, arousal=0.75, dominance=-0.15),
        reactivity=0.9,
        recovery_rate=0.1,
        skepticism_bias=0.05,
        novelty_seeking=0.95,
        risk_aversion=0.1,
    ),
}

PRESET_NAMES: tuple[str, ...] = tuple(PRESETS.keys())


def get_preset(name: str) -> Temperament:
    key = str(name).strip().lower()
    if key not in PRESETS:
        raise KeyError(
            f"Unknown temperament preset {name!r}. Choose one of: {', '.join(PRESET_NAMES)}"
        )
    return PRESETS[key].clamped()


def default_temperament_path() -> Path:
    override = (os.environ.get(ENV_TEMPERAMENT_PATH) or "").strip()
    if override:
        return Path(override).expanduser()
    return DEFAULT_TEMPERAMENT_PATH


def ensure_default_file(path: Path | str | None = None) -> Path:
    """Write a starter temperament.toml if missing (custom fields from PLAN_ALIVE)."""
    target = Path(path) if path is not None else default_temperament_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        # Default on-disk example matches PLAN_ALIVE illustration (custom, not a preset).
        starter = Temperament(
            name="custom",
            baseline_mood=BaselineMood(valence=0.1, arousal=-0.1, dominance=0.0),
            reactivity=0.7,
            recovery_rate=0.4,
            skepticism_bias=0.3,
            novelty_seeking=0.8,
            risk_aversion=0.5,
        )
        target.write_text(starter.to_toml(), encoding="utf-8")
    return target


def load_temperament(path: Path | str | None = None) -> Temperament:
    """Load temperament.toml; missing file → neutral custom (no behavioural delta)."""
    target = Path(path) if path is not None else default_temperament_path()
    if not target.is_file():
        return Temperament(name="custom").clamped()
    raw = tomllib.loads(target.read_text(encoding="utf-8"))
    block = raw.get("temperament") if isinstance(raw.get("temperament"), dict) else raw
    if not isinstance(block, dict):
        return Temperament(name="custom").clamped()
    name = str(block.get("name") or "custom").strip() or "custom"
    return Temperament(
        name=name,
        baseline_mood=BaselineMood.from_mapping(
            block.get("baseline_mood") if isinstance(block.get("baseline_mood"), dict) else None
        ),
        reactivity=float(block.get("reactivity", 0.5)),
        recovery_rate=float(block.get("recovery_rate", 0.5)),
        skepticism_bias=float(block.get("skepticism_bias", 0.0)),
        novelty_seeking=float(block.get("novelty_seeking", 0.5)),
        risk_aversion=float(block.get("risk_aversion", 0.0)),
    ).clamped()


def resolve_temperament(
    temperament: str | Temperament | None = None,
    *,
    path: Path | str | None = None,
) -> Temperament | None:
    """Resolve an explore argument into an active temperament, or ``None`` (no-op).

    - ``None`` → no temperament (byte-identical to today).
    - preset name → that preset.
    - ``\"custom\"`` / ``\"file\"`` → load from disk (writes default if missing).
    - ``Temperament`` → clamped instance (skipped if fully neutral).
    """
    if temperament is None:
        return None
    if isinstance(temperament, Temperament):
        t = temperament.clamped()
        return None if t.is_neutral else t
    key = str(temperament).strip().lower()
    if not key:
        return None
    if key in PRESETS:
        return get_preset(key)
    if key in {"custom", "file", "toml", "from_file"}:
        ensure_default_file(path)
        t = load_temperament(path)
        return None if t.is_neutral else t
    raise KeyError(
        f"Unknown temperament {temperament!r}. "
        f"Presets: {', '.join(PRESET_NAMES)}; or 'custom' to load temperament.toml"
    )


@dataclass(frozen=True)
class TemperamentApplication:
    """One disclosed knob move caused by temperament."""

    knob: str
    before: Any
    after: Any
    magnitude: float
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "knob": self.knob,
            "before": self.before,
            "after": self.after,
            "magnitude": round(float(self.magnitude), 4),
            "rationale": self.rationale,
        }


def mood_bias_from_temperament(temperament: Temperament) -> Any | None:
    """Opening appraisal-floor bias from baseline_mood (A2-compatible)."""
    t = temperament.clamped()
    mood = t.baseline_mood
    if abs(mood.valence) < 1e-6 and abs(mood.arousal) < 1e-6 and abs(mood.dominance) < 1e-6:
        return None
    from artificial_emotions.affect import MoodThresholdBias

    return MoodThresholdBias(
        pleasure=float(mood.valence),
        arousal=float(mood.arousal),
        dominance=float(mood.dominance),
        decay_factor=1.0,
    )


def apply_to_config(
    config: CuriosityConfig,
    temperament: Temperament,
) -> tuple[CuriosityConfig, list[TemperamentApplication]]:
    """Bias search knobs from temperament. Risk aversion may only *tighten* max_risk."""
    t = temperament.clamped()
    apps: list[TemperamentApplication] = []
    updates: dict[str, Any] = {}
    profile = config.value_profile

    nov_delta = t.novelty_seeking - _NEUTRAL_NOVELTY
    if abs(nov_delta) > 0.05:
        before_n = int(config.n_candidates)
        after_n = int(round(before_n * (1.0 + 0.75 * nov_delta)))
        after_n = max(4, min(64, after_n))
        if after_n != before_n:
            updates["n_candidates"] = after_n
            apps.append(
                TemperamentApplication(
                    "n_candidates",
                    before_n,
                    after_n,
                    abs(nov_delta),
                    "Novelty seeking widens or narrows the candidate pool.",
                )
            )
        before_d = float(config.diversity_threshold)
        # Higher novelty → tolerate less near-duplicate sameness (lower threshold).
        after_d = round(max(0.5, min(0.99, before_d - 0.2 * nov_delta)), 4)
        if abs(after_d - before_d) > 1e-6:
            updates["diversity_threshold"] = after_d
            apps.append(
                TemperamentApplication(
                    "diversity_threshold",
                    before_d,
                    after_d,
                    abs(nov_delta),
                    "Novelty seeking adjusts how hard near-duplicates are suppressed.",
                )
            )

    if t.risk_aversion > 0.05:
        before_r = float(profile.max_risk)
        after_r = round(max(0.05, before_r - 0.35 * t.risk_aversion), 4)
        if after_r < before_r - 1e-9:
            profile = profile.model_copy(update={"max_risk": after_r})
            updates["value_profile"] = profile
            apps.append(
                TemperamentApplication(
                    "value_profile.max_risk",
                    before_r,
                    after_r,
                    t.risk_aversion,
                    "Risk aversion tightens the ceiling only — never raises it.",
                )
            )

    # Skepticism bias boosts appraisal/modulation weights only — never flips
    # use_literature here (would break offline determinism / force network).

    if not updates:
        return config, apps
    return config.model_copy(update=updates), apps


def scale_appraisal_signals(
    signals: list[Any],
    temperament: Temperament,
) -> list[Any]:
    """Scale supported appraisal weights by reactivity / skepticism / novelty.

    Never invents signals that did not fire. Caps weights at 1.0.
    """
    from artificial_emotions.appraisal import AppraisalSignal

    t = temperament.clamped()
    factor = 0.5 + float(t.reactivity)  # reactivity 0.5 → 1.0
    nov_boost = max(0.0, t.novelty_seeking - _NEUTRAL_NOVELTY)
    out: list[Any] = []
    for s in signals:
        w = float(s.weight) * factor
        emotion = str(s.emotion)
        evidence = dict(s.evidence or {})
        if emotion == "skepticism" and t.skepticism_bias > 0:
            w = min(1.0, w + 0.35 * t.skepticism_bias)
            evidence["temperament_skepticism_bias"] = round(t.skepticism_bias, 4)
        if emotion in {"curiosity", "surprise", "wonder"} and nov_boost > 0:
            w = min(1.0, w * (1.0 + 0.5 * nov_boost))
            evidence["temperament_novelty_seeking"] = round(t.novelty_seeking, 4)
        if abs(factor - 1.0) > 1e-9:
            evidence["temperament_reactivity"] = round(t.reactivity, 4)
            evidence["temperament_weight_factor"] = round(factor, 4)
        w = max(0.0, min(1.0, w))
        if abs(w - float(s.weight)) < 1e-9 and evidence == (s.evidence or {}):
            out.append(s)
            continue
        out.append(
            AppraisalSignal(
                emotion=emotion,
                weight=w,
                because=s.because,
                evidence=evidence,
            )
        )
    out.sort(key=lambda s: (-float(s.weight), str(s.emotion)))
    return out


def bias_signal_weights(
    weights: dict[str, float],
    temperament: Temperament,
) -> dict[str, float]:
    """Nudge modulation inputs (persistence vs boredom) from recovery / novelty."""
    t = temperament.clamped()
    w = {k: float(v) for k, v in weights.items()}
    # Dogged: high recovery + low novelty → stay on the thread.
    persistence_pull = (t.recovery_rate - 0.5) * 0.45 + (
        _NEUTRAL_NOVELTY - t.novelty_seeking
    ) * 0.35
    if persistence_pull > 0.08:
        w["persistence"] = min(1.0, w.get("persistence", 0.0) + persistence_pull)
        w["determination"] = min(1.0, w.get("determination", 0.0) + 0.55 * persistence_pull)
        w["absorption"] = min(1.0, w.get("absorption", 0.0) + 0.4 * persistence_pull)
    # Flighty / restless: high novelty + low recovery → itch to change ground.
    jump_pull = (t.novelty_seeking - _NEUTRAL_NOVELTY) * 0.4 + (0.5 - t.recovery_rate) * 0.35
    if jump_pull > 0.08:
        w["boredom"] = min(1.0, w.get("boredom", 0.0) + jump_pull)
        w["curiosity"] = min(1.0, w.get("curiosity", 0.0) + 0.5 * jump_pull)
    if t.skepticism_bias > 0.2:
        w["skepticism"] = min(1.0, w.get("skepticism", 0.0) + 0.3 * t.skepticism_bias)
    return w or {"curiosity": 1.0}


def decay_frustration(accumulated: float, temperament: Temperament) -> float:
    """Higher recovery_rate fades session frustration faster between steps."""
    t = temperament.clamped()
    return max(0.0, float(accumulated) * (1.0 - 0.55 * t.recovery_rate))


def disclosure_payload(
    temperament: Temperament,
    applications: list[TemperamentApplication],
) -> dict[str, Any]:
    return {
        "temperament": temperament.to_dict(),
        "biases": [a.to_dict() for a in applications],
        "honesty": (
            "Temperament is a local .toml personality bias — computational only, "
            "does not feel, disclosed whenever it changes a run."
        ),
    }
