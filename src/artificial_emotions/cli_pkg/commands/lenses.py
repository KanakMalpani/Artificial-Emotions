"""CLI lenses over (or beside) a ranked set: `discover`, `stance`, `imagine`.

Implementations live here so they are not mixed with `run` / `spark` / `serve`.
``ranking.py`` re-exports the handlers so dispatch wiring does not churn.
"""

from __future__ import annotations

import argparse
import json

from artificial_emotions.models import (
    CuriosityConfig,
    resolve_value_profile,
)
from artificial_emotions.pipeline import CuriosityEngine

__all__ = [
    "_discover",
    "_imagine",
    "_stance",
]


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
