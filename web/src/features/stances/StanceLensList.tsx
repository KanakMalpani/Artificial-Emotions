/**
 * C2 — Lens-ordered list with rank-gap animation when wonder disagrees.
 */

import { useMemo, type CSSProperties } from "react";
import type { Ranked } from "../../types";
import { applyLens, type StanceId } from "./lenses";

export type StanceLensListProps = {
  results: Ranked[];
  stance: StanceId;
};

export function StanceLensList({ results, stance }: StanceLensListProps) {
  const lens = useMemo(() => applyLens(stance, results), [stance, results]);

  if (results.length === 0) return null;
  if (stance === "curiosity") return null;

  return (
    <section
      className="stance-lens-panel"
      aria-label={`${stance} lens`}
      data-testid="stance-lens-panel"
      data-stance={stance}
    >
      <p className="stance-lens-note">{lens.note}</p>
      <ol className="stance-lens-list">
        {lens.rows.map((row) => {
          const gap = row.rankGap;
          const disagrees = gap != null && gap !== 0;
          return (
            <li
              key={row.qid}
              className={
                "stance-lens-row" + (disagrees ? " has-rank-gap" : "")
              }
              data-testid={disagrees ? "stance-rank-gap-row" : "stance-lens-row"}
              style={
                disagrees
                  ? ({
                      ["--rank-gap"]: String(Math.min(8, Math.abs(gap))),
                    } as CSSProperties)
                  : undefined
              }
            >
              <span className="stance-lens-rank">#{row.lensRank}</span>
              <div className="stance-lens-body">
                <p className="stance-lens-q">{row.ranked.question.question}</p>
                {row.detail && (
                  <p className="stance-lens-detail">{row.detail}</p>
                )}
                {disagrees && (
                  <span
                    className="rank-gap-chip"
                    data-testid="rank-gap-chip"
                  >
                    rank gap {gap! > 0 ? "+" : ""}
                    {gap}
                    <span className="rank-gap-anim" aria-hidden="true" />
                  </span>
                )}
              </div>
              {row.scoreLabel && (
                <span className="stance-lens-score">{row.scoreLabel}</span>
              )}
            </li>
          );
        })}
      </ol>
    </section>
  );
}

export { StanceLensList as default };
