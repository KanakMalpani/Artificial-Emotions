/** Shared API / UI types for feature mount points (C0). */

export type ScoreAxes = {
  impact: number;
  neglectedness: number;
  tractability: number;
  surprise: number;
  answerability: number;
  risk: number;
  cost_proxy: number;
};

export type LitHit = {
  title: string;
  year?: number | null;
  cited_by_count?: number | null;
  url?: string | null;
};

export type Ranked = {
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

export type FeedbackEvent = {
  event_type: string;
  profile_name: string;
  question_id: string;
  question_text: string;
  rank: number;
  curiosity_score: number;
  score_axes: Partial<ScoreAxes>;
  preferred_over_ids?: string[];
  labels?: {
    position?: string;
    result?: string;
    months?: string;
    relation?: string;
  };
  notes?: string;
};

export type ProfileMeta = {
  name: string;
  description: string;
};

export type MixBlend = {
  framing?: string;
  inject_fragment?: string;
  percents?: Record<string, number>;
  honesty?: string;
  disclaimer?: string;
};

export type CompareData = {
  ranks_a?: { rank: number; question: string; curiosity_score: number }[];
  ranks_b?: { rank: number; question: string; curiosity_score: number }[];
  agreement?: { kendall_tau?: number | null; top_k_jaccard?: number | null };
  honesty?: string;
  profile_a?: { name?: string };
  profile_b?: { name?: string };
  veto_applied?: {
    n_kept?: number;
    n_flagged?: number;
    max_risk?: number;
    flagged?: { rank: number; question: string; veto_risk?: number }[];
  };
  constitution?: {
    id?: string;
    primary_profile?: string;
    veto_profile?: string;
  };
};

export type OutcomeDraft = {
  result: string;
  months: string;
  note: string;
};

export const OUTCOME_LABELS = [
  "partial_progress",
  "null",
  "contradicted",
  "answered_elsewhere",
  "abandoned",
] as const;

export const DOMAINS = [
  "ai",
  "biology",
  "medicine",
  "climate",
  "energy",
  "materials",
  "physics",
  "social",
  "general",
] as const;

export const AXIS: { key: keyof ScoreAxes; label: string; tip?: string }[] = [
  { key: "impact", label: "Impact" },
  { key: "neglectedness", label: "Neglected" },
  { key: "tractability", label: "Tractable", tip: "Resource/ops realism (not SFBench)" },
  { key: "surprise", label: "Surprise" },
  {
    key: "answerability",
    label: "Answerable",
    tip: "As-posed specificity — distinct from tractability; not a feasibility score",
  },
];

export const FALLBACK_PROFILES: ProfileMeta[] = [
  { name: "humanity_default", description: "Default multi-stakeholder weights" },
  { name: "funder_10y", description: "Tractable unknowns within ~10 years" },
  { name: "alignment_lab", description: "Neglected alignment / control unknowns" },
  { name: "climate_adaptation", description: "Climate adaptation / resilience" },
  { name: "basic_science", description: "Surprising fundamental unknowns" },
  { name: "near_term_ops", description: "Low-cost near-term operational unknowns" },
  {
    name: "public_demo_strict_risk",
    description: "Public / demo surface with a strict dual-use risk ceiling",
  },
];

export const MIX_SLIDERS: { id: string; label: string }[] = [
  { id: "curiosity", label: "Curiosity" },
  { id: "confusion", label: "Confusion" },
  { id: "awe", label: "Awe" },
  { id: "interest", label: "Interest" },
];

export function qidFor(r: Ranked): string {
  return (
    r.question.id ||
    `rank-${r.rank}-${r.question.question.slice(0, 24).replace(/\s+/g, "_")}`
  );
}
