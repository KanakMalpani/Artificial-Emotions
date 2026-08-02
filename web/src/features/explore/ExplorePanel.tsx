import { useQuery } from "@tanstack/react-query";
import {
  DOMAINS,
  FALLBACK_PROFILES,
  MIX_SLIDERS,
  type MixBlend,
  type ProfileMeta,
} from "../../types";

export type ExplorePanelProps = {
  domain: string;
  topic: string;
  profileName: string;
  profiles: ProfileMeta[];
  loading: boolean;
  profileDescription: string | null;
  activeProfileDescription: string | null | undefined;
  mixOpen: boolean;
  mixBusy: boolean;
  mixWeights: Record<string, number>;
  mixBlend: MixBlend | null;
  mixWarnings: string[];
  onDomain: (v: string) => void;
  onTopic: (v: string) => void;
  onProfileName: (v: string) => void;
  onRun: () => void;
  onSpark: () => void;
  onMixOpenToggle: () => void;
  onMixWeight: (id: string, value: number) => void;
  onBuildMix: () => void;
};

/** Mount: domain / profile / topic controls + optional framing mix. */
export function ExplorePanel(props: ExplorePanelProps) {
  const {
    domain,
    topic,
    profileName,
    profiles,
    loading,
    profileDescription,
    activeProfileDescription,
    mixOpen,
    mixBusy,
    mixWeights,
    mixBlend,
    mixWarnings,
    onDomain,
    onTopic,
    onProfileName,
    onRun,
    onSpark,
    onMixOpenToggle,
    onMixWeight,
    onBuildMix,
  } = props;

  return (
    <>
      <div className="controls">
        <label>
          Domain
          <select value={domain} onChange={(e) => onDomain(e.target.value)}>
            {DOMAINS.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </label>
        <label>
          ValueProfile
          <select
            value={profileName}
            onChange={(e) => onProfileName(e.target.value)}
          >
            {profiles.map((p) => (
              <option key={p.name} value={p.name}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Topic focus
          <input
            value={topic}
            onChange={(e) => onTopic(e.target.value)}
            placeholder="optional — e.g. aging biomarkers"
          />
        </label>
        <div className="btn-row">
          <button type="button" onClick={onRun} disabled={loading}>
            {loading ? "Mapping unknowns…" : "Ask what to investigate"}
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={onSpark}
            disabled={loading}
          >
            Fast spark
          </button>
        </div>
      </div>

      {(activeProfileDescription || profileDescription) && (
        <p className="profile-desc">
          <strong>Active profile.</strong>{" "}
          {profileDescription ?? activeProfileDescription}
        </p>
      )}

      <section className="mix-panel" aria-label="Investigation framing mix">
        <button
          type="button"
          className="mix-toggle"
          onClick={onMixOpenToggle}
          aria-expanded={mixOpen}
        >
          {mixOpen ? "Hide" : "Show"} investigation framing mix
          <span className="mix-hint">UX annotation only — does not feel</span>
        </button>
        {mixOpen && (
          <div className="mix-body">
            <p className="mix-honesty">
              Percentages are framing weights for investigation tone — not EES
              scores, not felt emotion, and not a clinical mood measure.
            </p>
            <div className="mix-sliders">
              {MIX_SLIDERS.map((s) => (
                <label key={s.id} className="mix-slider">
                  <span>
                    {s.label}{" "}
                    <em>{Math.round(mixWeights[s.id] ?? 0)}</em>
                  </span>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={mixWeights[s.id] ?? 0}
                    onChange={(e) =>
                      onMixWeight(s.id, Number(e.target.value))
                    }
                  />
                </label>
              ))}
            </div>
            <button type="button" onClick={onBuildMix} disabled={mixBusy}>
              {mixBusy ? "Mixing…" : "Build framing mix"}
            </button>
            {mixBlend && (
              <div className="mix-result">
                {mixWarnings.length > 0 && (
                  <ul className="mix-warnings">
                    {mixWarnings.map((w) => (
                      <li key={w.slice(0, 40)}>{w}</li>
                    ))}
                  </ul>
                )}
                {mixBlend.framing && (
                  <p>
                    <strong>Framing.</strong> {mixBlend.framing}
                  </p>
                )}
                {mixBlend.inject_fragment && (
                  <pre className="mix-inject">{mixBlend.inject_fragment}</pre>
                )}
                <p className="mix-disclaimer">
                  {mixBlend.honesty ||
                    mixBlend.disclaimer ||
                    "Annotation only — this system does not feel."}
                </p>
              </div>
            )}
          </div>
        )}
      </section>
    </>
  );
}

/** TanStack Query hook: load ValueProfile presets (server state). */
export function useProfilesQuery() {
  return useQuery({
    queryKey: ["profiles"],
    queryFn: async (): Promise<ProfileMeta[]> => {
      const r = await fetch("/v1/profiles");
      if (!r.ok) return FALLBACK_PROFILES;
      const data = await r.json();
      if (!data?.presets?.length) return FALLBACK_PROFILES;
      return data.presets.map((p: ProfileMeta) => ({
        name: p.name,
        description: p.description,
      }));
    },
    placeholderData: FALLBACK_PROFILES,
  });
}

export { ExplorePanel as default };
