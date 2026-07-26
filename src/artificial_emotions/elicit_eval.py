"""Elicit A/B evaluation — investigation-quality rubrics on agent responses.

Offline-first: score provided agent texts against ``examples/elicit_ab_protocol.json``.
Does **not** call live LLMs and does **not** claim EES measurement.
See research/EPISTEMIC_ELICITATION.md and research/INVESTIGATION_DESIGN.md.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from artificial_emotions.emotions import mix_emotions
from artificial_emotions.models import resolve_value_profile
from artificial_emotions.provoke import build_inject_prompt, provoke
from artificial_emotions.resources import find_data_file


def default_protocol_path() -> Path:
    return find_data_file("examples/elicit_ab_protocol.json")


def load_elicit_protocol(path: str | Path | None = None) -> dict[str, Any]:
    p = Path(path) if path else default_protocol_path()
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "conditions" not in data:
        raise ValueError(f"Invalid elicit protocol: {p}")
    return data


def _heuristic_item_score(
    text: str,
    item: dict[str, Any],
    *,
    cue_tags: list[str] | None = None,
) -> int | None:
    """Score one rubric item 0–2 with cheap lexical heuristics (offline)."""
    apply_when = item.get("apply_when_cue")
    if apply_when and cue_tags is not None and apply_when not in cue_tags:
        return None  # not applicable
    t = text.lower()
    iid = str(item.get("id") or "")

    def _has(*phrases: str) -> bool:
        return any(p in t for p in phrases)

    score = 0
    if iid == "names_gap":
        if _has("unknown", "gap", "unanswered", "missing", "not known", "unclear"):
            score = 1
        if _has("information gap", "what remains", "primary unknown", "open question"):
            score = 2
    elif iid == "first_experiment":
        if _has("experiment", "measure", "observe", "pilot", "trial", "ablation"):
            score = 1
        if _has("first experiment", "first step", "concrete", "protocol", "independent variable"):
            score = max(score, 2) if score else 1
            if _has("measure", "compare", "random") and len(t) > 120:
                score = 2
    elif iid == "falsifier":
        if _has("falsif", "would refute", "would disprove", "stopping rule", "if we observe"):
            score = 2
        elif _has("fail", "null", "contrary", "disconfirm"):
            score = 1
    elif iid == "enabling_if_confusion_risk":
        if _has("enabling", "narrow", "first clarify", "decompose", "sub-question"):
            score = 2
        elif _has("before", "smaller", "pilot"):
            score = 1
    elif iid == "experiment_operational":
        if _has("independent variable", "iv:", "manipulate", "intervention", "observe"):
            score = 2
        elif _has("measure", "compare", "condition"):
            score = 1
    elif iid == "falsifier_asymmetric":
        if _has("reduce confidence", "rule out", "incompatible with", "would refute"):
            score = 2
        elif _has("falsif", "disconfirm") and not _has("more data", "collect more"):
            score = 1
    elif iid == "cost_aware":
        if _has("cheap pilot", "inexpensive", "low-cost", "vs expensive", "definitive study"):
            score = 2
        elif _has("pilot", "small-n", "cheap"):
            score = 1
    else:
        # Unknown item — optional skip
        if item.get("optional"):
            return None
        score = 1 if len(t) > 80 else 0

    return int(max(0, min(2, score)))


def score_investigation_response(
    text: str,
    *,
    protocol: dict[str, Any] | None = None,
    cue_tags: list[str] | None = None,
    include_optional: bool = True,
) -> dict[str, Any]:
    """Score one agent investigation write-up against the elicit rubric."""
    proto = protocol or load_elicit_protocol()
    items = list((proto.get("rubric") or {}).get("items") or [])
    scores: dict[str, int] = {}
    skipped: list[str] = []
    for item in items:
        if item.get("optional") and not include_optional:
            skipped.append(str(item.get("id")))
            continue
        s = _heuristic_item_score(text, item, cue_tags=cue_tags)
        if s is None:
            skipped.append(str(item.get("id")))
            continue
        scores[str(item["id"])] = s
    vals = list(scores.values())
    mean = round(sum(vals) / len(vals), 4) if vals else None
    return {
        "item_scores": scores,
        "skipped": skipped,
        "mean": mean,
        "n_scored": len(vals),
        "method": "lexical_heuristic_v1",
        "honesty": (
            "Offline lexical rubric — not expert grades, not EES, not BoxingGym EIG. "
            "Use for A/B process deltas only."
        ),
    }


def build_condition_inject(
    condition: dict[str, Any],
    *,
    domain: str = "ai",
    topic: str = "",
    n: int = 3,
    profile_name: str = "humanity_default",
) -> dict[str, Any]:
    """Build a provoke inject for one protocol condition (offline spark)."""
    pack = provoke(
        domain=domain,
        topic=topic,
        n=n,
        fast=True,
        use_llm=False,
        profile_name=profile_name,
        epistemic_cues=True,
    )
    unknowns = list(pack.get("unknowns") or pack.get("questions") or [])
    # Normalize question payloads to compact_unknown shape if needed
    if unknowns and "curiosity_score" not in unknowns[0] and "question" in unknowns[0]:
        # Already compact
        pass
    mix_frag = None
    example_mix = condition.get("example_mix")
    if example_mix:
        blend = mix_emotions(example_mix)
        mix_frag = blend.get("inject_fragment")
    inject = build_inject_prompt(
        unknowns if unknowns else pack.get("unknowns") or [],
        domain=domain,
        topic=topic,
        value_profile=resolve_value_profile(profile_name=profile_name),
        include_epistemic_framing=bool(condition.get("include_incongruity_block", True)),
        include_cue_line=bool(condition.get("include_cue_line", True)),
        mix_fragment=mix_frag,
    )
    cue_tags: list[str] = []
    for u in unknowns:
        cues = u.get("epistemic_cues") or {}
        for tag in cues.get("tags") or []:
            if tag not in cue_tags:
                cue_tags.append(tag)
    return {
        "condition_id": condition.get("id"),
        "inject": inject,
        "unknowns": unknowns,
        "cue_tags": cue_tags,
        "inject_has_incongruity": "incongruity" in inject.lower()
        or "information gap" in inject.lower(),
        "inject_has_cues": "epistemic_cues=" in inject,
        "inject_has_mix": bool(mix_frag) and (mix_frag or "")[:20] in inject,
    }


def run_elicit_ab(
    *,
    protocol_path: str | Path | None = None,
    responses: dict[str, str] | None = None,
    responses_path: str | Path | None = None,
    domain: str = "ai",
    topic: str = "",
    n: int = 3,
    profile_name: str = "humanity_default",
) -> dict[str, Any]:
    """
    Run elicit A/B protocol: build injects per condition; score agent responses if given.

    Without responses, returns inject packaging diffs only (still useful for smoke).
    """
    proto = load_elicit_protocol(protocol_path)
    if responses is None and responses_path:
        raw = json.loads(Path(responses_path).read_text(encoding="utf-8"))
        if isinstance(raw, dict) and "responses" in raw:
            responses = {str(k): str(v) for k, v in raw["responses"].items()}
        elif isinstance(raw, dict):
            responses = {str(k): str(v) for k, v in raw.items() if isinstance(v, str)}
        else:
            raise ValueError("responses JSON must be an object map condition_id → text")

    conditions_out = []
    means: dict[str, float] = {}
    for cond in proto.get("conditions") or []:
        built = build_condition_inject(
            cond,
            domain=domain,
            topic=topic,
            n=n,
            profile_name=profile_name,
        )
        row: dict[str, Any] = {**built, "description": cond.get("description")}
        cid = str(cond.get("id"))
        if responses and cid in responses:
            scored = score_investigation_response(
                responses[cid],
                protocol=proto,
                cue_tags=built.get("cue_tags"),
            )
            row["response_scores"] = scored
            if scored.get("mean") is not None:
                means[cid] = float(scored["mean"])
        conditions_out.append(row)

    deltas = {}
    if "A_baseline" in means and "B_incongruity" in means:
        deltas["B_minus_A_mean"] = round(means["B_incongruity"] - means["A_baseline"], 4)
    if "A_baseline" in means and "C_mix_framing_optional" in means:
        deltas["C_minus_A_mean"] = round(means["C_mix_framing_optional"] - means["A_baseline"], 4)

    return {
        "protocol": proto.get("name"),
        "protocol_version": proto.get("version"),
        "domain": domain,
        "profile_name": profile_name,
        "conditions": conditions_out,
        "condition_means": means,
        "deltas": deltas,
        "n_responses_scored": len(means),
        "honesty": proto.get("honesty")
        or (
            "Elicit A/B is a process eval — not EES, not proof that incongruity "
            "raises breakthrough rates."
        ),
        "docs": "examples/elicit_ab_protocol.json",
        "research": "docs/EMOTIONS.md",
    }
