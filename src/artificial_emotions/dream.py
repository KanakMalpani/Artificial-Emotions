"""B5 Dream — explicit offline reanalysis of stored PersistentMemory history.

Never automatic, never background. On ``emotions dream`` only: re-read scars,
encounters, dead ends, and recurring terms across sessions; look for structure
missed live (recurring dead ends, terms across unconnected sessions, scars that
no longer match evidence).

Honest framing: this is **offline reanalysis of stored history**. The CLI may
say "dream" once; the payload must not call the output a dream.

Generative synthesis (when present) travels as ``ImaginedContent`` under
quarantine. Structured findings carry honesty tokens. Invents no literature.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from artificial_emotions.imagine import (
    HONESTY_IMAGINED,
    ImaginedContent,
    assert_imagined_safe,
    imagined_payload,
)
from artificial_emotions.memory import PersistentMemory, SessionRecord, scars_plain
from artificial_emotions.scars import MIN_ACTIVE_STRENGTH, decayed_strength
from artificial_emotions.trajectory import question_terms

__all__ = [
    "HONESTY_REANALYSIS",
    "KIND_REANALYSIS",
    "dream_claims_not",
    "reanalyze_history",
]

#: Payload honesty — every dream surface must carry this exact string.
HONESTY_REANALYSIS = "offline_reanalysis_of_stored_history"

#: ImaginedContent.kind for generative synthesis. Never ``dream``.
KIND_REANALYSIS = "history_reanalysis"

#: Minimum sessions a dead-end id must appear in to count as recurring.
_MIN_DEAD_END_SESSIONS = 2

#: Minimum unconnected sessions a term must span.
_MIN_TERM_SESSIONS = 2

#: Banned payload tokens — output must not call itself a dream.
_DREAM_BANNED = frozenset({"dream", "dreams", "dreaming", "dreamt"})


def dream_claims_not() -> tuple[str, ...]:
    """Honesty tokens every reanalysis surface must carry."""
    return (
        "a dream, vision, or subconscious process",
        "retrieved or newly invented literature",
        "phenomenal feeling or lived experience",
        "biological emotion",
        "that the system ran while idle or in the background",
    )


def reanalyze_history(
    memory: PersistentMemory | None = None,
    *,
    path: str | None = None,
) -> dict[str, Any]:
    """Offline reanalysis of stored history. Read-only; invents no literature.

    Explicit command only — callers must not schedule this. Never mutates
    ``memory`` or writes to disk.
    """
    mem = memory if memory is not None else PersistentMemory.load(path)

    recurring_dead_ends = _recurring_dead_ends(mem)
    cross_session_terms = _terms_across_unconnected_sessions(mem)
    mismatched_scars = _scars_that_no_longer_match(mem)
    encounter_echoes = _encounter_structure(mem)

    findings: list[dict[str, Any]] = []
    findings.extend(recurring_dead_ends)
    findings.extend(cross_session_terms)
    findings.extend(mismatched_scars)
    findings.extend(encounter_echoes)

    grounded_ids = _grounded_ids(mem, findings)
    invented_notes = _invented_notes(findings)

    imagined: list[ImaginedContent] = []
    if findings:
        synthesis = _synthesize(findings)
        imagined.append(
            ImaginedContent(
                content=synthesis,
                kind=KIND_REANALYSIS,
                driven_by=("curiosity", "doubt", "recognition"),
                grounded_in=tuple(grounded_ids),
                invented=tuple(invented_notes),
            )
        )

    # Quarantine when generative; always attach structured analysis.
    if imagined:
        payload = imagined_payload(
            imagined,
            extra={
                "kind": KIND_REANALYSIS,
                "analysis": {
                    "findings": findings,
                    "n_sessions": len(mem.sessions),
                    "n_scars": len(mem.scars),
                    "n_encounters": len(mem.encounters),
                    "source": "PersistentMemory",
                    "path": str(mem.path),
                },
                "framing": HONESTY_REANALYSIS,
                "offline": True,
                "network": False,
                "automatic": False,
                "background": False,
                "note": (
                    "Offline reanalysis of stored history — does not feel; "
                    "computational consolidation of local JSON only. "
                    "No literature retrieved or invented."
                ),
                "claims_not": list(dream_claims_not()),
            },
        )
        # Keep quarantine honesty; also stamp the reanalysis honesty token.
        payload["reanalysis_honesty"] = HONESTY_REANALYSIS
    else:
        payload = {
            "analysis": {
                "findings": [],
                "n_sessions": len(mem.sessions),
                "n_scars": len(mem.scars),
                "n_encounters": len(mem.encounters),
                "source": "PersistentMemory",
                "path": str(mem.path),
            },
            "imagined": [],
            "honesty": HONESTY_REANALYSIS,
            "reanalysis_honesty": HONESTY_REANALYSIS,
            "confidence": None,
            "framing": HONESTY_REANALYSIS,
            "offline": True,
            "network": False,
            "automatic": False,
            "background": False,
            "note": (
                "Offline reanalysis of stored history — nothing to consolidate yet. "
                "Does not feel; no literature retrieved or invented."
            ),
            "claims_not": list(dream_claims_not()),
            "docs": "docs/PLAN_ALIVE.md",
        }

    _assert_not_called_dream(payload)
    _assert_no_invented_literature(payload, mem)
    if imagined:
        ok, offenders = assert_imagined_safe(payload)
        if not ok:
            from artificial_emotions.errors import ERR_VALIDATION, CuriosityError

            raise CuriosityError(
                ERR_VALIDATION,
                "dream payload failed quarantine checks",
                details={"offenders": offenders},
            )
    return payload


# --- structure detectors -----------------------------------------------------------


def _recurring_dead_ends(mem: PersistentMemory) -> list[dict[str, Any]]:
    """Dead-end question ids that recur across sessions."""
    by_qid: dict[str, list[str]] = defaultdict(list)
    for session in mem.sessions:
        sid = session.session_id or "?"
        for qid in session.dead_ends:
            if qid and sid not in by_qid[qid]:
                by_qid[qid].append(sid)
        # Fallback: sessions that stopped on dead-end language with unseen picks.
        stopped = (session.stopped_because or "").lower()
        if any(tok in stopped for tok in ("dead end", "dead_end", "frustration", "exhaust")):
            for qid in session.question_ids:
                if qid and qid != session.best_question_id and sid not in by_qid[qid]:
                    by_qid[qid].append(sid)

    findings: list[dict[str, Any]] = []
    for qid, sessions in sorted(by_qid.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        if len(sessions) < _MIN_DEAD_END_SESSIONS:
            continue
        findings.append(
            {
                "type": "recurring_dead_end",
                "question_id": qid,
                "session_ids": list(sessions),
                "n_sessions": len(sessions),
                "evidence": "stored session dead_ends / dead-stop markers",
                "claims_not": ["that the gap is closed in the literature"],
            }
        )
    return findings


def _terms_across_unconnected_sessions(mem: PersistentMemory) -> list[dict[str, Any]]:
    """Terms that appear in sessions with no shared domain or question ids."""
    # term -> list of (session_id, domain, question_id_set)
    term_sessions: dict[str, list[tuple[str, str, frozenset[str]]]] = defaultdict(list)

    for session in mem.sessions:
        sid = session.session_id or "?"
        domain = (session.domain or "").lower()
        qids = frozenset(session.question_ids)
        terms = _session_terms(session)
        for term in terms:
            term_sessions[term].append((sid, domain, qids))

    findings: list[dict[str, Any]] = []
    for term, appearances in sorted(term_sessions.items()):
        if len(appearances) < _MIN_TERM_SESSIONS:
            continue
        # Unconnected: no shared domain AND no overlapping question ids between
        # at least one pair of appearances.
        unconnected_pairs: list[tuple[str, str]] = []
        for i, (sid_a, dom_a, q_a) in enumerate(appearances):
            for sid_b, dom_b, q_b in appearances[i + 1 :]:
                same_domain = bool(dom_a) and dom_a == dom_b
                shared_q = bool(q_a & q_b)
                if not same_domain and not shared_q:
                    unconnected_pairs.append((sid_a, sid_b))
        if not unconnected_pairs:
            continue
        session_ids = sorted({sid for sid, _, _ in appearances})
        findings.append(
            {
                "type": "cross_session_term",
                "term": term,
                "session_ids": session_ids,
                "n_sessions": len(session_ids),
                "unconnected_pairs": [{"a": a, "b": b} for a, b in unconnected_pairs[:5]],
                "evidence": "stored session topics / mined terms",
                "claims_not": ["a newly retrieved paper or corpus hit"],
            }
        )
    # Prefer higher span; cap for readability.
    findings.sort(key=lambda f: (-int(f["n_sessions"]), str(f["term"])))
    return findings[:12]


def _scars_that_no_longer_match(mem: PersistentMemory) -> list[dict[str, Any]]:
    """Scars contradicted by later affinities or successful sessions on the same target."""
    affinity_targets = {
        str(a.get("target") or "").lower()
        for a in mem.affinities
        if isinstance(a, dict) and a.get("target")
    }
    # Domains with recent non-dead-stop sessions that picked something.
    successful_domains: set[str] = set()
    for session in mem.sessions:
        stopped = (session.stopped_because or "").lower()
        deadish = any(tok in stopped for tok in ("dead end", "dead_end", "frustration", "exhaust"))
        if session.best_question_id and not deadish and session.steps_taken > 0:
            if session.domain:
                successful_domains.add(session.domain.lower())

    findings: list[dict[str, Any]] = []
    for entry in mem.scars:
        if not isinstance(entry, dict):
            continue
        target = str(entry.get("target") or "").strip()
        if not target:
            continue
        t_low = target.lower()
        strength, factor = decayed_strength(
            float(entry.get("strength") or 0.0),
            entry.get("updated_at"),
        )
        reasons: list[str] = []
        if t_low in affinity_targets:
            reasons.append("matching affinity recorded for the same target")
        if t_low in successful_domains:
            reasons.append("later sessions in this domain selected a best question")
        if strength < MIN_ACTIVE_STRENGTH and int(entry.get("hits") or 0) >= 2:
            reasons.append(
                f"decayed strength {strength:.4f} is below active threshold "
                f"(decay_factor={factor:.4f})"
            )
        if not reasons:
            continue
        findings.append(
            {
                "type": "mismatched_scar",
                "target": target,
                "kind": str(entry.get("kind") or "domain"),
                "hits": int(entry.get("hits") or 0),
                "decayed_strength": round(strength, 6),
                "reasons": reasons,
                "plain": scars_plain([entry])[0] if scars_plain([entry]) else target,
                "evidence": "stored scars vs affinities / later sessions",
                "claims_not": [
                    "that the scar was wrong about past runs",
                    "phenomenal healing",
                ],
            }
        )
    return findings


def _encounter_structure(mem: PersistentMemory) -> list[dict[str, Any]]:
    """High-encounter ids never selected — structure visible only across history."""
    findings: list[dict[str, Any]] = []
    for qid, count in sorted(mem.encounters.items(), key=lambda kv: (-int(kv[1]), kv[0])):
        n = int(count)
        if n < _MIN_DEAD_END_SESSIONS:
            continue
        picked = int(mem.selections.get(qid, 0))
        if picked != 0:
            continue
        # Only surface when the id also appears in ≥2 session records
        # (true cross-session echo, not a single bloated encounter counter).
        session_hits = [s.session_id for s in mem.sessions if qid in s.question_ids]
        if len(session_hits) < _MIN_DEAD_END_SESSIONS:
            continue
        findings.append(
            {
                "type": "unselected_recurring_encounter",
                "question_id": qid,
                "encounters": n,
                "selections": picked,
                "session_ids": session_hits,
                "evidence": "stored encounters vs selections",
                "claims_not": [
                    "a motive for non-selection",
                    "that non-selection is avoidance rather than judgment",
                ],
            }
        )
    return findings[:8]


def _session_terms(session: SessionRecord) -> list[str]:
    """Content terms from stored topic / mined terms / question id tokens."""
    out: list[str] = []
    for t in session.terms:
        lt = t.lower().strip()
        if lt and lt not in out:
            out.append(lt)
    for t in question_terms(session.topic or ""):
        if t not in out:
            out.append(t)
    for qid in session.question_ids:
        # Split id-like tokens: "ai-sandbagging-eval" → sandbagging, eval…
        for t in question_terms(qid.replace("-", " ").replace("_", " ")):
            if t not in out:
                out.append(t)
    return out


def _grounded_ids(mem: PersistentMemory, findings: list[dict[str, Any]]) -> list[str]:
    ids: list[str] = []
    for f in findings:
        for key in ("question_id", "target", "term"):
            val = f.get(key)
            if val and str(val) not in ids:
                ids.append(str(val))
        for sid in f.get("session_ids") or []:
            label = f"session:{sid}"
            if label not in ids:
                ids.append(label)
    for scar in mem.scars:
        if isinstance(scar, dict) and scar.get("target"):
            t = str(scar["target"])
            if t not in ids:
                ids.append(t)
    return ids[:40]


def _invented_notes(findings: list[dict[str, Any]]) -> list[str]:
    """State what was inferred (not retrieved). Never literature titles."""
    notes: list[str] = [
        "structure inferred by offline reanalysis of PersistentMemory JSON",
        "no corpus search, no network, no new literature",
    ]
    by_type: dict[str, int] = defaultdict(int)
    for f in findings:
        by_type[str(f.get("type") or "unknown")] += 1
    for kind, n in sorted(by_type.items()):
        notes.append(f"inferred:{kind}={n}")
    return notes


def _synthesize(findings: list[dict[str, Any]]) -> str:
    """Generative framing of stored-history structure — quarantined, not a dream."""
    bits: list[str] = []
    for f in findings[:8]:
        ftype = f.get("type")
        if ftype == "recurring_dead_end":
            bits.append(
                f"question {f['question_id']!r} was a dead end in "
                f"{f['n_sessions']} sessions ({', '.join(f['session_ids'][:4])})"
            )
        elif ftype == "cross_session_term":
            bits.append(
                f"term {f['term']!r} recurs across unconnected sessions "
                f"{', '.join(f['session_ids'][:4])}"
            )
        elif ftype == "mismatched_scar":
            bits.append(
                f"scar on {f['target']!r} no longer matches stored evidence: "
                f"{'; '.join(f['reasons'])}"
            )
        elif ftype == "unselected_recurring_encounter":
            bits.append(
                f"question {f['question_id']!r} seen {f['encounters']} times, "
                f"picked {f['selections']}"
            )
    body = "; ".join(bits) if bits else "no cross-session structure found"
    return (
        f"History reanalysis — structure missed live, derived only from stored "
        f"PersistentMemory: {body}."
    )


# --- guards ------------------------------------------------------------------------


def _walk_strings(node: Any) -> list[str]:
    found: list[str] = []
    if isinstance(node, str):
        found.append(node)
    elif isinstance(node, dict):
        for k, v in node.items():
            found.append(str(k))
            found.extend(_walk_strings(v))
    elif isinstance(node, (list, tuple)):
        for v in node:
            found.extend(_walk_strings(v))
    return found


#: Payload keys whose values must not label the output a dream.
#: Paths / ids are excluded — a file named ``memory_dream.json`` is fine.
_LABEL_KEYS = frozenset(
    {
        "kind",
        "status",
        "framing",
        "note",
        "content",
        "type",
        "asks",
        "use_when",
        "honesty",
        "reanalysis_honesty",
    }
)


def _assert_not_called_dream(payload: dict[str, Any]) -> None:
    """Payload must not label the output as a dream (CLI may say it once)."""
    from artificial_emotions.errors import ERR_VALIDATION, CuriosityError

    offenders = _dream_label_offenders(payload)
    if offenders:
        raise CuriosityError(
            ERR_VALIDATION,
            "reanalysis payload must not call the output a dream",
            details={"offending": offenders[0][:120]},
        )


def _dream_label_offenders(node: Any, *, path: str = "$") -> list[str]:
    """Find label fields that call the output a dream.

    Only semantic keys (``kind``, ``content``, ``note``, …) are checked.
    ``claims_not`` may mention dreams to deny them. Filesystem paths are ignored.
    """
    offenders: list[str] = []
    if isinstance(node, dict):
        for k, v in node.items():
            key_l = str(k).lower()
            child = f"{path}.{k}"
            if key_l == "claims_not":
                continue
            if key_l in _DREAM_BANNED:
                offenders.append(f"key {child}")
                continue
            if key_l in _LABEL_KEYS and isinstance(v, str):
                offenders.extend(_flag_dream_label(v, path=child))
            elif key_l in _LABEL_KEYS:
                offenders.extend(_dream_label_offenders(v, path=child))
            elif isinstance(v, (dict, list, tuple)):
                # Recurse into nested structures but only flag label keys inside.
                offenders.extend(_dream_label_offenders(v, path=child))
    elif isinstance(node, (list, tuple)):
        for i, v in enumerate(node):
            offenders.extend(_dream_label_offenders(v, path=f"{path}[{i}]"))
    return offenders


def _flag_dream_label(text: str, *, path: str) -> list[str]:
    lowered = text.lower()
    if "dream" in lowered and ("not" in lowered or "never" in lowered or "deny" in lowered):
        return []
    tokens = set(lowered.replace("-", " ").replace("_", " ").split())
    if tokens & _DREAM_BANNED:
        return [f"{path}: {text[:120]}"]
    return []


def _assert_no_invented_literature(
    payload: dict[str, Any],
    mem: PersistentMemory,
) -> None:
    """Dream may only cite ids/terms already in memory — no new literature."""
    from artificial_emotions.errors import ERR_VALIDATION, CuriosityError

    allowed = _allowed_tokens(mem)
    # Literature-shaped patterns that must not appear unless already stored.
    suspicious = (
        "arxiv.org",
        "doi.org",
        "doi:",
        "et al.",
        "proceedings of",
        "journal of",
        "isbn",
        "pmid:",
    )
    blob = " ".join(_walk_strings(payload)).lower()
    for marker in suspicious:
        if marker in blob and marker not in allowed:
            raise CuriosityError(
                ERR_VALIDATION,
                "reanalysis invented literature-shaped content not present in memory",
                details={"marker": marker},
            )


def _allowed_tokens(mem: PersistentMemory) -> set[str]:
    """Everything already on disk that dream is allowed to echo."""
    allowed: set[str] = set()
    for session in mem.sessions:
        for qid in session.question_ids:
            allowed.add(qid.lower())
        for d in session.dead_ends:
            allowed.add(d.lower())
        for t in session.terms:
            allowed.add(t.lower())
        if session.topic:
            allowed.add(session.topic.lower())
        if session.domain:
            allowed.add(session.domain.lower())
        if session.stopped_because:
            allowed.add(session.stopped_because.lower())
    for qid in mem.encounters:
        allowed.add(str(qid).lower())
    for entry in list(mem.scars) + list(mem.affinities):
        if isinstance(entry, dict):
            for v in entry.values():
                if isinstance(v, str):
                    allowed.add(v.lower())
    # Honesty / framing strings are always allowed.
    allowed.add(HONESTY_REANALYSIS)
    allowed.add(HONESTY_IMAGINED)
    allowed.update(c.lower() for c in dream_claims_not())
    return allowed
