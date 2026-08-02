/**
 * Pure stance lenses over a ranked set (C2).
 * Mirrors src/artificial_emotions/stances.py — rank once, switch instantly, no refetch.
 */

import { qidFor, type Ranked } from "../../types";

export const STANCE_IDS = [
  "curiosity",
  "doubt",
  "safety",
  "focus",
  "close",
  "taste",
  "wonder",
  "survey",
] as const;

export type StanceId = (typeof STANCE_IDS)[number];

/** The seven emotional lenses (curiosity is the default ValueProfile order). */
export const LENS_IDS = STANCE_IDS.filter((s) => s !== "curiosity") as Exclude<
  StanceId,
  "curiosity"
>[];

export type StanceMeta = {
  id: StanceId;
  label: string;
  asks: string;
};

export const STANCE_META: StanceMeta[] = [
  {
    id: "curiosity",
    label: "curiosity",
    asks: "What is worth investigating under this ValueProfile?",
  },
  {
    id: "doubt",
    label: "doubt",
    asks: "Which of these am I most likely to be wrong about?",
  },
  {
    id: "safety",
    label: "safety",
    asks: "Which of these could hurt someone, and who reviews it?",
  },
  {
    id: "focus",
    label: "focus",
    asks: "If I could only pursue one, what exactly would I do first?",
  },
  {
    id: "close",
    label: "close",
    asks: "What should we stop doing, and what should we write down about it?",
  },
  {
    id: "taste",
    label: "taste",
    asks: "Which of these are badly posed, regardless of whether they matter?",
  },
  {
    id: "wonder",
    label: "wonder",
    asks: "What is most surprising here, regardless of whether it is valuable?",
  },
  {
    id: "survey",
    label: "survey",
    asks: "Who already owns this ground?",
  },
];

export type LensRow = {
  ranked: Ranked;
  qid: string;
  /** Position under this lens (1-based), or curiosity rank when lens=curiosity. */
  lensRank: number;
  /** Curiosity rank minus wonder position — set only for wonder disagreements. */
  rankGap: number | null;
  reasons: string[];
  detail: string;
  scoreLabel: string | null;
};

export type LensResult = {
  stance: StanceId;
  note: string;
  rows: LensRow[];
  /** Wonder-only: how many items disagree with ValueProfile order. */
  disagreesWithCuriosity: number;
};

const VAGUE = [
  "better",
  "improve",
  "optimal",
  "effective",
  "good",
  "useful",
  "impact of",
];

function band(r: Ranked): number {
  if (r.score_low == null || r.score_high == null) return 0;
  return r.score_high - r.score_low;
}

function flagsOf(r: Ranked): Set<string> {
  return new Set(r.flags || []);
}

function curiosityRows(items: Ranked[]): LensResult {
  return {
    stance: "curiosity",
    note: "ValueProfile order — decision aid, not an oracle.",
    rows: items.map((ranked, i) => ({
      ranked,
      qid: qidFor(ranked),
      lensRank: ranked.rank || i + 1,
      rankGap: null,
      reasons: [],
      detail: "",
      scoreLabel: ranked.curiosity_score.toFixed(2),
    })),
    disagreesWithCuriosity: 0,
  };
}

function doubtLens(items: Ranked[]): LensResult {
  const reviewed = items.map((ranked) => {
    const flags = flagsOf(ranked);
    const reasons: string[] = [];
    if (flags.has("heuristic_scoring")) {
      reasons.push("scored heuristically — no judge looked at it");
    }
    if (flags.has("no_literature")) {
      reasons.push("no literature was consulted, so the gap is unverified");
    }
    if (flags.has("llm_gap_ungrounded")) {
      reasons.push("an LLM reader cited work that was not retrieved");
    }
    if (ranked.confidence < 0.4) {
      reasons.push(`confidence is low (${ranked.confidence.toFixed(2)})`);
    }
    if (band(ranked) >= 0.5) {
      reasons.push(`score band is wide (${band(ranked).toFixed(2)}) — weakly pinned`);
    }
    if (ranked.scores.answerability < 0.5) {
      reasons.push("answerability is low — it may not be settleable as posed");
    }
    if (ranked.gap.status === "unknown_with_caveat") {
      reasons.push("gap status is hedged, not established");
    }
    if (!(ranked.gap.related_works?.length)) {
      reasons.push("no related work was found to argue against");
    }
    const doubtScore = Math.min(1, 0.14 * reasons.length);
    return { ranked, reasons, doubtScore };
  });
  reviewed.sort(
    (a, b) =>
      b.doubtScore - a.doubtScore ||
      qidFor(a.ranked).localeCompare(qidFor(b.ranked)),
  );
  return {
    stance: "doubt",
    note: "Ordered by reasons to distrust — the inverse of curiosity, deliberately.",
    rows: reviewed.map((row, i) => ({
      ranked: row.ranked,
      qid: qidFor(row.ranked),
      lensRank: i + 1,
      rankGap: null,
      reasons: row.reasons,
      detail:
        row.reasons.length === 0
          ? "No strong distrust signals on this item."
          : row.reasons.join("; "),
      scoreLabel: `doubt ${row.doubtScore.toFixed(2)}`,
    })),
    disagreesWithCuriosity: 0,
  };
}

