"""Fresh offline vs literature compare → examples/run_ai_*_final.json."""

from __future__ import annotations

import json
from pathlib import Path

from artificial_curiosity import CuriosityEngine, CuriosityConfig

out = Path("examples")
out.mkdir(exist_ok=True)

for use_lit, fname in [
    (False, "run_ai_offline_final.json"),
    (True, "run_ai_literature_final.json"),
]:
    cfg = CuriosityConfig(domain="ai", n_return=5, use_literature=use_lit)
    results = CuriosityEngine(cfg).run_dict()
    path = out / fname
    path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    mode = "literature" if use_lit else "offline"
    print(f"[{mode}] Wrote {path} ({len(results)} items)")
    for i, r in enumerate(results[:3], 1):
        gap = r.get("gap", {})
        rel = gap.get("related_works", [])
        qtext = r["question"]["question"]
        print(
            f"  #{i} score={r['curiosity_score']:.3f} conf={r['confidence']:.2f} "
            f"gap={gap.get('status')} related={len(rel)} "
            f"overlap={gap.get('top_overlap', 0):.2f} flags={r.get('flags')}"
        )
        print(f"      {qtext[:120]}")
