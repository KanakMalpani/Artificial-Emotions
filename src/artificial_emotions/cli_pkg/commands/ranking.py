"""Ranking surfaces: `run`, `spark`, and `serve`."""

from __future__ import annotations

import argparse
import json

from artificial_emotions.models import (
    CuriosityConfig,
    resolve_value_profile,
)
from artificial_emotions.pipeline import CuriosityEngine
from artificial_emotions.provoke import provoke


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
    import uvicorn

    print(
        f"Artificial Emotions API → http://{args.host}:{args.port}\n"
        f"  Instant spark: GET /v1/curiosity/provoke?domain=ai&n=5\n"
        f"  Emotions:      GET /v1/emotions/catalog  POST /v1/emotions/mix\n"
        f"                 GET /v1/emotions/cues  POST /v1/emotions/annotate\n"
        f"  Stances:       GET /v1/stances  GET /v1/stances/doubt?domain=ai\n"
        f"  Agent guide:   GET /v1/agent\n"
        f"  Agent tools:   GET /v1/agent/tools\n"
        f"  Profiles:      GET /v1/profiles\n"
        f"  OpenAPI:       http://{args.host}:{args.port}/docs\n"
        f"  MCP (stdio):   curiosity-mcp\n"
    )
    uvicorn.run(
        "artificial_emotions.api:app",
        host=args.host,
        port=args.port,
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


def _explore(args: argparse.Namespace) -> int:
    """Run the curiosity loop and print the trajectory."""
    from artificial_emotions.explore import explore
    from artificial_emotions.memory import memory_disabled

    # CLI-only persistence by default; MCP/HTTP never enable it.
    persist = not getattr(args, "no_memory", False) and not memory_disabled()
    payload = explore(
        domain=args.domain,
        topic=args.topic,
        steps=args.steps,
        n_return=args.n,
        profile_name=args.profile,
        use_literature=args.literature,
        allow_weight_deltas=args.affect_weights,
        allow_domain_jump=not args.no_jump,
        persist_memory=persist,
        preference_log_path=getattr(args, "preference_log", None),
    )
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"\nExploring {payload['domain_started']} — {payload['steps_taken']} steps\n")
    for step in payload["trajectory"]["steps"]:
        drivers = {c["driver"] for c in step["modulation"]}
        acted = [a for a in step["appraisal"] if a["emotion"] in drivers]
        observed = [a for a in step["appraisal"] if a["emotion"] not in drivers]

        print(f"  step {step['step']}  [{step['domain']}]  {len(step['new_question_ids'])} new")
        if acted:
            print(
                "      acted:    " + ", ".join(f"{a['emotion']} {a['weight']:.2f}" for a in acted)
            )
        if observed:
            print(
                "      observed: "
                + ", ".join(f"{a['emotion']} {a['weight']:.2f}" for a in observed[:6])
            )
        for change in step["modulation"]:
            print(f"      · {change['knob']}: {change['before']} → {change['after']}")
            print(f"        because {change['driver']} — {change['rationale']}")
        for cost in step.get("costs") or []:
            print(f"      ✗ cost {cost['kind']}: {cost['disclosure']}")
        print(f"      → {step['note']}\n")

    print(f"Stopped: {payload['stopped_because']}")
    print(f"Ground covered: {', '.join(payload['trajectory']['domains_visited'])}")

    best = payload.get("best_found")
    if best:
        print(f"\nBest found  [score {best['curiosity_score']:.3f}]")
        print(f"  {best['question']}")

    feeling = payload.get("final_feeling")
    if feeling:
        print(f"\n{feeling['inner_monologue']}")
    avoiding = payload.get("avoiding") or (feeling or {}).get("avoiding")
    if avoiding:
        print(
            "\n(Pattern note: non-selection is either judgment or avoidance — "
            "cannot tell which. Annotation only; does not feel.)"
        )

    plan = payload.get("investigation_plan")
    if plan:
        step = plan["discriminating_step"]
        print(f"\nDo this first ({step['kind']}, cost {step['expected_cost_band']}):")
        print(f"  {step['observation']}")
    print(f"\n{payload['claims_not'][0].capitalize()} is not claimed here.")
    return 0


