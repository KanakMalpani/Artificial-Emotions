"""CLI: explicit ``emotions dream`` — offline reanalysis of stored history.

Never automatic, never background. CLI may say "dream" once; the payload does not.
"""

from __future__ import annotations

import argparse
import json
import sys

from artificial_emotions.dream import HONESTY_REANALYSIS, reanalyze_history
from artificial_emotions.imagine import IMAGINED_PAYLOAD_KEY
from artificial_emotions.memory import memory_disabled


def _dream(args: argparse.Namespace) -> int:
    """Handle top-level ``dream`` and ``emotions dream``."""
    if memory_disabled():
        msg = {
            "disabled": True,
            "reason": "CURIOSITY_NO_MEMORY is set — no history to reanalyze",
            "framing": HONESTY_REANALYSIS,
        }
        if getattr(args, "json", False):
            print(json.dumps(msg, indent=2))
        else:
            print(
                "Persistent memory disabled (CURIOSITY_NO_MEMORY=1) — nothing to reanalyze.",
                file=sys.stderr,
            )
        return 0

    path = getattr(args, "path", None)
    payload = reanalyze_history(path=path)

    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2))
        return 0

    # Say "dream" once — then speak only of offline reanalysis.
    print("dream — offline reanalysis of stored history\n")
    analysis = payload.get("analysis") or {}
    findings = analysis.get("findings") or []
    print(
        f"sessions={analysis.get('n_sessions', 0)}  "
        f"scars={analysis.get('n_scars', 0)}  "
        f"encounters={analysis.get('n_encounters', 0)}  "
        f"findings={len(findings)}"
    )
    print(f"framing: {payload.get('framing') or payload.get('reanalysis_honesty')}")
    print(f"honesty: {payload.get('honesty')}  confidence: {payload.get('confidence')!r}")

    if not findings:
        print("\nNo cross-session structure found in stored history.")
    else:
        print("\nfindings:")
        for item in findings:
            ftype = item.get("type")
            if ftype == "recurring_dead_end":
                print(
                    f"  recurring dead end: {item['question_id']} ({item['n_sessions']} sessions)"
                )
            elif ftype == "cross_session_term":
                print(
                    f"  cross-session term: {item['term']!r} "
                    f"({item['n_sessions']} unconnected sessions)"
                )
            elif ftype == "mismatched_scar":
                print(
                    f"  mismatched scar: {item['target']} — {'; '.join(item.get('reasons') or [])}"
                )
            elif ftype == "unselected_recurring_encounter":
                print(
                    f"  unselected encounter: {item['question_id']} "
                    f"seen {item['encounters']}, picked {item['selections']}"
                )
            else:
                print(f"  {ftype}: {item}")

    imagined = payload.get(IMAGINED_PAYLOAD_KEY) or []
    if imagined:
        print(f"\n{IMAGINED_PAYLOAD_KEY} (quarantine, not retrieved):")
        for entry in imagined:
            print(f"  [{entry.get('kind')}] {entry.get('content')}")
            for claim in (entry.get("invented") or [])[:4]:
                print(f"      invented: {claim}")

    print(f"\n{payload.get('note') or ''}")
    # Do not re-print the word "dream" — banner already used it once.
    claims = [c for c in (payload.get("claims_not") or []) if "dream" not in str(c).lower()]
    if claims:
        print("claims_not: " + "; ".join(claims[:3]))
    return 0
