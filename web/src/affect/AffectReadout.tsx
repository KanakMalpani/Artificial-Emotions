/**
 * Honest visualization of computed affect state (C1).
 * Copy must not claim phenomenal feeling — PAD numbers + CSS token readout only.
 */

import { useAffectStore } from "../store/affectStore";
import { useAffectCss } from "./AffectProvider";
import { MOOD_PRESETS, type MoodPresetName } from "./types";

const PRESET_KEYS = Object.keys(MOOD_PRESETS) as MoodPresetName[];

export function AffectReadout() {
  const { vars, affectEnabled, reducedMotion } = useAffectCss();
  const steadyMode = useAffectStore((s) => s.steadyMode);
  const setSteadyMode = useAffectStore((s) => s.setSteadyMode);
  const setPad = useAffectStore((s) => s.setPad);
  const valence = useAffectStore((s) => s.valence);
  const activation = useAffectStore((s) => s.activation);
  const dominance = useAffectStore((s) => s.dominance);
  const boredom = useAffectStore((s) => s.boredom);

  return (
    <aside
      className="affect-readout"
      data-testid="affect-readout"
      aria-label="Computed affect visualization"
    >
      <div className="affect-readout-head">
        <p className="affect-readout-title">Computed affect</p>
        <p className="affect-readout-honesty">
          Visualization of PAD / embodiment_hint state only — not a claim that
          the system feels. Annotation, not phenomenology.
        </p>
      </div>

      <dl className="affect-readout-grid" data-testid="affect-pad-values">
        <div>
          <dt>valence (P)</dt>
          <dd data-testid="affect-valence">{valence.toFixed(2)}</dd>
        </div>
        <div>
          <dt>activation (A)</dt>
          <dd data-testid="affect-activation">{activation.toFixed(2)}</dd>
        </div>
        <div>
          <dt>dominance (D)</dt>
          <dd data-testid="affect-dominance">{dominance.toFixed(2)}</dd>
        </div>
        <div>
          <dt>boredom</dt>
          <dd data-testid="affect-boredom">{boredom.toFixed(2)}</dd>
        </div>
      </dl>

      <p className="affect-readout-tokens" data-testid="affect-css-tokens">
        <span>
          temp {vars["--ae-color-temperature"]} · sat{" "}
          {vars["--ae-saturation"]} · motion {vars["--ae-motion-duration"]} ·
          contrast {vars["--ae-contrast"]} · density {vars["--ae-density"]}
        </span>
        <span data-testid="affect-enabled-flag">
          {affectEnabled ? "affect on" : "affect off"}
          {steadyMode ? " · steady" : ""}
          {reducedMotion ? " · reduced-motion" : ""}
        </span>
      </p>

      <div className="affect-readout-actions">
        <button
          type="button"
          className="btn-secondary"
          data-testid="affect-steady-toggle"
          aria-pressed={steadyMode}
          onClick={() => setSteadyMode(!steadyMode)}
        >
          {steadyMode ? "Steady on" : "Steady off"}
        </button>
        {PRESET_KEYS.map((name) => (
          <button
            key={name}
            type="button"
            className="btn-feedback"
            data-testid={`affect-preset-${name}`}
            onClick={() => setPad(MOOD_PRESETS[name])}
          >
            {name}
          </button>
        ))}
      </div>
    </aside>
  );
}
