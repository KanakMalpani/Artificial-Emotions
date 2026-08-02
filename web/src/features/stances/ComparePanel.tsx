import type { CompareData, ProfileMeta } from "../../types";

export type ComparePanelProps = {
  profileName: string;
  profiles: ProfileMeta[];
  compareB: string;
  vetoProfile: string;
  compareBusy: boolean;
  compareErr: string | null;
  compareOpen: boolean;
  compareData: CompareData | null;
  onCompareB: (v: string) => void;
  onVetoProfile: (v: string) => void;
  onCompare: () => void;
  onConstitutionCompare: () => void;
};

/** Mount: profile side-by-side / constitution+veto compare (stance lens precursor). */
export function ComparePanel(props: ComparePanelProps) {
  const {
    profileName,
    profiles,
    compareB,
    vetoProfile,
    compareBusy,
    compareErr,
    compareOpen,
    compareData,
    onCompareB,
    onVetoProfile,
    onCompare,
    onConstitutionCompare,
  } = props;

  return (
    <section className="compare-panel" aria-label="Profile compare">
      <div className="compare-controls">
        <label>
          Compare vs
          <select value={compareB} onChange={(e) => onCompareB(e.target.value)}>
            {profiles
              .filter((p) => p.name !== profileName)
              .map((p) => (
                <option key={p.name} value={p.name}>
                  {p.name}
                </option>
              ))}
          </select>
        </label>
        <label>
          Safety veto
          <select
            value={vetoProfile}
            onChange={(e) => onVetoProfile(e.target.value)}
          >
            {profiles.map((p) => (
              <option key={p.name} value={p.name}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="btn-secondary"
          onClick={onCompare}
          disabled={compareBusy || compareB === profileName}
        >
          {compareBusy ? "Comparing…" : "Side-by-side ranks"}
        </button>
        <button
          type="button"
          className="btn-secondary"
          onClick={onConstitutionCompare}
          disabled={compareBusy}
        >
          Compare + veto
        </button>
      </div>
      {compareErr && <p className="error">{compareErr}</p>}
      {compareOpen && compareData && (
        <div className="compare-grid">
          <div className="compare-col">
            <h3>{compareData.profile_a?.name ?? profileName}</h3>
            <ol>
              {(compareData.ranks_a || []).map((r) => (
                <li key={`a-${r.rank}`}>
                  <span className="compare-rank">#{r.rank}</span>
                  <span className="compare-q">{r.question}</span>
                  <span className="compare-score">
                    {r.curiosity_score.toFixed(2)}
                  </span>
                </li>
              ))}
            </ol>
          </div>
          <div className="compare-col">
            <h3>{compareData.profile_b?.name ?? compareB}</h3>
            <ol>
              {(compareData.ranks_b || []).map((r) => (
                <li key={`b-${r.rank}`}>
                  <span className="compare-rank">#{r.rank}</span>
                  <span className="compare-q">{r.question}</span>
                  <span className="compare-score">
                    {r.curiosity_score.toFixed(2)}
                  </span>
                </li>
              ))}
            </ol>
          </div>
          <p className="compare-meta">
            τ=
            {compareData.agreement?.kendall_tau == null
              ? "n/a"
              : Number(compareData.agreement.kendall_tau).toFixed(3)}
            {" · "}
            top-k Jaccard=
            {compareData.agreement?.top_k_jaccard == null
              ? "n/a"
              : Number(compareData.agreement.top_k_jaccard).toFixed(3)}
            {" — "}
            offline heuristic; no silent merge.
            {compareData.veto_applied
              ? ` Veto kept=${compareData.veto_applied.n_kept} flagged=${compareData.veto_applied.n_flagged} (max_risk=${compareData.veto_applied.max_risk}).`
              : ""}
          </p>
          {(compareData.veto_applied?.flagged?.length ?? 0) > 0 && (
            <p className="compare-meta">
              Flagged over risk ceiling:{" "}
              {compareData.veto_applied!.flagged!
                .slice(0, 3)
                .map((f) => `#${f.rank}`)
                .join(", ")}
              {" — stakeholders can disagree; not a consensus score."}
            </p>
          )}
        </div>
      )}
    </section>
  );
}

export { ComparePanel as default };