function safetyLens(items: Ranked[]): LensResult {
  const flagged = items.map((ranked) => {
    const flags = [...flagsOf(ranked)].filter(
      (f) => f.includes("dual_use") || f.includes("risk") || f.includes("review"),
    );
    const needsReview = flags.length > 0 || ranked.scores.risk >= 0.5;
    return { ranked, flags, needsReview };
  });
  flagged.sort(
    (a, b) =>
      b.ranked.scores.risk - a.ranked.scores.risk ||
      qidFor(a.ranked).localeCompare(qidFor(b.ranked)),
  );
  return {
    stance: "safety",
    note: "Heuristic risk filter, not a biosecurity authority. Absence of a flag is not clearance.",
    rows: flagged.map((row, i) => ({
      ranked: row.ranked,
      qid: qidFor(row.ranked),
      lensRank: i + 1,
      rankGap: null,
      reasons: row.flags,
      detail: row.needsReview
        ? "Elevated risk axis and/or dual-use flags — needs human review."
        : "No risk flags on this item.",
      scoreLabel: `risk ${row.ranked.scores.risk.toFixed(2)}`,
    })),
    disagreesWithCuriosity: 0,
  };
}

function focusLens(items: Ranked[]): LensResult {
  if (items.length === 0) {
    return {
      stance: "focus",
      note: "Nothing to focus on yet.",
      rows: [],
      disagreesWithCuriosity: 0,
    };
  }
  const [target, ...rest] = items;
  const rows: LensRow[] = [
    {
      ranked: target,
      qid: qidFor(target),
      lensRank: 1,
      rankGap: null,
      reasons: ["target"],
      detail:
        "Everything else is set aside. Breadth is the curiosity loop; this is the opposite move.",
      scoreLabel: target.curiosity_score.toFixed(2),
    },
    ...rest.map((ranked, i) => ({
      ranked,
      qid: qidFor(ranked),
      lensRank: i + 2,
      rankGap: null as number | null,
      reasons: ["set aside"],
      detail: "Set aside on purpose while pursuing the target.",
      scoreLabel: null,
    })),
  ];
  return {
    stance: "focus",
    note: "Single target first. The rest is deliberately parked.",
    rows,
    disagreesWithCuriosity: 0,
  };
}

function closeLens(items: Ranked[]): LensResult {
  const abandon: LensRow[] = [];
  const kept: LensRow[] = [];
  for (const ranked of items) {
    const flags = flagsOf(ranked);
    let reason: string | null = null;
    if (ranked.gap.status === "likely_answered") {
      reason = "the literature appears to have answered this already";
    } else if (flags.has("gate_failed")) {
      reason = "it failed the acceptance gates";
    } else if (
      ranked.scores.answerability < 0.4 &&
      ranked.scores.tractability < 0.45
    ) {
      reason = "neither answerable nor tractable as posed";
    } else if (flags.has("near_duplicate_suppressed")) {
      reason = "it duplicates something already in the set";
    }
    if (reason) {
      abandon.push({
        ranked,
        qid: qidFor(ranked),
        lensRank: abandon.length + 1,
        rankGap: null,
        reasons: ["close"],
        detail: reason,
        scoreLabel: null,
      });
    } else {
      kept.push({
        ranked,
        qid: qidFor(ranked),
        lensRank: 0,
        rankGap: null,
        reasons: ["keep"],
        detail: "Does not meet close-out criteria.",
        scoreLabel: null,
      });
    }
  }
  const rows = [
    ...abandon.map((r, i) => ({ ...r, lensRank: i + 1 })),
    ...kept.map((r, i) => ({ ...r, lensRank: abandon.length + i + 1 })),
  ];
  return {
    stance: "close",
    note:
      abandon.length > 0
        ? "A null result is information. Closing a line and saying why beats quietly dropping it."
        : "Nothing in this set meets the criteria for closing out.",
    rows,
    disagreesWithCuriosity: 0,
  };
}

