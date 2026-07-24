import { useEffect, useMemo, useState } from "react";

type ScoreAxes = {
  impact: number;
  neglectedness: number;
  tractability: number;
  surprise: number;
  answerability: number;
  risk: number;
  cost_proxy: number;
};

type LitHit = {
  title: string;
  year?: number | null;
  cited_by_count?: number | null;
  url?: string | null;
};

type Ranked = {
  rank: number;
  curiosity_score: number;
  confidence: number;
  score_low?: number | null;
  score_high?: number | null;
  flags: string[];
  investigation_brief: string;
  scores: ScoreAxes;
  gap: {
    status: string;
    confidence: number;
    notes: string;
    top_overlap?: number;
    related_works?: LitHit[];
  };
  question: {
    id?: string;
    question: string;
    why_it_matters: string;
    operationalization: string;
    tags: string[];
    domain: string;
  };
};

type FeedbackEvent = {
  event_type: string;
  profile_name: string;
  question_id: string;
  question_text: string;
  rank: number;
  curiosity_score: number;
  score_axes: Partial<ScoreAxes>;
  preferred_over_ids?: string[];
  labels?: { position?: string };
};

type ProfileMeta = {
  name: string;
  description: string;
};

type MixBlend = {
  framing?: string;
  inject_fragment?: string;
  percents?: Record<string, number>;
  honesty?: string;
  disclaimer?: string;
};

const DOMAINS = [
  "ai",
  "biology",
  "medicine",
  "climate",
  "energy",
  "materials",
  "physics",
  "social",
  "general",
];

const AXIS: { key: keyof ScoreAxes; label: string }[] = [
  { key: "impact", label: "Impact" },
  { key: "neglectedness", label: "Neglected" },
  { key: "tractability", label: "Tractable" },
  { key: "surprise", label: "Surprise" },
  { key: "answerability", label: "Answerable" },
];

const FALLBACK_PROFILES: ProfileMeta[] = [
  { name: "humanity_default", description: "Default multi-stakeholder weights" },
  { name: "funder_10y", description: "Tractable unknowns within ~10 years" },
  { name: "alignment_lab", description: "Neglected alignment / control unknowns" },
  { name: "climate_adaptation", description: "Climate adaptation / resilience" },
  { name: "basic_science", description: "Surprising fundamental unknowns" },
  { name: "near_term_ops", description: "Low-cost near-term operational unknowns" },
];

const MIX_SLIDERS: { id: string; label: string }[] = [
  { id: "curiosity", label: "Curiosity" },
  { id: "confusion", label: "Confusion" },
  { id: "awe", label: "Awe" },
  { id: "interest", label: "Interest" },
];

