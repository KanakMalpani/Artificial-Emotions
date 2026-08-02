/**
 * C3 — Trajectory map: steps, mood colour, dead ends, cost markers, hover appraisal.
 */

import { useMemo, useState } from "react";
import {
  DEMO_TRAJECTORY,
  moodColour,
  sketchFromResults,
  type TrajectoryStepView,
  type TrajectoryView,
} from "./trajectoryTypes";
import type { Ranked } from "../../types";

export type TrajectoryMapProps = {
  domain: string;
  topic: string;
  results: Ranked[];
  /** Optional explore payload; falls back to session sketch / demo. */
  trajectory?: TrajectoryView | null;
};

export function TrajectoryMap({
  domain,
  topic,
  results,
  trajectory,
}: TrajectoryMapProps) {
  const view: TrajectoryView = useMemo(() => {
    if (trajectory && trajectory.steps.length > 0) return trajectory;
    if (results.length > 0) {
      return sketchFromResults(
        domain,
        topic,
        results.map((r) => ({
          question: r.question.question,
          curiosity_score: r.curiosity_score,
          flags: r.flags,
        })),
      );
    }
    return DEMO_TRAJECTORY;
  }, [trajectory, results, domain, topic]);

  const [hoverStep, setHoverStep] = useState<number | null>(null);
  const hovered: TrajectoryStepView | undefined = view.steps.find(
    (s) => s.step === hoverStep,
  );

  return (
    <section
      className="trajectory-map"
      aria-label="Trajectory map"
      data-testid="trajectory-map"
      data-source={view.source}
    >
      <div className="trajectory-map-head">
        <h2 className="trajectory-map-title">Trajectory</h2>
        <p className="trajectory-map-lede">
          Path of the loop — mood colour per step, dead ends drawn as dead ends,
          cost markers where a feeling changed a knob. Hover a step for appraisal
          evidence.
        </p>
        <p className="trajectory-map-source">
          source={view.source}
          {view.source === "demo"
            ? " — illustrative path until explore or a ranking exists"
            : view.source === "session_sketch"
              ? " — derived from this session's ranks (not a full explore)"
              : " — from explore payload"}
        </p>
      </div>

      <ol className="trajectory-path" data-testid="trajectory-path">
        {view.steps.map((step, i) => {
          const dead = !step.made_progress;
          const hasCost = (step.costs?.length ?? 0) > 0;
          const colour = moodColour(step.primary_feeling);
          return (
            <li
              key={step.step}
              className={
                "trajectory-node" +
                (dead ? " is-dead-end" : "") +
                (hasCost ? " has-cost" : "") +
                (hoverStep === step.step ? " is-hover" : "")
              }
              data-testid={`trajectory-step-${step.step}`}
              data-dead-end={dead ? "1" : "0"}
              onMouseEnter={() => setHoverStep(step.step)}
              onMouseLeave={() => setHoverStep(null)}
              onFocus={() => setHoverStep(step.step)}
              onBlur={() => setHoverStep(null)}
              tabIndex={0}
            >
              {i > 0 && (
                <span
                  className={"trajectory-edge" + (dead ? " is-broken" : "")}
                  aria-hidden="true"
                />
              )}
              <button
                type="button"
                className="trajectory-dot"
                style={{ background: colour, borderColor: colour }}
                aria-label={`Step ${step.step}: ${step.primary_feeling}${dead ? ", dead end" : ""}`}
              >
                {step.step}
              </button>
              <div className="trajectory-card">
                <span className="trajectory-feeling" style={{ color: colour }}>
                  {step.primary_feeling || "—"}
                </span>
                <span className="trajectory-domain">{step.domain}</span>
                <p className="trajectory-q">{step.top_question}</p>
                {dead && (
                  <span className="trajectory-dead-label" data-testid="trajectory-dead-end">
                    dead end
                  </span>
                )}
                {hasCost &&
                  step.costs.map((c, ci) => (
                    <span
                      key={ci}
                      className="trajectory-cost-marker"
                      data-testid="trajectory-cost-marker"
                      title={c.disclosure || c.detail || c.kind}
                    >
                      cost: {c.kind || "affect"}
                    </span>
                  ))}
              </div>
            </li>
          );
        })}
      </ol>

      {view.dead_ends.length > 0 && (
        <p className="trajectory-dead-list">
          Dead ends recorded: {view.dead_ends.length}
        </p>
      )}

      {hovered && (
        <aside
          className="trajectory-hover"
          data-testid="trajectory-appraisal"
          aria-live="polite"
        >
          <p className="trajectory-hover-title">
            Step {hovered.step} · appraisal evidence
          </p>
          {(hovered.appraisal?.length ?? 0) === 0 ? (
            <p className="trajectory-hover-empty">No appraisal rows on this step.</p>
          ) : (
            <ul>
              {hovered.appraisal.map((a, i) => (
                <li key={i}>
                  <strong>{a.emotion || a.rule || "signal"}</strong>
                  {a.evidence ? ` — ${a.evidence}` : ""}
                  {a.intensity != null ? ` (intensity ${a.intensity})` : ""}
                </li>
              ))}
            </ul>
          )}
          {hovered.note && <p className="trajectory-hover-note">{hovered.note}</p>}
        </aside>
      )}
    </section>
  );
}

export { TrajectoryMap as default };
