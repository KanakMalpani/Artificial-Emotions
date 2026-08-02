"""CLI: persistent memory show | forget | reset | avoiding."""

from __future__ import annotations

import argparse
import json
import sys

from artificial_emotions.memory import PersistentMemory, memory_disabled


def _memory(args: argparse.Namespace) -> int:
    """Handle ``emotions memory …`` and top-level ``memory …``."""
    cmd = getattr(args, "memory_cmd", None)
    if not cmd:
        print(
            "Usage: emotions memory {show|forget|reset|avoiding}\n"
            "  Local JSON at ~/.artificial_emotions/memory.json (CLI only).\n"
            "  Opt out: CURIOSITY_NO_MEMORY=1. Annotation continuity — does not feel.",
            file=sys.stderr,
        )
        return 2

    if memory_disabled():
        msg = {
            "disabled": True,
            "reason": "CURIOSITY_NO_MEMORY is set — no read or write",
        }
        if getattr(args, "json", False):
            print(json.dumps(msg, indent=2))
        else:
            print("Persistent memory disabled (CURIOSITY_NO_MEMORY=1).", file=sys.stderr)
        return 0

    path = getattr(args, "path", None)
    mem = PersistentMemory.load(path)

    if cmd == "show":
        payload = mem.show()
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"memory file: {payload['path']}")
            print(f"sessions: {len(payload['sessions'])} (cap {payload['max_sessions']})")
            print(
                f"encounters: {len(payload['encounters'])}  "
                f"selections: {len(payload.get('selections') or {})}"
            )
            print(f"scars: {len(payload['scars'])}  affinities: {len(payload['affinities'])}")
            for line in payload.get("scars_plain") or []:
                print(f"  scar: {line}")
            for line in payload.get("affinities_plain") or []:
                print(f"  affinity: {line}")
            mood = payload["mood_carryover"]
            stamp = mood.get("updated_at") or "never"
            print(
                "mood_carryover: "
                f"P={mood['pleasure']} A={mood['arousal']} D={mood['dominance']} "
                f"(updated_at={stamp})"
            )
            if payload["sessions"]:
                print("\nrecent sessions:")
                for s in payload["sessions"][-5:]:
                    print(
                        f"  {s['session_id']}  [{s['domain']}]  "
                        f"{s['steps_taken']} steps  {s['primary_feeling']}"
                    )
            print(f"\n{payload['privacy_notice']}")
        return 0

    if cmd == "avoiding":
        from artificial_emotions.avoidance import avoiding_payload

        payload = avoiding_payload(
            encounters=mem.encounters,
            selections=mem.selections,
        )
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            if not payload["avoiding"]:
                print(
                    "No persistent non-selection patterns "
                    f"(need ≥{payload['min_encounters']} encounters, 0 selections)."
                )
                print(payload["note"])
                return 0
            print(f"avoiding: {payload['count']} pattern(s)\n")
            for item in payload["avoiding"]:
                print(
                    f"  {item['question_id']}: seen {item['encounters']}, "
                    f"picked {item['selections']}"
                )
            if payload["monologue"]:
                print(f"\n{payload['monologue']}")
            print(f"\n{payload['note']}")
        return 0

    if cmd == "forget":
        result = mem.forget(getattr(args, "what", ""))
        if result.get("forgot"):
            mem.save()
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result.get("forgot"):
                print(f"forgot: {result}")
            else:
                print(f"nothing forgotten: {result.get('reason')}", file=sys.stderr)
                return 1
        return 0

    if cmd == "reset":
        mem.reset()
        deleted = mem.delete_file()
        # ensure empty file is gone; if delete failed because missing, still ok
        payload = {"reset": True, "deleted_file": deleted, "path": str(mem.path)}
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"memory reset. deleted_file={deleted} path={mem.path}")
        return 0

    print(f"Unknown memory subcommand: {cmd}", file=sys.stderr)
    return 2
