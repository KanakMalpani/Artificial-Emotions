/**
 * C4 — Imagination canvas: visually unmistakable quarantine.
 * No scores. Permanently labelled. Impossible to screenshot as a finding.
 */

import { useMemo } from "react";
import { qidFor, type Ranked } from "../../types";

export type QuarantinedItem = {
  id: string;
  kind: string;
  content: string;
  driven_by: string[];
  grounded_in: string[];
  invented: string[];
  status: "imagined";
  confidence: null;
  honesty: "imagined_not_retrieved";
};

/** Local presentation of quarantine UX — not retrieved literature. */
export function buildQuarantine(results: Ranked[]): QuarantinedItem[] {
  if (results.length === 0) {
    return DEMO_QUARANTINE;
  }
  const top = results.slice(0, 3);
  return top.flatMap((r, i) => {
    const id = qidFor(r);
    const premortem: QuarantinedItem = {
      id: `imagined-premortem-${id}`,
      kind: "premortem",
      content: `Suppose pursuing “${r.question.question}” failed quietly. What killed it: an unstated assumption in the operationalization, a literature neighbour we under-weighted, or a risk flag that should have stopped the line earlier?`,
      driven_by: ["skepticism", "suspicion"],
      grounded_in: [id],
      invented: [
        "failure mode narrative",
        "causal attribution not in the corpus",
      ],
      status: "imagined",
      confidence: null,
      honesty: "imagined_not_retrieved",
    };
    if (i === 0) {
      const reform: QuarantinedItem = {
        id: `imagined-reform-${id}`,
        kind: "reformulation",
        content: `A sharper pose of the same unknown: replace vague comparatives with a measurable criterion, name the population, and state what observation would falsify the claim — then re-check the gap.`,
        driven_by: ["elegance", "parsimony", "clarity"],
        grounded_in: [id],
        invented: ["rewritten question text", "falsifier not retrieved"],
        status: "imagined",
        confidence: null,
        honesty: "imagined_not_retrieved",
      };
      return [premortem, reform];
    }
    return [premortem];
  });
}

export const DEMO_QUARANTINE: QuarantinedItem[] = [
  {
    id: "imagined-demo-premortem",
    kind: "premortem",
    content:
      "Suppose the top ranked unknown was pursued for a year and produced nothing publishable. The kill shot was not effort — it was an operationalization that two readers never would have agreed on.",
    driven_by: ["skepticism", "suspicion"],
    grounded_in: ["demo-seed"],
    invented: ["year-long failure narrative", "reader-disagreement claim"],
    status: "imagined",
    confidence: null,
    honesty: "imagined_not_retrieved",
  },
  {
    id: "imagined-demo-reform",
    kind: "reformulation",
    content:
      "Imagine a better-posed version: one question mark, one measurable outcome, one named population, and a falsifier you could check against existing literature this week.",
    driven_by: ["elegance", "clarity"],
    grounded_in: ["demo-seed"],
    invented: ["reformulated question", "falsifier schedule"],
    status: "imagined",
    confidence: null,
    honesty: "imagined_not_retrieved",
  },
];

export type ImaginationCanvasProps = {
  results: Ranked[];
};

export function ImaginationCanvas({ results }: ImaginationCanvasProps) {
  const items = useMemo(() => buildQuarantine(results), [results]);

  return (
    <section
      className="imagine-canvas"
      aria-label="Imagination quarantine"
      data-testid="imagine-canvas"
    >
      <div className="imagine-canvas-banner" data-testid="imagine-quarantine-banner">
        <span className="imagine-stamp">IMAGINED — NOT RETRIEVED</span>
        <p>
          Quarantine surface. Nothing here is a ranked finding. No curiosity
          scores. honesty=imagined_not_retrieved. Imagination cannot feed
          ranking without gap verification.
        </p>
      </div>

      <ul className="imagine-list">
        {items.map((item) => (
          <li
            key={item.id}
            className="imagine-card"
            data-testid="imagine-card"
            data-kind={item.kind}
            data-status="imagined"
          >
            <div className="imagine-card-labels">
              <span className="imagine-permanent-label">imagined</span>
              <span className="imagine-kind">{item.kind}</span>
              <span className="imagine-honesty">{item.honesty}</span>
            </div>
            <p className="imagine-content">{item.content}</p>
            <dl className="imagine-meta">
              <div>
                <dt>driven by</dt>
                <dd>{item.driven_by.join(", ")}</dd>
              </div>
              <div>
                <dt>grounded in</dt>
                <dd>{item.grounded_in.join(", ") || "—"}</dd>
              </div>
              <div>
                <dt>invented</dt>
                <dd>{item.invented.join("; ")}</dd>
              </div>
              <div>
                <dt>confidence</dt>
                <dd data-testid="imagine-confidence-null">null — imagination does not get a score</dd>
              </div>
            </dl>
            {/* Deliberately no score / rank / curiosity_score fields */}
          </li>
        ))}
      </ul>
    </section>
  );
}

export { ImaginationCanvas as default };
