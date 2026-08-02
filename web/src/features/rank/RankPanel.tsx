import {
  qidFor,
  type OutcomeDraft,
  type Ranked,
} from "../../types";
import { RankCard } from "./RankCard";

export type RankPanelProps = {
  domain: string;
  profileLabel: string;
  resultMode: "run" | "spark" | null;
  results: Ranked[];
  preferredIds: Set<string>;
  outcomeDraft: Record<string, OutcomeDraft>;
  feedbackCount: number;
  feedbackNote: string | null;
  critiqueNote: string | null;
  soundnessNote: string | null;
  error: string | null;
  onRecordFeedback: (
    r: Ranked,
    eventType: "prefer" | "reject" | "already_answered" | "tie",
  ) => void;
  onRecordOutcome: (r: Ranked) => void;
  onOutcomeDraft: (qid: string, draft: OutcomeDraft) => void;
  onCritique: (r: Ranked) => void;
  onSoundness: (r: Ranked) => void;
  onSummarizeFeedback: () => void;
  onSuggestPair: () => void;
};

/** Mount: feedback bar + ranked result cards. */
export function RankPanel(props: RankPanelProps) {
  const {
    domain,
    profileLabel,
    resultMode,
    results,
    preferredIds,
    outcomeDraft,
    feedbackCount,
    feedbackNote,
    critiqueNote,
    soundnessNote,
    error,
    onRecordFeedback,
    onRecordOutcome,
    onOutcomeDraft,
    onCritique,
    onSoundness,
    onSummarizeFeedback,
    onSuggestPair,
  } = props;

  return (
    <>
      {feedbackNote && <p className="feedback-note">{feedbackNote}</p>}
      {critiqueNote && <p className="feedback-note">{critiqueNote}</p>}
      {soundnessNote && <p className="feedback-note">{soundnessNote}</p>}
      {feedbackCount > 0 && (
        <div className="feedback-bar">
          <span>{feedbackCount} feedback event(s) this session</span>
          <button
            type="button"
            className="btn-secondary"
            onClick={onSummarizeFeedback}
          >
            Summarize feedback
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={onSuggestPair}
          >
            Suggest next duel
          </button>
        </div>
      )}
      {results.length >= 2 && feedbackCount === 0 && (
        <div className="feedback-bar">
          <button
            type="button"
            className="btn-secondary"
            onClick={onSuggestPair}
          >
            Suggest next duel
          </button>
        </div>
      )}

      {error && <div className="error">{error}</div>}

      {results.length > 0 && (
        <>
          <div className="meta-row">
            <span>{results.length} ranked unknowns</span>
            <span>domain={domain}</span>
            <span>profile={profileLabel}</span>
            <span>
              {resultMode === "spark"
                ? "fast spark (offline seeds)"
                : "literature-grounded gap check"}
            </span>
          </div>
          <p className="profile-note">
            Rankings use explicit ValueProfile weights — decision aids, not
            oracles. Curiosity scores and [low–high] bands are evidence-strength
            envelopes, not calibrated probabilities. Investigation briefs are
            primary; axis bars are secondary context.
          </p>
          <section className="list">
            {results.map((r) => {
              const id = qidFor(r);
              return (
                <RankCard
                  key={`${r.rank}-${r.question.question}`}
                  ranked={r}
                  preferred={preferredIds.has(id)}
                  outcomeDraft={outcomeDraft[id]}
                  onPrefer={() => onRecordFeedback(r, "prefer")}
                  onTie={() => onRecordFeedback(r, "tie")}
                  onReject={() => onRecordFeedback(r, "reject")}
                  onAlreadyAnswered={() =>
                    onRecordFeedback(r, "already_answered")
                  }
                  onCritique={() => onCritique(r)}
                  onSoundness={() => onSoundness(r)}
                  onOutcomeDraft={(draft) => onOutcomeDraft(id, draft)}
                  onLogOutcome={() => onRecordOutcome(r)}
                />
              );
            })}
          </section>
        </>
      )}
    </>
  );
}

export { RankPanel as default };
