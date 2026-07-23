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
    question: string;
    why_it_matters: string;
    operationalization: string;
    tags: string[];
    domain: string;
  };
};

type ProfileMeta = {
  name: string;
  description: string;
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

export default function App() {
  const [domain, setDomain] = useState("ai");
  const [topic, setTopic] = useState("");
  const [profileName, setProfileName] = useState("humanity_default");
  const [profiles, setProfiles] = useState<ProfileMeta[]>(FALLBACK_PROFILES);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<Ranked[]>([]);
  const [activeProfile, setActiveProfile] = useState<string | null>(null);

  const subtitle = useMemo(
    () =>
      "Current AI answers questions. This layer asks what humanity should investigate next — and ranks unknowns by expected impact.",
    [],
  );

  useEffect(() => {
    // Fire-and-forget profile list; keep fallbacks if API is down.
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
        }),
      });
      if (!res.ok) {
        throw new Error(`API ${res.status}`);
      }
      const data = await res.json();
      setResults(data.questions ?? []);
      setActiveProfile(data.value_profile?.name ?? profileName);
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
        <button type="button" onClick={run} disabled={loading}>
          {loading ? "Mapping unknowns…" : "Ask what to investigate"}
        </button>
      </div>

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
            Bands are evidence-strength envelopes.
          </p>
          <section className="list">
            {results.map((r) => {
              const works = r.gap.related_works?.slice(0, 3) ?? [];
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
                      <span className={`chip gap-${r.gap.status}`}>
                        gap:{r.gap.status}
                      </span>
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
        not oracles.
      </p>
    </main>
  );
}
