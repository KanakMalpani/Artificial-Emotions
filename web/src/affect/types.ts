/**
 * Affect types for MoodShell (C1).
 * Mirrors PAD + embodiment_hint from affect.py — visualization only.
 */

/** Continuous PAD-aligned numbers written into CSS vars. */
export type AffectPad = {
  /** Pleasure / valence: -1 unpleasant … +1 pleasant */
  valence: number;
  /** Arousal / activation: 0 calm … 1 activated */
  activation: number;
  /** Dominance: -1 overwhelmed … +1 empowered */
  dominance: number;
  /** Agency proxy (0..1), usually derived from dominance / hint */
  agency: number;
  /** 0..1 — drives desaturation + slower pulse when high */
  boredom: number;
  /** 0..1 — non-focused UI recedes when high */
  absorption: number;
};

/** Qualitative embodiment_hint labels from felt_simulation. */
export type EmbodimentHint = {
  valence: string;
  activation: string;
  agency: string;
};

/** Numeric mood.P / mood.A / mood.D from felt_simulation.mood */
export type FeltMoodPad = {
  P?: number;
  A?: number;
  D?: number;
};

export type FeltSimulationLike = {
  mood?: FeltMoodPad & { qualitative?: EmbodimentHint & { arousal?: string; dominance?: string } };
  embodiment_hint?: EmbodimentHint;
  primary_feeling?: string;
};

export const NEUTRAL_PAD: AffectPad = {
  valence: 0,
  activation: 0.35,
  dominance: 0,
  agency: 0.5,
  boredom: 0,
  absorption: 0,
};

/** Named fixtures for demos / Playwright visual coverage. */
export const MOOD_PRESETS = {
  pleasant: {
    valence: 0.72,
    activation: 0.68,
    dominance: 0.42,
    agency: 0.72,
    boredom: 0,
    absorption: 0.15,
  },
  bored: {
    valence: -0.08,
    activation: 0.14,
    dominance: -0.22,
    agency: 0.28,
    boredom: 0.88,
    absorption: 0,
  },
  anxious: {
    valence: -0.68,
    activation: 0.82,
    dominance: -0.55,
    agency: 0.22,
    boredom: 0,
    absorption: 0.12,
  },
} as const satisfies Record<string, AffectPad>;

export type MoodPresetName = keyof typeof MOOD_PRESETS;
