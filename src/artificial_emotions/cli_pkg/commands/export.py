"""CLI: `emotions export unknowns` — file/JSON document, no webhooks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from artificial_emotions.export_unknowns import (
    DELIVERY_FILE,
    DELIVERY_STDOUT,
    coerce_ranked_questions,
    export_unknowns,
    write_unknowns_export,
)
from artificial_emotions.models import (
    CuriosityConfig,
    resolve_value_profile,
)
from artificial_emotions.pipeline import CuriosityEngine


def _export(args: argparse.Namespace) -> int:
    cmd = getattr(args, "export_cmd", None)
    if cmd != "unknowns":
        print(
            "Usage: emotions export unknowns [--json] [--out PATH] "
            "[--from PATH | run flags]\n"
            "  File export is the v1 path. Webhook URLs are not accepted (SSRF).\n"
            "  Scores are decision aids with an explicit ValueProfile — not oracles.",
            file=sys.stderr,
        )
        return 2
    return _export_unknowns(args)


def _run_pipeline(args: argparse.Namespace) -> tuple[list[object], object]:
    profile = resolve_value_profile(profile_name=args.profile)
    config = CuriosityConfig(
        domain=args.domain,
        topic=args.topic,
        n_candidates=args.candidates,
        n_return=args.n,
        use_llm=bool(getattr(args, "llm", False)),
        use_literature=not bool(getattr(args, "no_literature", False)),
        literature_backend=getattr(args, "literature_backend", "openalex"),
        literature_cache_dir=getattr(args, "lit_cache", None),
        literature_workers=max(1, min(16, int(getattr(args, "lit_workers", 4) or 4))),
        llm_model=getattr(args, "model", "gpt-4o-mini"),
        judge_model=getattr(args, "judge_model", None),
        judge_ensemble_n=int(getattr(args, "judge_ensemble", 1) or 1),
        llm_base_url=getattr(args, "base_url", None),
        value_profile=profile,
        diversity_backend=getattr(args, "diversity", "jaccard"),
        preference_log_path=getattr(args, "preference_log", None),
        preference_rerank_path=getattr(args, "preference_rerank", None),
        preference_learn_path=getattr(args, "preference_learn", None),
        preference_learn_apply=bool(getattr(args, "preference_learn_apply", False)),
    )
    return list(CuriosityEngine(config).run()), profile


def _export_unknowns(args: argparse.Namespace) -> int:
    from_path = getattr(args, "from_path", None)
    out_path = getattr(args, "out", None)
    delivery = DELIVERY_FILE if out_path else DELIVERY_STDOUT

    profile_name = getattr(args, "profile", None)
    domain = getattr(args, "domain", "") or ""
    topic = getattr(args, "topic", "") or ""
    literature_backend = "none"
    value_profile = None

    try:
        if from_path:
            raw = json.loads(Path(from_path).read_text(encoding="utf-8"))
            questions = coerce_ranked_questions(raw)
            if isinstance(raw, dict):
                domain = str(raw.get("domain") or domain)
                topic = str(raw.get("topic") or topic)
                profile_name = raw.get("profile_name") or profile_name
                literature_backend = str(raw.get("literature_backend") or literature_backend)
                maybe_profile = raw.get("value_profile")
                if isinstance(maybe_profile, dict):
                    value_profile = maybe_profile
                    profile_name = profile_name or maybe_profile.get("name")
        else:
            questions, profile = _run_pipeline(args)
            value_profile = profile.model_dump(mode="json")
            profile_name = profile.name
            literature_backend = (
                args.literature_backend if not getattr(args, "no_literature", False) else "none"
            )

        document = export_unknowns(
            questions,
            domain=domain,
            topic=topic,
            profile_name=profile_name,
            value_profile=value_profile,
            literature_backend=literature_backend,
            delivery=delivery,
        )
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if out_path:
        try:
            written = write_unknowns_export(document, out_path)
        except OSError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if not args.json:
            print(f"Wrote {document['count']} unknowns to {written}")
            print(document["honesty"])
            return 0

    if args.json:
        print(json.dumps(document, indent=2))
        return 0

    print(f"\nExported {document['count']} ranked unknowns  delivery={document['delivery']}")
    print(f"ValueProfile: {document.get('profile_name') or 'unspecified'}")
    print("Webhooks: not accepted (SSRF). File / --json is the v1 path.\n")
    for row in document["questions"]:
        rank = row.get("rank")
        score = row.get("curiosity_score")
        q = row.get("question")
        text = q.get("question") if isinstance(q, dict) else q
        band = ""
        if score is not None:
            band = f"  score={score}"
        print(f"#{rank}{band}")
        print(f"    {text}")
        print()
    print(document["honesty"])
    return 0
