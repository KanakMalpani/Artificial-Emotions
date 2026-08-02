import { create } from "zustand";
import {
  padFromEmbodimentHint,
  padFromFeltSimulation,
} from "../affect/deriveTokens";
import {
  NEUTRAL_PAD,
  type AffectPad,
  type EmbodimentHint,
  type FeltSimulationLike,
} from "../affect/types";

/**
 * Affect state (C1). PAD / embodiment_hint feed AffectProvider → CSS vars.
 */
export type AffectSlice = AffectPad & {
  embodimentHint: EmbodimentHint | null;
  /** When true, pin affect styling off (steady mode). */
  steadyMode: boolean;
  setPad: (pad: Partial<AffectPad>) => void;
  setSteadyMode: (steady: boolean) => void;
  /** Apply qualitative embodiment_hint labels from felt_simulation. */
  setEmbodimentHint: (hint: EmbodimentHint) => void;
  /** Apply full felt_simulation payload (numeric mood preferred). */
  applyFeltSimulation: (felt: FeltSimulationLike) => void;
};

export const useAffectStore = create<AffectSlice>((set) => ({
  ...NEUTRAL_PAD,
  embodimentHint: null,
  steadyMode: false,
  setPad: (pad) => set((s) => ({ ...s, ...pad })),
  setSteadyMode: (steadyMode) => set({ steadyMode }),
  setEmbodimentHint: (hint) =>
    set({
      ...padFromEmbodimentHint(hint),
      embodimentHint: hint,
    }),
  applyFeltSimulation: (felt) =>
    set({
      ...padFromFeltSimulation(felt),
      embodimentHint: felt.embodiment_hint ?? null,
    }),
}));
