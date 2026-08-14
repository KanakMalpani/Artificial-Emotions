"""Emotion catalog / cue annotation commands (and the `epistemic` alias)."""

from __future__ import annotations

import argparse
import json
import sys


def _parse_mix_parts(parts: list[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for part in parts:
        raw = part.strip()
        if "=" not in raw:
            raise ValueError(
                f"Expected emotion_id=percent, got '{part}'. "
                "Example: curiosity=40 confusion=30 awe=30"
            )
        key, val = raw.split("=", 1)
        kid = key.strip().lower().replace("-", "_")
        if not kid:
            raise ValueError(f"Empty emotion id in '{part}'")
        out[kid] = float(val.strip())
    return out


def _print_pack_check(payload: dict) -> None:
    print("Pack check (CONTRIBUTING operationalization + why_it_matters)")
    print(
        f"  packs={payload.get('n_packs')}  questions={payload.get('n_questions')}  "
        f"errors={payload.get('n_errors')}  warnings={payload.get('n_warnings')}  "
        f"ok={payload.get('ok')}"
    )
    for pack in payload.get("packs") or []:
        source = str(pack.get("source") or pack.get("name") or "")
        label = source.replace("\\", "/").rsplit("/", 1)[-1] or source
        mark = "OK" if pack.get("ok") else "FAIL"
        print(f"  [{mark}] {label}  {pack.get('n_questions')} questions")
        for issue in pack.get("issues") or []:
            qid = issue.get("question_id") or ""
            loc = f"  {qid}" if qid else ""
            print(f"    {issue.get('severity')} {issue.get('code')}{loc}: {issue.get('message')}")
    honesty = payload.get("honesty")
    if honesty:
        print(f"\n{honesty}")


def _emotions(args: argparse.Namespace) -> int:
    from artificial_emotions.emotions import (
        annotate_epistemic,
        elicit_helpers,
        emotion_catalog,
        emotion_pack,
        list_epistemic_cues,
        mix_emotions,
    )

    cmd = getattr(args, "emotions_cmd", None)
    if not cmd:
        print(
            "Usage: curiosity emotions {cues|catalog|mix|annotate|elicit|pack|memory|dream}\n"
            "  (alias: curiosity epistemic …)\n"
            "  pack check: lint bundled (or --path) packs against CONTRIBUTING bar\n"
            "  mix example: curiosity emotions mix curiosity=40 confusion=30 awe=30\n"
            "Emotion tags/mixes are UX annotations — this system does not feel.",
            file=sys.stderr,
        )
        return 2

    if cmd == "memory":
        from artificial_emotions.cli_pkg.commands.memory import _memory

        return _memory(args)

    if cmd == "dream":
        from artificial_emotions.cli_pkg.commands.dream import _dream

        return _dream(args)

    if cmd == "cues":
        payload = list_epistemic_cues()
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print("Epistemic cue tags (annotation only — does not feel)\n")
            for c in payload["cues"]:
                print(f"  {c['tag']}: {c['meaning']}")
            print(f"\n{payload['disclaimer']}")
        return 0

    if cmd == "catalog":
        try:
            payload = emotion_catalog(family=getattr(args, "family", None))
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(
                f"Emotion catalog v{payload.get('version')} — "
                f"{payload['count']} emotions (annotation only)\n"
            )
            for e in payload["emotions"]:
                print(f"  {e['id']:14} [{e['family']}] {e['label']}")
                use_for = str(e.get("use_for") or "").strip()
                if use_for:
                    print(f"    {use_for}")
            print(f"\n{payload['disclaimer']}")
        return 0

    if cmd == "mix":
        try:
            weights = _parse_mix_parts(list(args.parts))
            sim_feel = str(getattr(args, "simulate_feeling", "true")).lower() in (
                "true",
                "1",
                "yes",
            )
            payload = mix_emotions(weights, simulate_feeling=sim_feel)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"primary={payload['primary']}")
            print(
                "mix=" + ", ".join(f"{c['id']}={c['percent']:.1f}%" for c in payload["components"])
            )
            if payload.get("cue_tags"):
                print(f"cues={', '.join(payload['cue_tags'])}")
            print(payload["inject_fragment"])
            print(payload["disclaimer"])
        return 0

    if cmd == "annotate":
        try:
            payload = annotate_epistemic(
                args.question,
                gap_status=args.gap_status,
                surprise=args.surprise,
                neglectedness=args.neglectedness,
                answerability=args.answerability,
                notes=args.notes,
                domain=args.domain,
            )
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            cues = payload["epistemic_cues"]
            print(f"primary={cues['primary']}")
            print(f"tags={', '.join(cues['tags'])}")
            if payload.get("inject_fragment"):
                print(payload["inject_fragment"])
            print(payload["disclaimer"])
        return 0

    if cmd == "elicit":
        payload = elicit_helpers()
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(payload["framing"])
            print()
            print(payload["inject_prefix"])
        return 0

    if cmd == "pack":
        pack_cmd = getattr(args, "pack_cmd", None) or "load"
        if pack_cmd == "check":
            from artificial_emotions.packs import check_packs

            payload = check_packs(
                paths=getattr(args, "pack_paths", None),
                name=getattr(args, "name", None),
            )
            if args.json:
                print(json.dumps(payload, indent=2))
            else:
                _print_pack_check(payload)
            return 0 if payload.get("ok") else 1
        try:
            payload = emotion_pack(getattr(args, "name", None) or "affective_science")
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"{payload['name']} v{payload.get('version')} — {payload['count']} questions")
            print(payload.get("description") or "")
            for q in payload["questions"][:5]:
                print(f"  - {q['id']}: {q['question'][:100]}")
            if payload["count"] > 5:
                print(f"  … +{payload['count'] - 5} more (use --json)")
            print(f"\n{payload['disclaimer']}")
        return 0

    print(f"Unknown emotions subcommand: {cmd}", file=sys.stderr)
    return 2
