/**
 * Demo / session trajectory shapes for C3 map (offline-safe).
 * Real explore payloads share the same step fields.
 */

export type AppraisalEvidence = {
  emotion?: string;
  intensity?: number;
  evidence?: string;
  rule?: string;
  [key: string]: unknown;
};

export type TrajectoryStepView = {
  step: number;
  domain: string;
  topic: string;
  top_question: string;
  top_score: number;
  primary_feeling: string;
  ambivalence: number;
  made_progress: boolean;
  note: string;
  appraisal: AppraisalEvidence[];
  costs: { kind?: string; detail?: string; disclosure?: string }[];
  modulation?: { knob?: string; delta?: number; reason?: string }[];
};

export type TrajectoryView = {
  steps: TrajectoryStepView[];
  dead_ends: string[];
  domains_visited: string[];
  surprises: { question_id?: string; note?: string }[];
  source: "explore" | "session_sketch" | "demo";
};

/** Mood → fill hue for step nodes (honest visualization of primary_feeling). */
export function moodColour(feeling: string): string {
  const f = (feeling || "").toLowerCase();
  if (/anx|fear|reluct/.test(f)) return "#5a6f8a";
  if (/frustr|disappoint|resign/.test(f)) return "#8b5a4a";
  if (/bore|fatigue/.test(f)) return "#8a8f96";
  if (/wonder|surpris|insight|interest|enjoy/.test(f)) return "#c47a1a";
  if (/determin|absor|persist/.test(f)) return "#1f6b5a";
  if (/skept|suspic/.test(f)) return "#6b5a8b";
  if (/compass|respect/.test(f)) return "#2f6b7a";
  return "#3a4a63";
}

/** Build a light sketch from the current ranked set when explore was not run. */
export function sketchFromResults(
  domain: string,
  topic: string,
  questions: { question: string; curiosity_score: number; flags?: string[] }[],
): TrajectoryView {
  if (questions.length === 0) {
    return DEMO_TRAJECTORY;
  }
  const steps: TrajectoryStepView[] = questions.slice(0, 5).map((q, i) => {
    const dead = (q.flags || []).some((f) => f.includes("gate")) || q.curiosity_score < 0.25;
    return {
      step: i + 1,
      domain,
      topic: topic || "",
      top_question: q.question,
      top_score: q.curiosity_score,
      primary_feeling:
        i === 0
          ? "interest"
          : i === 1
            ? "skepticism"
            : i === 2
              ? "wonder"
              : dead
                ? "disappointment"
                : "determination",
      ambivalence: 0.2 + i * 0.08,
      made_progress: !dead,
      note: dead
        ? "Session sketch: low score / gated — drawn as a dead end."
        : "Session sketch from ranked results (not a full explore loop).",
      appraisal: [
        {
          emotion:
            i === 0
              ? "interest"
              : i === 1
                ? "skepticism"
                : i === 2
                  ? "wonder"
                  : "determination",
          evidence: `Top score ${q.curiosity_score.toFixed(2)} in domain=${domain}`,
          rule: "session_sketch",
        },
      ],
      costs:
        i === 2
          ? [
              {
                kind: "distraction",
                detail: "Sketch marker: surprise pulled attention.",
                disclosure: "Cost markers appear when explore logs them.",
              },
            ]
          : [],
      modulation: [],
    };
  });
  const deadEnds = steps
    .filter((s) => !s.made_progress)
    .map((s) => s.top_question.slice(0, 80));
  return {
    steps,
    dead_ends: deadEnds,
    domains_visited: [domain],
    surprises: steps
      .filter((s) => /wonder|surpris/i.test(s.primary_feeling))
      .map((s) => ({ note: s.top_question.slice(0, 60) })),
    source: "session_sketch",
  };
}

/** Always-available demo path so the map is visible without the API. */
export const DEMO_TRAJECTORY: TrajectoryView = {
  source: "demo",
  domains_visited: ["ai", "biology"],
  dead_ends: [
    "Does scaling alone yield alignment? — literature already dense; no new gap.",
  ],
  surprises: [
    { question_id: "demo-q3", note: "Sparse neighbours on mechanistic interpretability transfer." },
  ],
  steps: [
    {
      step: 1,
      domain: "ai",
      topic: "",
      top_question: "Which evaluation gaps still lack operational falsifiers?",
      top_score: 0.72,
      primary_feeling: "interest",
      ambivalence: 0.15,
      made_progress: true,
      note: "Opening pass — fresh ground.",
      appraisal: [
        {
          emotion: "interest",
          intensity: 0.6,
          evidence: "Open gap with moderate neglectedness",
          rule: "open_gap",
        },
      ],
      costs: [],
      modulation: [{ knob: "breadth", delta: 0.05, reason: "interest widens slightly" }],
    },
    {
      step: 2,
      domain: "ai",
      topic: "",
      top_question: "Does scaling alone yield alignment?",
      top_score: 0.41,
      primary_feeling: "disappointment",
      ambivalence: 0.35,
      made_progress: false,
      note: "Dead end — crowded literature, no actionable gap.",
      appraisal: [
        {
          emotion: "disappointment",
          intensity: 0.55,
          evidence: "Gap status likely_answered; high citation neighbourhood",
          rule: "dead_end",
        },
      ],
      costs: [
        {
          kind: "tunnel",
          detail: "Absorption kept the loop on a depleted vein one step too long.",
          disclosure: "Cost disclosed — never loosens risk ceilings.",
        },
      ],
      modulation: [],
    },
    {
      step: 3,
      domain: "biology",
      topic: "aging",
      top_question: "Which aging biomarkers remain unvalidated across cohorts?",
      top_score: 0.68,
      primary_feeling: "wonder",
      ambivalence: 0.22,
      made_progress: true,
      note: "Domain jump after dead end.",
      appraisal: [
        {
          emotion: "wonder",
          intensity: 0.7,
          evidence: "High surprise × neglectedness vs prior domain",
          rule: "novelty_pull",
        },
      ],
      costs: [
        {
          kind: "distraction",
          detail: "Wonder pulled onto a shiny lower-scoring branch than the prior best.",
          disclosure: "Affect cost visible on the trajectory.",
        },
      ],
      modulation: [{ knob: "domain", delta: 1, reason: "jump after dead end" }],
    },
    {
      step: 4,
      domain: "biology",
      topic: "aging",
      top_question: "Can a cheap assay falsify the leading biomarker claim?",
      top_score: 0.74,
      primary_feeling: "determination",
      ambivalence: 0.1,
      made_progress: true,
      note: "Focused follow-through.",
      appraisal: [
        {
          emotion: "determination",
          intensity: 0.65,
          evidence: "Tractable operationalization; prior wonder paid off",
          rule: "progress",
        },
      ],
      costs: [],
      modulation: [{ knob: "depth", delta: 0.1, reason: "determination narrows" }],
    },
  ],
};
