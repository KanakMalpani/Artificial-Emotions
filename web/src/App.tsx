import { useMemo, useState } from "react";
import { AffectReadout } from "./affect";
import { ExplorePanel, useProfilesQuery } from "./features/explore";
import { ImaginationCanvas } from "./features/imagine";
import { ConfessionPanel, TrajectoryMap } from "./features/memory";
import { RankPanel } from "./features/rank";
import {
  ComparePanel,
  StanceLensList,
  StanceNav,
  type StanceId,
} from "./features/stances";
import {
  FALLBACK_PROFILES,
  MIX_SLIDERS,
  qidFor,
  type CompareData,
  type FeedbackEvent,
  type MixBlend,
  type OutcomeDraft,
  type Ranked,
} from "./types";

/**
 * App shell: C1 affect + Wave 4 presentation (C2–C5).
 * AffectProvider (main.tsx) writes --ae-* CSS vars from PAD state.
 */
export default function App() {

  const profilesQuery = useProfilesQuery();
  const profiles = profilesQuery.data ?? FALLBACK_PROFILES;

  const [domain, setDomain] = useState("ai");
  const [topic, setTopic] = useState("");
  const [profileName, setProfileName] = useState("humanity_default");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<Ranked[]>([]);
  const [resultMode, setResultMode] = useState<"run" | "spark" | null>(null);
  const [activeStance, setActiveStance] = useState<StanceId>("curiosity");
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
  const [critiqueNote, setCritiqueNote] = useState<string | null>(null);
  const [soundnessNote, setSoundnessNote] = useState<string | null>(null);
  const [preferredIds, setPreferredIds] = useState<Set<string>>(new Set());
  const [outcomeDraft, setOutcomeDraft] = useState<
    Record<string, OutcomeDraft>
  >({});
  const [compareB, setCompareB] = useState("alignment_lab");
  const [vetoProfile, setVetoProfile] = useState("public_demo_strict_risk");
  const [compareOpen, setCompareOpen] = useState(false);
  const [compareBusy, setCompareBusy] = useState(false);
  const [compareErr, setCompareErr] = useState<string | null>(null);
  const [compareData, setCompareData] = useState<CompareData | null>(null);

  const subtitle = useMemo(
    () =>
      "Current AI answers questions. This curiosity layer ranks what to investigate next — decision aids, not oracles.",
    [],
  );

  const activeProfileMeta = useMemo(
    () => profiles.find((p) => p.name === (activeProfile ?? profileName)),
    [profiles, activeProfile, profileName],
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
          profile_name: profileName,
          literature_workers: 4,
        }),
      });
      if (!res.ok) throw new Error(`API ${res.status}`);
      const data = await res.json();
      setResults(data.questions ?? []);
      setResultMode("run");
      setActiveStance("curiosity");
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
      setResults((data.questions ?? []) as Ranked[]);
      setResultMode("spark");
      setActiveStance("curiosity");
      setActiveProfile(data.value_profile?.name ?? profileName);
      setProfileDescription(data.value_profile?.description ?? null);
      if (mixBlend?.inject_fragment && data.inject) {
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
      setError(e instanceof Error ? e.message : "Emotion mix failed");
    } finally {
      setMixBusy(false);
    }
  }

  function recordFeedback(
    r: Ranked,
    eventType: "prefer" | "reject" | "already_answered" | "tie",
  ) {
    const qid = qidFor(r);
    const others = results
      .filter((x) => x.rank !== r.rank)
      .slice(0, eventType === "tie" ? 1 : 3)
      .map((x) => qidFor(x));
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
    if (eventType === "prefer" || eventType === "tie") {
      setPreferredIds((prev) => new Set([...prev, qid]));
    }
    setFeedbackNote(`${eventType} recorded for #${r.rank} (session only)`);
  }

  function recordOutcome(r: Ranked) {
    const qid = qidFor(r);
    const draft = outcomeDraft[qid] || {
      result: "partial_progress",
      months: "",
      note: "",
    };
    const labels: FeedbackEvent["labels"] = {
      position: String(r.rank),
      result: draft.result,
    };
    if (draft.months.trim()) labels.months = draft.months.trim();
    const ev: FeedbackEvent = {
      event_type: "outcome",
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
      labels,
      notes: draft.note.trim() || undefined,
    };
    setFeedback((prev) => [...prev, ev]);
    setFeedbackNote(
      `outcome=${draft.result} for #${r.rank} (sparse; not a certificate)`,
    );
  }

  async function critiqueCard(r: Ranked) {
    setCritiqueNote(null);
    try {
      const res = await fetch("/v1/briefs/critique", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: r.question.question,
          operationalization: r.question.operationalization,
          brief: r.investigation_brief || "",
          why_it_matters: r.question.why_it_matters,
        }),
      });
      if (!res.ok) throw new Error(`API ${res.status}`);
      const data = await res.json();
      const codes = (data.issues || [])
        .slice(0, 3)
        .map((i: { code: string }) => i.code)
        .join(", ");
      setCritiqueNote(
        `#${r.rank}: ${data.n_issues} form issue(s)` +
          (codes ? ` [${codes}]` : " — clean") +
          " — does not re-rank.",
      );
    } catch (e) {
      setCritiqueNote(e instanceof Error ? e.message : "Critique failed");
    }
  }

  async function soundnessCard(r: Ranked) {
    setSoundnessNote(null);
    try {
      const res = await fetch("/v1/evals/soundness", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          candidates: [
            {
              question_id: qidFor(r),
              question: r.question.question,
              operationalization: r.question.operationalization,
              brief: r.investigation_brief || "",
              gap_status: r.gap?.status || "",
              axes: {
                answerability: r.scores.answerability,
                tractability: r.scores.tractability,
                risk: r.scores.risk,
              },
            },
          ],
        }),
      });
      if (!res.ok) throw new Error(`API ${res.status}`);
      const data = await res.json();
      const row = (data.results || [])[0];
      const codes = (row?.critique?.issues || [])
        .slice(0, 2)
        .map((i: { code?: string }) => i.code || "issue")
        .join(", ");
      setSoundnessNote(
        `#${r.rank}: soundness=${row?.soundness ?? "n/a"}` +
          (codes ? ` [${codes}]` : "") +
          " — triage only; does not re-rank.",
      );
    } catch (e) {
      setSoundnessNote(e instanceof Error ? e.message : "Soundness failed");
    }
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

  async function runConstitutionCompare() {
    setCompareBusy(true);
    setCompareErr(null);
    try {
      const res = await fetch("/v1/profiles/constitution-compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          domain,
          topic,
          primary_profile: profileName,
          veto_profile: vetoProfile,
          n: 6,
        }),
      });
      if (!res.ok) throw new Error(`API ${res.status}`);
      setCompareData(await res.json());
      setCompareOpen(true);
    } catch (e) {
      setCompareErr(
        e instanceof Error ? e.message : "Constitution compare failed",
      );
      setCompareData(null);
    } finally {
      setCompareBusy(false);
    }
  }

  async function suggestPair() {
    if (results.length < 2) {
      setFeedbackNote("Need ≥2 ranked results for a duel suggestion.");
      return;
    }
    try {
      const candidates = results.map((r) => ({
        question_id: qidFor(r),
        rank: r.rank,
        curiosity_score: r.curiosity_score,
        question: r.question.question,
      }));
      const res = await fetch("/v1/preferences/suggest-pair", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          candidates,
          events: feedback,
          profile_name: activeProfile ?? profileName,
        }),
      });
      if (!res.ok) throw new Error(`API ${res.status}`);
      const data = await res.json();
      const pair = data.pair;
      if (!pair) {
        setFeedbackNote(data.reason || "No pair suggested");
        return;
      }
      setFeedbackNote(
        `Next duel: #${pair.a?.rank} vs #${pair.b?.rank} — prior=${pair.prior_comparisons} (not BT overwrite)`,
      );
    } catch (e) {
      setFeedbackNote(e instanceof Error ? e.message : "Suggest-pair failed");
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
      const nOut = data.outcomes?.n_outcome ?? 0;
      const byResult = data.outcomes?.by_result || {};
      const outBits = Object.entries(byResult)
        .map(([k, v]) => `${k}:${v}`)
        .join(",");
      setFeedbackNote(
        `Summary n=${data.n_events} pairwise=${data.n_pairwise}` +
          (top ? ` top=[${top}]` : "") +
          (nOut
            ? ` outcomes=${nOut}${outBits ? ` (${outBits})` : ""}`
            : "") +
          " — n is small; not a performance certificate.",
      );
    } catch (e) {
      setFeedbackNote(e instanceof Error ? e.message : "Summarize failed");
    }
  }

  return (
    <main className="shell" data-testid="mood-shell">
      <h1 className="brand">Artificial Emotions</h1>
      <p className="lede">{subtitle}</p>

      <AffectReadout />

      <StanceNav
        results={results}
        activeStance={activeStance}
        onStance={setActiveStance}
      />

      <ExplorePanel
        domain={domain}
        topic={topic}
        profileName={profileName}
        profiles={profiles}
        loading={loading}
        profileDescription={profileDescription}
        activeProfileDescription={activeProfileMeta?.description}
        mixOpen={mixOpen}
        mixBusy={mixBusy}
        mixWeights={mixWeights}
        mixBlend={mixBlend}
        mixWarnings={mixWarnings}
        onDomain={setDomain}
        onTopic={setTopic}
        onProfileName={setProfileName}
        onRun={run}
        onSpark={spark}
        onMixOpenToggle={() => setMixOpen((o) => !o)}
        onMixWeight={(id, value) =>
          setMixWeights((w) => ({ ...w, [id]: value }))
        }
        onBuildMix={buildMix}
      />

      <ComparePanel
        profileName={profileName}
        profiles={profiles}
        compareB={compareB}
        vetoProfile={vetoProfile}
        compareBusy={compareBusy}
        compareErr={compareErr}
        compareOpen={compareOpen}
        compareData={compareData}
        onCompareB={setCompareB}
        onVetoProfile={setVetoProfile}
        onCompare={runCompare}
        onConstitutionCompare={runConstitutionCompare}
      />

      <StanceLensList results={results} stance={activeStance} />

      {activeStance === "curiosity" && (
        <RankPanel
          domain={domain}
          profileLabel={activeProfile ?? profileName}
          resultMode={resultMode}
          results={results}
          preferredIds={preferredIds}
          outcomeDraft={outcomeDraft}
          feedbackCount={feedback.length}
          feedbackNote={feedbackNote}
          critiqueNote={critiqueNote}
          soundnessNote={soundnessNote}
          error={error}
          onRecordFeedback={recordFeedback}
          onRecordOutcome={recordOutcome}
          onOutcomeDraft={(qid, draft) =>
            setOutcomeDraft((d) => ({ ...d, [qid]: draft }))
          }
          onCritique={critiqueCard}
          onSoundness={soundnessCard}
          onSummarizeFeedback={summarizeFeedback}
          onSuggestPair={suggestPair}
        />
      )}

      {error && activeStance !== "curiosity" && (
        <div className="error">{error}</div>
      )}

      <TrajectoryMap domain={domain} topic={topic} results={results} />

      <ImaginationCanvas results={results} />

      <ConfessionPanel
        results={results}
        profileLabel={activeProfile ?? profileName}
      />

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
