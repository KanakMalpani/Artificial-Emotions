import { useMemo, useState } from "react";

type ScoreAxes = {
  impact: number;
  neglectedness: number;
  tractability: number;
  surprise: number;
  answerability: number;
  risk: number;
  cost_proxy: number;
};

type Ranked = {
  rank: number;
  curiosity_score: number;
  confidence: number;
  flags: string[];
  investigation_brief: string;
  scores: ScoreAxes;
  gap: { status: string; confidence: number; notes: string };
  question: {
    question: string;
    why_it_matters: string;
    operationalization: string;
    tags: string[];
    domain: string;
  };
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

export default function App() {
  const [domain, setDomain] = useState("ai");
  const [topic, setTopic] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<Ranked[]>([]);

  const subtitle = useMemo(
    () =>
      "Current AI answers questions. This layer asks what humanity should investigate next — and ranks unknowns by expected impact.",
    [],
  );

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
        }),
      });
      if (!res.ok) {
        throw new Error(`API ${res.status}`);
      }
      const data = await res.json();
      setResults(data.questions ?? []);
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
            <span>literature-grounded gap check</span>
          </div>
          <section className="list">
            {results.map((r) => (
              <article className="card" key={`${r.rank}-${r.question.question}`}>
                <div className="rank">#{r.rank}</div>
                <div>
                  <h2 className="q-title">{r.question.question}</h2>
                  <div className="scores">
                    <span className="chip">
                      curiosity {r.curiosity_score.toFixed(3)}
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
                  <p className="why">
                    <strong>Why it matters.</strong> {r.question.why_it_matters}
                  </p>
                  <p className="ops">
                    <strong>Operationalization.</strong>{" "}
                    {r.question.operationalization}
                  </p>
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
            ))}
          </section>
        </>
      )}

      <p className="footer-note">
        Scores estimate expected value of investigation (impact × neglectedness ×
        tractability × surprise), gated by answerability, risk, and literature gap
        status. They are decision aids — not oracles.
      </p>
    </main>
  );
}
