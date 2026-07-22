"""Eval harness: smoke the curiosity layer across domains offline."""

from __future__ import annotations

import json
from pathlib import Path

from artificial_curiosity.models import CuriosityConfig, Domain
from artificial_curiosity.pipeline import CuriosityEngine


def main() -> None:
    out_dir = Path(__file__).resolve().parent
    summary = []
    for domain in Domain:
        if domain == Domain.GENERAL:
            continue
        engine = CuriosityEngine(
            CuriosityConfig(
                domain=domain.value,
                n_return=5,
                use_llm=False,
                use_literature=False,
            )
        )
        results = engine.run()
        summary.append(
            {
                "domain": domain.value,
                "count": len(results),
                "top": [
                    {
                        "rank": r.rank,
                        "score": r.curiosity_score,
                        "question": r.question.question,
                        "gap": r.gap.status.value,
                    }
                    for r in results[:3]
                ],
            }
        )
    path = out_dir / "eval_offline_summary.json"
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {path}")
    for row in summary:
        print(f"\n== {row['domain']} ==")
        for t in row["top"]:
            print(f"  #{t['rank']} {t['score']:.3f} {t['question'][:90]}")


if __name__ == "__main__":
    main()
