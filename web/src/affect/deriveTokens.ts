/**
 * Pure PAD / embodiment_hint → CSS custom property map (C1).
 * Tokens must derive from the affect payload — never from hardcoded theme picks
 * at call sites. AffectProvider is the sole writer of live --ae-* values.
 */

import {
  type AffectPad,
  type EmbodimentHint,
  type FeltSimulationLike,
  NEUTRAL_PAD,
} from "./types";

export type AffectCssVarMap = Record<`--ae-${string}`, string>;

export type DeriveOptions = {
  /** Explicit steady mode — pins affect styling off. */
  steadyMode: boolean;
  /** prefers-reduced-motion: reduce — disables affect motion + styling. */
  reducedMotion: boolean;
};

const VALENCE_HINT: Record<string, number> = {
  pleasant: 0.65,
  unpleasant: -0.65,
  ambivalent: 0,
};

const ACTIVATION_HINT: Record<string, number> = {
  activated: 0.75,
  "mid-arousal": 0.5,
  calm: 0.22,
};

const AGENCY_HINT: Record<string, { dominance: number; agency: number }> = {
  empowered: { dominance: 0.55, agency: 0.75 },
  "balanced-agency": { dominance: 0, agency: 0.5 },
  overwhelmed: { dominance: -0.55, agency: 0.25 },
};

function clamp(n: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, n));
}

/** Map qualitative embodiment_hint labels → continuous PAD. */
export function padFromEmbodimentHint(hint: EmbodimentHint): AffectPad {
  const agencyMap = AGENCY_HINT[hint.agency] ?? AGENCY_HINT["balanced-agency"];
  const activation =
    ACTIVATION_HINT[hint.activation] ?? NEUTRAL_PAD.activation;
  const valence = VALENCE_HINT[hint.valence] ?? 0;
  // Calm + ambivalent/unpleasant → mild boredom signal for desaturation path
  const boredom =
    activation <= 0.28 && Math.abs(valence) < 0.35
      ? 0.55
      : activation <= 0.28
        ? 0.35
        : 0;
  return {
    valence,
    activation,
    dominance: agencyMap.dominance,
    agency: agencyMap.agency,
    boredom,
    absorption: 0,
  };
}

/** Prefer numeric mood PAD; fall back to embodiment_hint labels. */
export function padFromFeltSimulation(felt: FeltSimulationLike): AffectPad {
  const hint = felt.embodiment_hint;
  const mood = felt.mood;
  const fromHint = hint ? padFromEmbodimentHint(hint) : { ...NEUTRAL_PAD };

  const valence =
    typeof mood?.P === "number" ? clamp(mood.P, -1, 1) : fromHint.valence;
  const activation =
    typeof mood?.A === "number" ? clamp(mood.A, 0, 1) : fromHint.activation;
  const dominance =
    typeof mood?.D === "number" ? clamp(mood.D, -1, 1) : fromHint.dominance;

  const agency =
    hint && AGENCY_HINT[hint.agency]
      ? AGENCY_HINT[hint.agency].agency
      : clamp((dominance + 1) / 2, 0, 1);

  let boredom = fromHint.boredom;
  if (felt.primary_feeling === "boredom") {
    boredom = Math.max(boredom, 0.8);
  }

  return {
    valence,
    activation,
    dominance,
    agency,
    boredom,
    absorption: fromHint.absorption,
  };
}

function neutralVars(reducedMotion: boolean): AffectCssVarMap {
  return {
    "--ae-valence": "0",
    "--ae-activation": "0.35",
    "--ae-dominance": "0",
    "--ae-agency": "0.5",
    "--ae-color-temperature": "0deg",
    "--ae-saturation": "1",
    "--ae-motion-duration": reducedMotion ? "0ms" : "280ms",
    "--ae-motion-easing": "ease-out",
    "--ae-contrast": "1",
    "--ae-density": "1",
    "--ae-focus-recede": "1",
    "--ae-warmth": "0.5",
    "--ae-coolness": "0.5",
    "--ae-boredom": "0",
    "--ae-absorption": "0",
    "--ae-affect-enabled": "0",
  };
}

/**
 * Derive CSS custom properties from continuous PAD.
 * Valence → colour temperature; activation → motion; dominance → contrast/density;
 * boredom → desaturation; absorption → focus recede.
 */
export function deriveAffectCssVars(
  pad: AffectPad,
  opts: DeriveOptions,
): AffectCssVarMap {
  if (opts.steadyMode || opts.reducedMotion) {
    return neutralVars(opts.reducedMotion);
  }

  const valence = clamp(pad.valence, -1, 1);
  const activation = clamp(pad.activation, 0, 1);
  const dominance = clamp(pad.dominance, -1, 1);
  const agency = clamp(pad.agency, 0, 1);
  const boredom = clamp(pad.boredom, 0, 1);
  const absorption = clamp(pad.absorption, 0, 1);

  // Warm when pleasant, cool when unpleasant (hue-rotate degrees).
  const colorTempDeg = valence * 28;
  const warmth = (valence + 1) / 2;
  const coolness = 1 - warmth;

  // Boredom desaturates; mild grey-out also when valence is strongly negative.
  const saturation = clamp(
    1 - boredom * 0.75 - Math.max(0, -valence) * 0.12,
    0.2,
    1,
  );

  // High activation → quick/restless; low → slow/heavy. Boredom slows further.
  const motionMs = Math.round(
    clamp(720 - activation * 560 + boredom * 280, 120, 900),
  );
  const easing =
    activation >= 0.65
      ? "cubic-bezier(0.22, 1, 0.36, 1)"
      : activation <= 0.3
        ? "ease-in-out"
        : "ease-out";

  // High dominance → sharper contrast, tighter density; low → softer, more spaced.
  const contrast = clamp(1 + dominance * 0.2, 0.8, 1.22);
  const density = clamp(1 - dominance * 0.22, 0.78, 1.25);

  // Absorption: non-focus surfaces recede (opacity multiplier).
  const focusRecede = clamp(1 - absorption * 0.55, 0.35, 1);

  return {
    "--ae-valence": valence.toFixed(4),
    "--ae-activation": activation.toFixed(4),
    "--ae-dominance": dominance.toFixed(4),
    "--ae-agency": agency.toFixed(4),
    "--ae-color-temperature": `${colorTempDeg.toFixed(2)}deg`,
    "--ae-saturation": saturation.toFixed(4),
    "--ae-motion-duration": `${motionMs}ms`,
    "--ae-motion-easing": easing,
    "--ae-contrast": contrast.toFixed(4),
    "--ae-density": density.toFixed(4),
    "--ae-focus-recede": focusRecede.toFixed(4),
    "--ae-warmth": warmth.toFixed(4),
    "--ae-coolness": coolness.toFixed(4),
    "--ae-boredom": boredom.toFixed(4),
    "--ae-absorption": absorption.toFixed(4),
    "--ae-affect-enabled": "1",
  };
}

/** Apply a var map onto an element (typically document.documentElement). */
export function applyAffectCssVars(
  el: HTMLElement,
  vars: AffectCssVarMap,
): void {
  for (const [key, value] of Object.entries(vars)) {
    el.style.setProperty(key, value);
  }
}
