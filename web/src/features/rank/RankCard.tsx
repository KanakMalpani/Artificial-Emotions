import {
  AXIS,
  OUTCOME_LABELS,
  type OutcomeDraft,
  type Ranked,
} from "../../types";

export type RankCardProps = {
  ranked: Ranked;
  preferred: boolean;
  outcomeDraft: OutcomeDraft | undefined;
  onPrefer: () => void;
  onTie: () => void;
  onReject: () => void;
  onAlreadyAnswered: () => void;
  onCritique: () => void;
  onSoundness: () => void;
  onOutcomeDraft: (draft: OutcomeDraft) => void;
  onLogOutcome: () => void;
};

export function RankCard(props: RankCardProps) {
  const {
    ranked: r,
    preferred,
    outcomeDraft,
    onPrefer,
    onTie,
    onReject,
    onAlreadyAnswered,
    onCritique,
    onSoundness,
    onOutcomeDraft,
    onLogOutcome,
  } = props;

  const works = r.gap?.related_works?.slice(0, 3) ?? [];
  const band =
    r.score_low != null && r.score_high != null
      ? `[${r.score_low.toFixed(2)}–${r.score_high.toFixed(2)}]`
      : null;
  const draft = outcomeDraft || {
    result: "partial_progress",
    months: "",
    note: "",
  };

  return (
    <article className="card">
      <div className="rank">#{r.rank}</div>
      <div>
        <h2 className="q-title">{r.question.question}</h2>
        <div className="scores">
          <span className="chip">
            curiosity {r.curiosity_score.toFixed(3)}
            {band ? ` ${band}` : ""}
          </span>
          <span className="chip">conf {r.confidence.toFixed(2)}</span>
          <span className={`chip gap-${r.gap?.status ?? "unknown"}`}>
            gap:{r.gap?.status ?? "n/a"}
          </span>
          <span className="chip">cost {r.scores.cost_proxy.toFixed(2)}</span>
          {r.flags?.slice(0, 4).map((f) => (
            <span className="chip flag" key={f}>
              {f}
            </span>
          ))}
          {r.question.tags?.slice(0, 3).map((t) => (
            <span className="chip" key={t}>
              {t}
            </span>
          ))}
        </div>
        {r.investigation_brief && (
          <div className="brief">
            <strong>Investigation brief.</strong> {r.investigation_brief}
          </div>
        )}
        <div className="feedback-actions">
          <button type="button" className="btn-feedback" onClick={onPrefer}>
            Prefer
          </button>
          <button type="button" className="btn-feedback" onClick={onTie}>
            Tie
          </button>
          <button type="button" className="btn-feedback" onClick={onReject}>
            Reject
          </button>
          <button
            type="button"
            className="btn-feedback"
            onClick={onAlreadyAnswered}
          >
            Already answered
          </button>
          <button type="button" className="btn-feedback" onClick={onCritique}>
            Critique form
          </button>
          <button type="button" className="btn-feedback" onClick={onSoundness}>
            Soundness
          </button>
        </div>
        {preferred && (
          <div className="outcome-picker">
            <label>
              Outcome
              <select
                value={draft.result}
                onChange={(e) =>
                  onOutcomeDraft({
                    ...draft,
                    result: e.target.value,
                  })
                }
              >
                {OUTCOME_LABELS.map((o) => (
                  <option key={o} value={o}>
                    {o}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Months
              <input
                type="number"
                min={0}
                placeholder="opt"
                value={draft.months}
                onChange={(e) =>
                  onOutcomeDraft({
                    ...draft,
                    months: e.target.value,
                  })
                }
              />
            </label>
            <button
              type="button"
              className="btn-feedback"
              onClick={onLogOutcome}
            >
              Log outcome
            </button>
            <span className="outcome-hint">
              Sparse flywheel — not auto-retrain
            </span>
          </div>
        )}
        <p className="why">
          <strong>Why it matters.</strong> {r.question.why_it_matters}
        </p>
        <p className="ops">
          <strong>Operationalization.</strong> {r.question.operationalization}
        </p>
        {works.length > 0 && (
          <div className="lit">
            <strong>Neighborhood literature</strong>
            <span className="lit-note">
              {" "}
              (related ≠ answered; overlap=
              {(r.gap.top_overlap ?? 0).toFixed(2)})
            </span>
            <ul>
              {works.map((w) => (
                <li key={w.title}>
                  {w.url ? (
                    <a href={w.url} target="_blank" rel="noreferrer">
                      {w.title}
                    </a>
                  ) : (
                    w.title
                  )}
                  {w.year != null ? ` (${w.year})` : ""}
                </li>
              ))}
            </ul>
          </div>
        )}
        <div className="bars">
          {AXIS.map((a) => (
            <div className="bar-row" key={a.key}>
              <span title={a.tip}>{a.label}</span>
              <div className="bar-track">
                <div
                  className="bar-fill"
                  style={{ width: `${r.scores[a.key] * 100}%` }}
                />
              </div>
              <span>{r.scores[a.key].toFixed(2)}</span>
            </div>
          ))}
        </div>
      </div>
    </article>
  );
}