def _discover(args: argparse.Namespace) -> int:
    """Literature-based discovery: propose links nobody has studied."""
    from artificial_emotions.discover import discover

    payload = discover(
        args.seed,
        max_bridges=args.bridges,
        max_links=args.n,
        cooccurrence_ceiling=args.ceiling,
        cache_dir=args.cache_dir,
        corpus=args.corpus,
    )
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    if not payload["ok"]:
        print(f"\nDiscovery failed: {payload.get('error')}")
        print(payload["note"])
        return 1

    print(
        f"\nLiterature-based discovery from '{payload['seed']}'"
        f"  (Swanson ABC · source: {payload.get('source', 'unknown')})\n"
    )
    if not payload["links"]:
        print("  No disconnected links found. Try a narrower seed concept,")
        print("  or raise --ceiling if the field is very large.")
        return 0

    for link in payload["links"]:
        print(f"  {link['a']}  --[{link['b']}]-->  {link['c']}")
        print(f"      co-occurrence: {link['ac_cooccurrence']} works   gap: {link['gap_score']}")
        print(f"      Q: {link['question']}")
        for title in link["evidence_ab"][:1]:
            print(f"      evidence A-B: {title[:80]}")
        for title in link["evidence_bc"][:1]:
            print(f"      evidence B-C: {title[:80]}")
        print()

    print(payload["how_to_read"])
    print(f"\nNot claimed: {payload['claims_not'][0]}.")
    return 0


def _stance(args: argparse.Namespace) -> int:
    """Look at a ranked set through one emotional stance."""
    from artificial_emotions.stances import apply_stance, list_stances

    if args.stance_name in (None, "list"):
        catalog = list_stances()
        if args.json:
            print(json.dumps(catalog, indent=2))
            return 0
        print("\nStances — different questions to ask of the same ranked set\n")
        for s in catalog["stances"]:
            print(f"  {s['stance']:8} {s['asks']}")
            print(f"           use when: {s['use_when']}")
            print(f"           driven by: {', '.join(s['driving_emotions'])}\n")
        print(catalog["note"])
        return 0

    profile = resolve_value_profile(profile_name=args.profile)
    items = CuriosityEngine(
        CuriosityConfig(
            domain=args.domain,
            topic=args.topic,
            n_return=args.n,
            use_llm=False,
            use_literature=args.literature,
            value_profile=profile,
        )
    ).run()
    payload = apply_stance(args.stance_name, items)

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"\n[{payload['stance']}]  {payload['asks']}")
    print(f"driven by: {', '.join(payload['driving_emotions'])}\n")
    view = payload["view"]
    for key, value in view.items():
        if key == "note":
            continue
        if isinstance(value, list):
            for row in value:
                if isinstance(row, dict):
                    head = row.get("question") or row.get("term") or str(row)
                    print(f"  · {str(head)[:88]}")
                    for field_name in (
                        "doubt_score",
                        "risk_axis",
                        "form_score",
                        "crowding",
                        "reason",
                        "needs_human_review",
                    ):
                        if field_name in row:
                            print(f"      {field_name}: {row[field_name]}")
                    for list_field in ("reasons_to_distrust", "problems", "flags"):
                        for entry in row.get(list_field) or []:
                            print(f"      - {entry}")
                    if row.get("advice"):
                        print(f"      → {row['advice']}")
                else:
                    print(f"  · {row}")
            print()
        elif isinstance(value, dict) and key == "target":
            print(f"  target: {value['question']}\n")
        elif not isinstance(value, dict):
            print(f"  {key}: {value}\n")
    if view.get("note"):
        print(view["note"])
    print(f"\nNot claimed: {payload['claims_not'][0]}.")
    return 0