export default function App() {
  const [domain, setDomain] = useState("ai");
  const [topic, setTopic] = useState("");
  const [profileName, setProfileName] = useState("humanity_default");
  const [profiles, setProfiles] = useState<ProfileMeta[]>(FALLBACK_PROFILES);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<Ranked[]>([]);
  const [activeProfile, setActiveProfile] = useState<string | null>(null);
  const [profileDescription, setProfileDescription] = useState<string | null>(
    null,
  );
  const [mixWeights, setMixWeights] = useState<Record<string, number>>({
    curiosity: 40,
    confusion: 25,
    awe: 20,
    interest: 15,
  });
  const [mixBlend, setMixBlend] = useState<MixBlend | null>(null);
  const [mixOpen, setMixOpen] = useState(false);
  const [mixBusy, setMixBusy] = useState(false);
  const [mixWarnings, setMixWarnings] = useState<string[]>([]);
  const [feedback, setFeedback] = useState<FeedbackEvent[]>([]);
  const [feedbackNote, setFeedbackNote] = useState<string | null>(null);
  const [compareB, setCompareB] = useState("alignment_lab");
  const [compareOpen, setCompareOpen] = useState(false);
  const [compareBusy, setCompareBusy] = useState(false);
  const [compareErr, setCompareErr] = useState<string | null>(null);
  const [compareData, setCompareData] = useState<{
    ranks_a?: { rank: number; question: string; curiosity_score: number }[];
    ranks_b?: { rank: number; question: string; curiosity_score: number }[];
    agreement?: { kendall_tau?: number | null; top_k_jaccard?: number | null };
    honesty?: string;
    profile_a?: { name?: string };
    profile_b?: { name?: string };
  } | null>(null);

  const subtitle = useMemo(
    () =>
      "Current AI answers questions. This layer asks what humanity should investigate next — and ranks unknowns by expected impact.",
    [],
  );

  const activeProfileMeta = useMemo(
    () => profiles.find((p) => p.name === (activeProfile ?? profileName)),
    [profiles, activeProfile, profileName],
  );

  useEffect(() => {
    fetch("/v1/profiles")
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.presets?.length) {
          setProfiles(
            data.presets.map((p: ProfileMeta) => ({
              name: p.name,
              description: p.description,
            })),
          );
        }
      })
      .catch(() => undefined);
  }, []);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/v1/curiosity/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          domain,
          topic,
          n_return: 8,
          n_candidates: 16,
          use_llm: false,
          use_literature: true,
          profile_name: profileName,
          literature_workers: 4,
        }),
      });
      if (!res.ok) {
        throw new Error(`API ${res.status}`);
      }
      const data = await res.json();
      setResults(data.questions ?? []);
      setActiveProfile(data.value_profile?.name ?? profileName);
      setProfileDescription(data.value_profile?.description ?? null);
    } catch (e) {
      setError(
        e instanceof Error
          ? `${e.message}. Is the API running on :8000?`
          : "Request failed",
      );
    } finally {
      setLoading(false);
    }
  }

  async function spark() {
    setLoading(true);
    setError(null);
    try {
      const qs = new URLSearchParams({
        domain,
        n: "5",
        fast: "true",
        profile_name: profileName,
      });
      if (topic.trim()) qs.set("topic", topic.trim());
      const res = await fetch(`/v1/curiosity/provoke?${qs.toString()}`);
      if (!res.ok) throw new Error(`API ${res.status}`);
      const data = await res.json();
      const questions = (data.questions ?? []) as Ranked[];
      setResults(questions);
      setActiveProfile(data.value_profile?.name ?? profileName);
      setProfileDescription(data.value_profile?.description ?? null);
      if (mixBlend?.inject_fragment && data.inject) {
        // Framing is optional UX — never claimed as felt emotion.
        void navigator.clipboard?.writeText?.(
          `${mixBlend.inject_fragment}\n\n${data.inject}`,
        );
      }
    } catch (e) {
      setError(
        e instanceof Error
          ? `${e.message}. Is the API running on :8000?`
          : "Spark failed",
      );
    } finally {
      setLoading(false);
    }
  }

  async function buildMix() {
    setMixBusy(true);
    setError(null);
    try {
      const weights: Record<string, number> = {};
      for (const s of MIX_SLIDERS) {
        const v = mixWeights[s.id] ?? 0;
        if (v > 0) weights[s.id] = v;
      }
      const res = await fetch("/v1/emotions/mix", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ weights }),
      });
      if (!res.ok) throw new Error(`Mix API ${res.status}`);
      const data = await res.json();
      setMixBlend({
        framing: data.framing,
        inject_fragment: data.inject_fragment,
        percents: data.percents,
        honesty: data.disclaimer || data.honesty,
        disclaimer: data.disclaimer,
      });
      setMixWarnings(Array.isArray(data.warnings) ? data.warnings : []);
      setMixOpen(true);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Emotion mix failed",
      );
    } finally {
      setMixBusy(false);
    }
  }

  function recordFeedback(
    r: Ranked,
    eventType: "prefer" | "reject" | "already_answered" | "tie",
  ) {
    const qid =
      r.question.id ||
      `rank-${r.rank}-${r.question.question.slice(0, 24).replace(/\s+/g, "_")}`;
    const others = results
      .filter((x) => x.rank !== r.rank)
      .slice(0, eventType === "tie" ? 1 : 3)
      .map(
        (x) =>
          x.question.id ||
          `rank-${x.rank}-${x.question.question.slice(0, 24).replace(/\s+/g, "_")}`,
      );
    const ev: FeedbackEvent = {
      event_type: eventType,
      profile_name: activeProfile ?? profileName,
      question_id: qid,
      question_text: r.question.question,
      rank: r.rank,
      curiosity_score: r.curiosity_score,
      score_axes: {
        impact: r.scores.impact,
        neglectedness: r.scores.neglectedness,
        tractability: r.scores.tractability,
        surprise: r.scores.surprise,
      },
      preferred_over_ids:
        eventType === "prefer" || eventType === "tie" ? others : [],
      labels: {
        position: String(r.rank),
        ...(eventType === "tie" ? { relation: "tie" } : {}),
      },
    };
    setFeedback((prev) => [...prev, ev]);
    setFeedbackNote(`${eventType} recorded for #${r.rank} (session only)`);
  }

  async function runCompare() {
    setCompareBusy(true);
    setCompareErr(null);
    try {
      const res = await fetch("/v1/profiles/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          domain,
          topic,
          profile_a: profileName,
          profile_b: compareB,
          n: 6,
        }),
      });
      if (!res.ok) throw new Error(`API ${res.status}`);
      setCompareData(await res.json());
      setCompareOpen(true);
    } catch (e) {
      setCompareErr(e instanceof Error ? e.message : "Compare failed");
      setCompareData(null);
    } finally {
      setCompareBusy(false);
    }
  }

  async function summarizeFeedback() {
    if (feedback.length < 1) {
      setFeedbackNote("No feedback yet — use Prefer / Reject on cards.");
      return;
    }
    try {
      const res = await fetch("/v1/preferences/summarize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          events: feedback,
          profile_name: activeProfile ?? profileName,
          top_k: 8,
        }),
      });
      if (!res.ok) throw new Error(`API ${res.status}`);
      const data = await res.json();
      const top = (data.top_question_ids || [])
        .slice(0, 3)
        .map((t: { question_id: string }) => t.question_id)
        .join(", ");
      setFeedbackNote(
        `Summary n=${data.n_events} pairwise=${data.n_pairwise}` +
          (top ? ` top=[${top}]` : "") +
          " — profile-scoped, not calibrated.",
      );
    } catch (e) {
      setFeedbackNote(e instanceof Error ? e.message : "Summarize failed");
    }
  }

  return (
    <main className="shell">
      <h1 className="brand">Artificial Curiosity</h1>
      <p className="lede">{subtitle}</p>

      <div className="controls">
        <label>
          Domain
          <select value={domain} onChange={(e) => setDomain(e.target.value)}>
            {DOMAINS.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </label>
        <label>
          ValueProfile
          <select
            value={profileName}
            onChange={(e) => setProfileName(e.target.value)}
          >
            {profiles.map((p) => (
              <option key={p.name} value={p.name}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Topic focus
          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="optional — e.g. aging biomarkers"
          />
        </label>
        <div className="btn-row">
          <button type="button" onClick={run} disabled={loading}>
            {loading ? "Mapping unknowns…" : "Ask what to investigate"}
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={spark}
            disabled={loading}
          >
            Fast spark
          </button>
        </div>
      </div>

      {(activeProfileMeta?.description || profileDescription) && (
        <p className="profile-desc">
          <strong>Active profile.</strong>{" "}
          {profileDescription ?? activeProfileMeta?.description}
        </p>
      )}

      <section className="compare-panel" aria-label="Profile compare">
        <div className="compare-controls">
          <label>
            Compare vs
            <select
              value={compareB}
              onChange={(e) => setCompareB(e.target.value)}
            >
              {profiles
                .filter((p) => p.name !== profileName)
                .map((p) => (
                  <option key={p.name} value={p.name}>
                    {p.name}
                  </option>
                ))}
            </select>
          </label>
          <button
            type="button"
            className="btn-secondary"
            onClick={runCompare}
            disabled={compareBusy || compareB === profileName}
          >
            {compareBusy ? "Comparing…" : "Side-by-side ranks"}
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
            </p>
          </div>
        )}
      </section>

      <section className="mix-panel" aria-label="Investigation framing mix">
        <button
          type="button"
          className="mix-toggle"
          onClick={() => setMixOpen((o) => !o)}
          aria-expanded={mixOpen}
        >
          {mixOpen ? "Hide" : "Show"} investigation framing mix
          <span className="mix-hint">UX annotation only — does not feel</span>
        </button>
        {mixOpen && (
          <div className="mix-body">
            <p className="mix-honesty">
              Percentages are framing weights for investigation tone — not EES
              scores, not felt emotion, and not a clinical mood measure.
            </p>
            <div className="mix-sliders">
              {MIX_SLIDERS.map((s) => (
                <label key={s.id} className="mix-slider">
                  <span>
                    {s.label}{" "}
                    <em>{Math.round(mixWeights[s.id] ?? 0)}</em>
                  </span>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={mixWeights[s.id] ?? 0}
                    onChange={(e) =>
                      setMixWeights((w) => ({
                        ...w,
                        [s.id]: Number(e.target.value),
                      }))
                    }
                  />
                </label>
              ))}
            </div>
            <button type="button" onClick={buildMix} disabled={mixBusy}>
              {mixBusy ? "Mixing…" : "Build framing mix"}
            </button>
            {mixBlend && (
              <div className="mix-result">
                {mixWarnings.length > 0 && (
                  <ul className="mix-warnings">
                    {mixWarnings.map((w) => (
                      <li key={w.slice(0, 40)}>{w}</li>
                    ))}
                  </ul>
                )}
                {mixBlend.framing && (
                  <p>
                    <strong>Framing.</strong> {mixBlend.framing}
                  </p>
                )}
                {mixBlend.inject_fragment && (
                  <pre className="mix-inject">{mixBlend.inject_fragment}</pre>
                )}
                <p className="mix-disclaimer">
                  {mixBlend.honesty ||
                    mixBlend.disclaimer ||
                    "Annotation only — this system does not feel."}
                </p>
              </div>
            )}
          </div>
        )}
      </section>

      {feedbackNote && <p className="feedback-note">{feedbackNote}</p>}
      {feedback.length > 0 && (
        <div className="feedback-bar">
          <span>{feedback.length} feedback event(s) this session</span>
          <button type="button" className="btn-secondary" onClick={summarizeFeedback}>
            Summarize feedback
          </button>
        </div>
      )}

      {error && <div className="error">{error}</div>}

      {results.length > 0 && (
        <>
          <div className="meta-row">
            <span>{results.length} ranked unknowns</span>
            <span>domain={domain}</span>
            <span>profile={activeProfile ?? profileName}</span>
            <span>literature-grounded gap check</span>
          </div>
          <p className="profile-note">
            Rankings use explicit ValueProfile weights — decision aids, not oracles.
            Curiosity scores and [low–high] bands are evidence-strength envelopes,
            not calibrated probabilities. Investigation briefs are primary; axis
            bars are secondary context.
          </p>
          <section className="list">
            {results.map((r) => {
              const works = r.gap?.related_works?.slice(0, 3) ?? [];
              const band =
                r.score_low != null && r.score_high != null
                  ? `[${r.score_low.toFixed(2)}–${r.score_high.toFixed(2)}]`
                  : null;
              return (
                <article className="card" key={`${r.rank}-${r.question.question}`}>
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
                      <span className="chip">
                        cost {r.scores.cost_proxy.toFixed(2)}
                      </span>
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
                      <button
                        type="button"
                        className="btn-feedback"
                        onClick={() => recordFeedback(r, "prefer")}
                      >
                        Prefer
                      </button>
                      <button
                        type="button"
                        className="btn-feedback"
                        onClick={() => recordFeedback(r, "tie")}
                      >
                        Tie
                      </button>
                      <button
                        type="button"
                        className="btn-feedback"
                        onClick={() => recordFeedback(r, "reject")}
                      >
                        Reject
                      </button>
                      <button
                        type="button"
                        className="btn-feedback"
                        onClick={() => recordFeedback(r, "already_answered")}
                      >
                        Already answered
                      </button>
                    </div>
                    <p className="why">
                      <strong>Why it matters.</strong> {r.question.why_it_matters}
                    </p>
                    <p className="ops">
                      <strong>Operationalization.</strong>{" "}
                      {r.question.operationalization}
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
                          <span>{a.label}</span>
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
            })}
          </section>
        </>
      )}

      <p className="footer-note">
        Scores estimate expected value of investigation (impact × neglectedness ×
        tractability × surprise), gated by answerability, risk, and literature gap
        status. Profile name and [low–high] bands are always shown — decision aids,
        not oracles. Neglectedness/cost are heuristic proxies, not funding databases.
        Emotion mixes are optional framing weights only.
      </p>
    </main>
  );
}
