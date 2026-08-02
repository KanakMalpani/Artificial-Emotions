/**
 * AffectProvider (C1): maps PAD / embodiment_hint → live --ae-* CSS vars.
 * Respects prefers-reduced-motion and explicit steady mode.
 */

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useAffectStore } from "../store/affectStore";
import {
  applyAffectCssVars,
  deriveAffectCssVars,
  type AffectCssVarMap,
} from "./deriveTokens";
import {
  MOOD_PRESETS,
  type MoodPresetName,
  type AffectPad,
} from "./types";

type AffectContextValue = {
  vars: AffectCssVarMap;
  reducedMotion: boolean;
  affectEnabled: boolean;
};

const AffectContext = createContext<AffectContextValue | null>(null);

function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(() => {
    if (typeof window === "undefined" || !window.matchMedia) return false;
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  });

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onChange = () => setReduced(mq.matches);
    onChange();
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  return reduced;
}

/** Optional `?mood=pleasant|bored|anxious` for demos / Playwright fixtures. */
function moodFromSearch(): MoodPresetName | null {
  if (typeof window === "undefined") return null;
  const raw = new URLSearchParams(window.location.search).get("mood");
  if (raw && raw in MOOD_PRESETS) return raw as MoodPresetName;
  return null;
}

function padFromStore(s: {
  valence: number;
  activation: number;
  dominance: number;
  agency: number;
  boredom: number;
  absorption: number;
}): AffectPad {
  return {
    valence: s.valence,
    activation: s.activation,
    dominance: s.dominance,
    agency: s.agency,
    boredom: s.boredom,
    absorption: s.absorption,
  };
}

export function AffectProvider({ children }: { children: ReactNode }) {
  const steadyMode = useAffectStore((s) => s.steadyMode);
  const valence = useAffectStore((s) => s.valence);
  const activation = useAffectStore((s) => s.activation);
  const dominance = useAffectStore((s) => s.dominance);
  const agency = useAffectStore((s) => s.agency);
  const boredom = useAffectStore((s) => s.boredom);
  const absorption = useAffectStore((s) => s.absorption);
  const setPad = useAffectStore((s) => s.setPad);

  const reducedMotion = usePrefersReducedMotion();

  // Apply URL mood fixture once on mount (e2e / demo).
  useEffect(() => {
    const preset = moodFromSearch();
    if (preset) setPad(MOOD_PRESETS[preset]);
  }, [setPad]);

  const pad = useMemo(
    () =>
      padFromStore({
        valence,
        activation,
        dominance,
        agency,
        boredom,
        absorption,
      }),
    [valence, activation, dominance, agency, boredom, absorption],
  );

  const vars = useMemo(
    () => deriveAffectCssVars(pad, { steadyMode, reducedMotion }),
    [pad, steadyMode, reducedMotion],
  );

  const affectEnabled = vars["--ae-affect-enabled"] === "1";

  useEffect(() => {
    const root = document.documentElement;
    applyAffectCssVars(root, vars);
    root.dataset.aeEnabled = affectEnabled ? "1" : "0";
    root.dataset.aeSteady = steadyMode ? "1" : "0";
    root.dataset.aeReducedMotion = reducedMotion ? "1" : "0";
    return () => {
      // Leave last vars; next provider mount rewrites. Clear data attrs on unmount.
      delete root.dataset.aeEnabled;
      delete root.dataset.aeSteady;
      delete root.dataset.aeReducedMotion;
    };
  }, [vars, affectEnabled, steadyMode, reducedMotion]);

  const value = useMemo(
    () => ({ vars, reducedMotion, affectEnabled }),
    [vars, reducedMotion, affectEnabled],
  );

  return (
    <AffectContext.Provider value={value}>{children}</AffectContext.Provider>
  );
}

export function useAffectCss(): AffectContextValue {
  const ctx = useContext(AffectContext);
  if (!ctx) {
    throw new Error("useAffectCss must be used within AffectProvider");
  }
  return ctx;
}