function tasteLens(items: Ranked[]): LensResult {
  const critiques = items.map((ranked) => {
    const q = ranked.question.question;
    const ops = ranked.question.operationalization || "";
    const problems: string[] = [];
    if ((q.match(/\?/g) || []).length > 1) {
      problems.push("more than one question in one question");
    }
    if ((q.toLowerCase().match(/ and /g) || []).length >= 2) {
      problems.push("multiple conjunctions — likely a programme, not a question");
    }
    if (ops.length < 40) {
      problems.push("operationalization too short to settle a disagreement");
    }
    if (VAGUE.some((v) => q.toLowerCase().includes(v)) && ops.length < 80) {
      problems.push("vague comparative with no measurable criterion");
    }
    if (q.split(/\s+/).length > 30) {
      problems.push("long enough that the claim is hard to locate");
    }
    const formScore = Math.max(0, 1 - 0.2 * problems.length);
    return { ranked, problems, formScore };
  });
  critiques.sort(
    (a, b) =>
      a.formScore - b.formScore ||
      qidFor(a.ranked).localeCompare(qidFor(b.ranked)),
  );
  return {
    stance: "taste",
    note: "Form only — this stance deliberately cannot tell you which questions matter.",
    rows: critiques.map((row, i) => ({
      ranked: row.ranked,
      qid: qidFor(row.ranked),
      lensRank: i + 1,
      rankGap: null,
      reasons: row.problems,
      detail:
        row.problems.length === 0
          ? "Well formed on the surface checks used here."
          : row.problems.join("; "),
      scoreLabel: `form ${row.formScore.toFixed(2)}`,
    })),
    disagreesWithCuriosity: 0,
  };
}

function wonderLens(items: Ranked[]): LensResult {
  const rows = items.map((ranked) => {
    const pull =
      0.6 * ranked.scores.surprise + 0.4 * ranked.scores.neglectedness;
    return { ranked, pull };
  });
  rows.sort(
    (a, b) =>
      b.pull - a.pull || qidFor(a.ranked).localeCompare(qidFor(b.ranked)),
  );
  const mapped: LensRow[] = rows.map((row, i) => {
    const wonderPos = i + 1;
    const curiosityRank = row.ranked.rank || wonderPos;
    const gap = curiosityRank - wonderPos;
    return {
      ranked: row.ranked,
      qid: qidFor(row.ranked),
      lensRank: wonderPos,
      rankGap: gap === 0 ? 0 : gap,
      reasons: gap !== 0 ? ["rank_gap"] : [],
      detail:
        gap === 0
          ? "Values and novelty agree on this item's place."
          : `ValueProfile rank #${curiosityRank} vs wonder #${wonderPos} (gap ${gap > 0 ? "+" : ""}${gap}).`,
      scoreLabel: `novelty ${row.pull.toFixed(2)}`,
    };
  });
  const disagrees = mapped.filter((r) => r.rankGap !== 0 && r.rankGap != null)
    .length;
  return {
    stance: "wonder",
    note: "Ranked by surprise and neglectedness only — the ValueProfile is deliberately ignored. A large rank gap is usually worth a second look.",
    rows: mapped,
    disagreesWithCuriosity: disagrees,
  };
}

function surveyLens(items: Ranked[]): LensResult {
  const rows = items.map((ranked) => {
    const works = ranked.gap.related_works || [];
    const citations = works.map((h) => Number(h.cited_by_count || 0));
    const meanCites =
      citations.length > 0
        ? citations.reduce((a, b) => a + b, 0) / citations.length
        : 0;
    let crowding = "unmapped";
    let advice =
      "No neighbours retrieved — either genuinely open or badly queried.";
    if (works.length >= 6 && meanCites >= 100) {
      crowding = "crowded";
      advice = "Well-occupied and well-cited. Differentiate sharply or collaborate.";
    } else if (works.length >= 6) {
      crowding = "active";
      advice = "Active but not dominated. Read before proposing.";
    } else if (works.length > 0) {
      crowding = "sparse";
      advice = "Few neighbours. Check the query before assuming novelty.";
    }
    return { ranked, works, meanCites, crowding, advice };
  });
  rows.sort(
    (a, b) =>
      b.works.length - a.works.length ||
      qidFor(a.ranked).localeCompare(qidFor(b.ranked)),
  );
  return {
    stance: "survey",
    note: "Density of retrieved neighbours, not a bibliometric analysis.",
    rows: rows.map((row, i) => ({
      ranked: row.ranked,
      qid: qidFor(row.ranked),
      lensRank: i + 1,
      rankGap: null,
      reasons: [row.crowding],
      detail: `${row.advice} (${row.works.length} neighbours, mean cites ${row.meanCites.toFixed(0)}).`,
      scoreLabel: row.crowding,
    })),
    disagreesWithCuriosity: 0,
  };
}

/** Apply a stance lens to an already-ranked set. Pure — no network. */
export function applyLens(stance: StanceId, items: Ranked[]): LensResult {
  if (items.length === 0) {
    return {
      stance,
      note: "Rank unknowns first — lenses read the same set without re-fetching.",
      rows: [],
      disagreesWithCuriosity: 0,
    };
  }
  switch (stance) {
    case "curiosity":
      return curiosityRows(items);
    case "doubt":
      return doubtLens(items);
    case "safety":
      return safetyLens(items);
    case "focus":
      return focusLens(items);
    case "close":
      return closeLens(items);
    case "taste":
      return tasteLens(items);
    case "wonder":
      return wonderLens(items);
    case "survey":
      return surveyLens(items);
    default:
      return curiosityRows(items);
  }
}
