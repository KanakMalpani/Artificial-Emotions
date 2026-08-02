/**
 * C5 — Confession panel (non-modal): what wasn't checked, flags, memory influence, avoidance.
 * Honesty copy first — pairs with A6 pattern reporting (not motive claims).
 */

import { useMemo } from "react";
import type { Ranked } from "../../types";

export type AvoidancePatternView = {
  question_id: string;
  question?: string;
  encounters: number;
  selections: number;
};

export type ConfessionPanelProps = {
  results: Ranked[];
  profileLabel: string;
  /** Optional explore claims_not + mood_carryover / costs / avoidance. */
  claimsNot?: string[];
  memoryInfluence?: {
    label: string;
    magnitude: string;
    detail: string;
  }[];
  avoidance?: AvoidancePatternView[];
};

const DEFAULT_CLAIMS_NOT = [
  "an answer to any question it surfaced",
  "an optimal or complete search of the field",
  "a closed-loop scientist — it runs no experiments",
  "biological emotion; the affect is a computational blend",
  "a loosened safety or risk gate from affect costs",
  "a motive or psychological cause for non-selection",
];

const CANNOT_DISTINGUISH =
  "That pattern is either good judgment or avoidance, and I can't tell which from here.";

const DEMO_AVOIDANCE: AvoidancePatternView[] = [
  {
    question_id: "ai-04",
    question: "Which dual-use evaluation protocols remain unpublished?",
    encounters: 6,
    selections: 0,
  },
];

export function ConfessionPanel({
  results,
  profileLabel,
  claimsNot,
  memoryInfluence,
  avoidance,
}: ConfessionPanelProps) {
  const unchecked = useMemo(() => {
    const out: string[] = [];
    if (results.length === 0) {
      out.push("No ranking this session — literature neighbourhoods unconsulted.");
      out.push("Gap status not established for any candidate.");
      return out;
    }
    const noLit = results.filter(
      (r) =>
        (r.flags || []).includes("no_literature") ||
        !(r.gap.related_works?.length),
    );
    const heuristic = results.filter((r) =>
      (r.flags || []).includes("heuristic_scoring"),
    );
    const hedged = results.filter(
      (r) => r.gap.status === "unknown_with_caveat" || r.gap.status === "unknown",
    );
    if (noLit.length) {
      out.push(
        `${noLit.length} item(s) without retrieved neighbours — gap unverified.`,
      );
    }
    if (heuristic.length) {
      out.push(
        `${heuristic.length} item(s) scored heuristically — no judge looked at them.`,
      );
    }
    if (hedged.length) {
      out.push(`${hedged.length} item(s) with hedged or unknown gap status.`);
    }
    if (out.length === 0) {
      out.push(
        "Surface checks present; still not a complete search of the field.",
      );
    }
    return out;
  }, [results]);

  const flags = useMemo(() => {
    const map = new Map<string, number>();
    for (const r of results) {
      for (const f of r.flags || []) {
        map.set(f, (map.get(f) || 0) + 1);
      }
    }
    return [...map.entries()].sort((a, b) => b[1] - a[1]);
  }, [results]);

  const mem =
    memoryInfluence && memoryInfluence.length > 0
      ? memoryInfluence
      : results.length > 0
        ? [
            {
              label: "session ranks only",
              magnitude: "0 (no persistent memory loaded in UI)",
              detail:
                "CLI memory can bias thresholds; this panel discloses influence when present. Opt out: CURIOSITY_NO_MEMORY=1.",
            },
          ]
        : [
            {
              label: "none loaded",
              magnitude: "0",
              detail:
                "Fresh UI session. Persistent memory lives on disk (~/.artificial_emotions/memory.json) when enabled in CLI.",
            },
          ];

  const avoid =
    avoidance && avoidance.length > 0
      ? avoidance
      : results.length === 0
        ? DEMO_AVOIDANCE
        : [];

  const claims = claimsNot?.length ? claimsNot : DEFAULT_CLAIMS_NOT;

  return (
    <aside
      className="confession-panel"
      aria-label="Confession panel"
      data-testid="confession-panel"
    >
      <div className="confession-head">
        <h2 className="confession-title">Confession</h2>
        <p className="confession-honesty" data-testid="confession-honesty">
          What this run did not check, what flags fired, what memory biased it,
          and what it walked past. Pattern reporting only — not a claim that the
          system feels, and not mind-reading.
        </p>
      </div>

      <div className="confession-grid">
        <section data-testid="confession-unchecked">
          <h3>Not checked</h3>
          <ul>
            {unchecked.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </section>

        <section data-testid="confession-flags">
          <h3>Flags</h3>
          {flags.length === 0 ? (
            <p className="confession-empty">
              {results.length
                ? "No flags on the current set."
                : "No ranked set yet — flags appear after a run."}
            </p>
          ) : (
            <ul className="confession-flag-list">
              {flags.map(([name, n]) => (
                <li key={name}>
                  <code>{name}</code> ×{n}
                </li>
              ))}
            </ul>
          )}
          <p className="confession-meta">profile={profileLabel}</p>
        </section>

        <section data-testid="confession-memory">
          <h3>Memory influence</h3>
          <ul>
            {mem.map((m) => (
              <li key={m.label}>
                <strong>{m.label}</strong> — {m.magnitude}
                <br />
                <span className="confession-detail">{m.detail}</span>
              </li>
            ))}
          </ul>
        </section>

        <section data-testid="confession-avoidance">
          <h3>Avoidance patterns</h3>
          {avoid.length === 0 ? (
            <p className="confession-empty">
              No persistent non-selection pattern in this session
              (needs ≥6 encounters, 0 selections).
            </p>
          ) : (
            <ul>
              {avoid.map((a) => (
                <li key={a.question_id}>
                  I&apos;ve now seen <code>{a.question_id}</code> in{" "}
                  {a.encounters} sessions and picked it up {a.selections} times.
                  {a.question ? (
                    <>
                      {" "}
                      <span className="confession-detail">
                        ({a.question.slice(0, 72)}
                        {a.question.length > 72 ? "…" : ""})
                      </span>
                    </>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
          <p className="confession-cannot" data-testid="confession-cannot-distinguish">
            {CANNOT_DISTINGUISH}
          </p>
        </section>

        <section className="confession-claims" data-testid="confession-claims-not">
          <h3>claims_not</h3>
          <ul>
            {claims.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </section>
      </div>
    </aside>
  );
}

export { ConfessionPanel as default };