def _imagine(args: argparse.Namespace) -> int:
    """Generate quarantined imagined content (premortem / reformulation / …)."""
    from artificial_emotions.imagine import (
        HONESTY_IMAGINED,
        IMAGINED_PAYLOAD_KEY,
        apply_imagination,
        list_imagination_kinds,
    )

    if args.imagine_kind in (None, "list"):
        catalog = list_imagination_kinds()
        if args.json:
            print(json.dumps(catalog, indent=2))
            return 0
        print("\nImagination — generative twins of stances (quarantined)\n")
        for entry in catalog["kinds"]:
            gen = entry.get("generator")
            if gen == "wired":
                label = "wired"
            elif gen == "corpus_gated":
                label = "corpus-gated"
            elif gen == "cut":
                label = "cut"
            else:
                label = "registry only"
            print(f"  {entry['kind']:14} [{label}]  {entry['asks']}")
            print(f"                 twin of: {entry.get('stance_twin') or '—'}")
            print(f"                 use when: {entry['use_when']}")
            print(f"                 driven by: {', '.join(entry['driving_emotions'])}\n")
        print(catalog["note"])
        print(f"honesty: {catalog['honesty']}")
        return 0

    # B3 transfer is corpus-gated — not applied over a ranked set.
    if (args.imagine_kind or "").strip().lower() == "transfer":
        from artificial_emotions.transfer import imagine_transfer

        seed = (getattr(args, "seed", "") or "").strip()
        corpus = (getattr(args, "corpus", "") or "").strip()
        if not seed or not corpus:
            print(
                "transfer requires --seed and --corpus "
                "(structural analogy over a local literature corpus).\n"
                "Example: emotions imagine transfer --seed 'Fish oil' "
                "--corpus examples/discovery_corpus_timesplit_demo.json"
            )
            return 2
        payload = imagine_transfer(seed, corpus=corpus, max_links=args.n)
        if args.json:
            print(json.dumps(payload, indent=2))
            return 0 if payload.get("ok", True) else 1
        if not payload.get("ok", True) and payload.get("ship_status") == "cut":
            print(f"\n[imagine:transfer] CUT — {payload.get('note')}")
            return 1
        print(f"\n[imagine:transfer]  {payload.get('asks')}")
        print(f"driven by: {', '.join(payload.get('driving_emotions') or [])}")
        print(f"honesty: {payload['honesty']}  confidence: {payload['confidence']!r}")
        print(f"ship_status={payload.get('ship_status')}  method={payload.get('method')}")
        print(f"offline={payload.get('offline')}  network={payload.get('network')}\n")
        for entry in payload.get(IMAGINED_PAYLOAD_KEY) or []:
            print(f"  · {str(entry.get('content', ''))[:140]}")
            grounded = entry.get("grounded_in") or []
            if grounded:
                print(f"      grounded_in: {', '.join(grounded)}")
            for claim in (entry.get("invented") or [])[:4]:
                print(f"      invented: {claim}")
            print(f"      status={entry.get('status')}  confidence={entry.get('confidence')!r}")
            print()
        if payload.get("note"):
            print(payload["note"])
        assert payload["honesty"] == HONESTY_IMAGINED
        print(f"\nNot claimed: {payload['claims_not'][0]}.")
        return 0

    profile = resolve_value_profile(profile_name=args.profile)
    items = CuriosityEngine(
        CuriosityConfig(
            domain=args.domain,
            topic=args.topic,
            n_return=args.n,
            use_llm=False,
            use_literature=bool(getattr(args, "literature", False)),
            value_profile=profile,
        )
    ).run()
    payload = apply_imagination(args.imagine_kind, items)

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"\n[imagine:{payload['kind']}]  {payload['asks']}")
    print(f"driven by: {', '.join(payload['driving_emotions'])}")
    print(f"honesty: {payload['honesty']}  confidence: {payload['confidence']!r}")
    print(f"offline={payload.get('offline')}  network={payload.get('network')}\n")
    for entry in payload.get(IMAGINED_PAYLOAD_KEY) or []:
        print(f"  · {str(entry.get('content', ''))[:120]}")
        grounded = entry.get("grounded_in") or []
        invented = entry.get("invented") or []
        if grounded:
            print(f"      grounded_in: {', '.join(grounded)}")
        for claim in invented[:4]:
            print(f"      invented: {claim}")
        print(f"      status={entry.get('status')}  confidence={entry.get('confidence')!r}")
        print()
    if payload.get("note"):
        print(payload["note"])
    assert payload["honesty"] == HONESTY_IMAGINED
    print(f"\nNot claimed: {payload['claims_not'][0]}.")
    return 0
