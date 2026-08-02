/**
 * C2 — Seven stances as primary nav.
 * Rank once; switch lens instantly (pure client functions). Wonder rank-gap pulse when novelty disagrees with ValueProfile.
 */

import { useMemo } from "react";
import type { Ranked } from "../../types";
import {
  STANCE_META,
  applyLens,
  type LensResult,
  type StanceId,
} from "./lenses";

export type StanceNavProps = {
  results: Ranked[];
  activeStance: StanceId;
  onStance: (id: StanceId) => void;
};

export function StanceNav({ results, activeStance, onStance }: StanceNavProps) {
  const lens: LensResult = useMemo(
    () => applyLens(activeStance, results),
    [activeStance, results],
  );

  const wonderPreview = useMemo(
    () => (results.length ? applyLens("wonder", results) : null),
    [results],
  );
  const wonderDisagrees = wonderPreview?.disagreesWithCuriosity ?? 0;

  return (
    <nav
      className="stance-nav"
      aria-label="Stance lenses"
      data-testid="stance-nav"
    >
      <div className="stance-nav-head">
        <p className="stance-nav-title">Lenses</p>
        <p className="stance-nav-hint">
          Rank once — switch instantly. Each lens is a pure view over the same
          set; nothing is re-fetched.
        </p>
      </div>
      <ul className="stance-nav-list" role="tablist">
        {STANCE_META.map((s) => {
          const selected = activeStance === s.id;
          const showGapPulse =
            s.id === "wonder" && wonderDisagrees > 0 && !selected;
          return (
            <li key={s.id}>
              <button
                type="button"
                role="tab"
                aria-selected={selected}
                className={
                  "stance-tab" +
                  (selected ? " is-active" : "") +
                  (showGapPulse ? " has-rank-gap" : "")
                }
                data-testid={`stance-tab-${s.id}`}
                data-stance={s.id}
                onClick={() => onStance(s.id)}
                title={s.asks}
              >
                <span className="stance-tab-label">{s.label}</span>
                {s.id === "wonder" && wonderDisagrees > 0 && (
                  <span
                    className="stance-rank-gap-badge"
                    data-testid="wonder-rank-gap-badge"
                    aria-label={`${wonderDisagrees} items disagree with ValueProfile order`}
                  >
                    {wonderDisagrees} gap
                  </span>
                )}
              </button>
            </li>
          );
        })}
      </ul>
      <p className="stance-asks" data-testid="stance-asks">
        {STANCE_META.find((m) => m.id === activeStance)?.asks}
        {activeStance === "wonder" && lens.disagreesWithCuriosity > 0 && (
          <span className="stance-gap-note">
            {" "}
            — {lens.disagreesWithCuriosity} item
            {lens.disagreesWithCuriosity === 1 ? "" : "s"} where wonder
            disagrees with the ValueProfile.
          </span>
        )}
      </p>
    </nav>
  );
}

export { StanceNav as default };
