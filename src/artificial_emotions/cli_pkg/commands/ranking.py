"""Ranking surfaces: `run`, `spark`, and `serve`.

`discover` / `stance` / `imagine` live in ``lenses``; ``explore`` lives in
``commands/explore.py``. Both are re-exported here so ``commands/__init__.py``
and the dispatch table keep a stable import path. Parser groups live under
``cli_pkg/parser/``; ``build_parser`` is the facade.
"""

from __future__ import annotations

import argparse
import json
import sys

from artificial_emotions.cli_pkg.commands.explore import _explore
from artificial_emotions.cli_pkg.commands.lenses import (
    _discover,
    _imagine,
    _stance,
)
from artificial_emotions.models import (
    CuriosityConfig,
    resolve_value_profile,
)
from artificial_emotions.pipeline import CuriosityEngine
from artificial_emotions.provoke import provoke

__all__ = [
    "_discover",
    "_explore",
    "_imagine",
    "_run_engine",
    "_serve",
    "_spark",
    "_stance",
]


def _run_engine(args: argparse.Namespace) -> int:
    profile = resolve_value_profile(profile_name=args.profile)
    config = CuriosityConfig(
        domain=args.domain,
        topic=args.topic,
        n_candidates=args.candidates,
        n_return=args.n,
        use_llm=args.llm,
        use_literature=not args.no_literature,
        literature_backend=args.literature_backend,
        literature_cache_dir=args.lit_cache,
        literature_workers=max(1, min(16, int(getattr(args, "lit_workers", 4) or 4))),
        llm_model=args.model,
        judge_model=args.judge_model,
        judge_ensemble_n=args.judge_ensemble,
        llm_base_url=args.base_url,
        value_profile=profile,
        diversity_backend=args.diversity,
        preference_log_path=args.preference_log,
        preference_rerank_path=getattr(args, "preference_rerank", None),
        preference_learn_path=getattr(args, "preference_learn", None),
        preference_learn_apply=bool(getattr(args, "preference_learn_apply", False)),
    )
    results = CuriosityEngine(config).run()

    if args.json:
        print(json.dumps([r.model_dump(mode="json") for r in results], indent=2))
        return 0

    print(f"\nArtificial Emotions - domain={args.domain}")
    print(f"ValueProfile: {profile.name}")
    print(f"Literature backend: {args.literature_backend if not args.no_literature else 'none'}")
    print("What should we investigate next?\n")
    for r in results:
        band = ""
        if r.score_low is not None and r.score_high is not None:
            band = f"  [{r.score_low:.2f}–{r.score_high:.2f}]"
        print(f"#{r.rank}  score={r.curiosity_score:.3f}{band}  conf={r.confidence:.2f}")
        print(f"    {r.question.question}")
        print(f"    gap={r.gap.status.value}  flags={','.join(r.flags) or 'none'}")
        print()
    return 0


def _serve(args: argparse.Namespace) -> int:
    from artificial_emotions.config import (
        bind_is_loopback,
        configured_api_keys,
        refuse_nonlocal_bind_reason,
        resolve_serve_bind,
    )

    host, port = resolve_serve_bind(getattr(args, "host", None), getattr(args, "port", None))
    reason = refuse_nonlocal_bind_reason(host)
    if reason:
        print(reason, file=sys.stderr)
        return 2
    if not bind_is_loopback(host) and not configured_api_keys():
        print(
            "Warning: non-loopback bind with no CURIOSITY_API_KEY "
            "(open local-v1 API). Set a key before exposing the port. "
            "Still not TLS / not production. See docs/THREAT_MODEL.md.",
            file=sys.stderr,
        )

    import uvicorn

    print(
        f"Artificial Emotions API → http://{host}:{port}\n"
        f"  Instant spark: GET /v1/curiosity/provoke?domain=ai&n=5\n"
        f"  Emotions:      GET /v1/emotions/catalog  POST /v1/emotions/mix\n"
        f"                 GET /v1/emotions/cues  POST /v1/emotions/annotate\n"
        f"  Stances:       GET /v1/stances  GET /v1/stances/doubt?domain=ai\n"
        f"  Agent guide:   GET /v1/agent\n"
        f"  Agent tools:   GET /v1/agent/tools\n"
        f"  Profiles:      GET /v1/profiles\n"
        f"  OpenAPI:       http://{host}:{port}/docs\n"
        f"  MCP (stdio):   curiosity-mcp\n"
    )
    uvicorn.run(
        "artificial_emotions.api:app",
        host=host,
        port=port,
        reload=args.reload,
    )
    return 0


def _spark(args: argparse.Namespace) -> int:
    pack = provoke(
        domain=args.domain,
        topic=args.topic,
        n=args.n,
        fast=not args.literature,
        use_llm=args.llm,
        use_literature=args.literature,
        profile_name=args.profile,
        llm_model=args.model,
        judge_model=args.judge_model,
        llm_base_url=args.base_url,
        diversity_backend=args.diversity,
    )
    if getattr(args, "compact", False):
        unknowns = pack.get("unknowns") or []
        compact = next((u for u in unknowns if u.get("rank") == 1), None)
        print(json.dumps(compact if compact is not None else {}, indent=2))
        return 0
    if args.json:
        print(json.dumps(pack, indent=2))
        return 0
    print(pack["inject"])
    return 0
