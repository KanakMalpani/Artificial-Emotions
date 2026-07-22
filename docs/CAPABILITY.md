CAPABILITY
- For a chosen domain/topic and explicit value profile, the system produces a ranked list of unanswered (or partially answered) scientific questions with multi-axis scores, literature gap evidence, confidence, and investigation briefs — so a human or downstream agent can decide what to investigate next.

CONSTRAINTS
- Ranking requires an explicit ValueProfile (defaults provided, not hidden).
- Candidates failing answerability, risk, or likely-answered gates cannot appear in the returned top-N.
- Near-duplicate questions are suppressed.
- When literature is unavailable, gap status must be `unknown_with_caveat` and confidence lowered.
- Heuristic scoring must be flagged in `flags`.
- Scores are estimates, never presented as ground truth.

IMPLEMENTATION CONTRACT
- Actors: researcher, funder, AI scientist agent, operator.
- Surfaces: Python library, CLI (`curiosity`), HTTP (`POST /v1/curiosity/run`), web UI.
- States: candidate → gap-verified → scored → gated → diversified → briefed.
- Interfaces: `CuriosityConfig` in; `list[RankedQuestion]` out.
- Data: no persistent DB in v0.1; optional future preference store.
- Security: no elevated privileges; outbound only to OpenAlex + optional LLM API.

NON-GOALS
- Running lab experiments or writing papers.
- Replacing systematic reviews.
- Claiming universal, value-free prioritization of all science.

OPEN QUESTIONS
- Best calibration dataset for prospective question quality.
- Whether separate generator/judge models materially reduce self-preference.
- Funding-signal neglectedness beyond publication density.

HANDOFF
- Ready for local use and iteration. Next: embedding diversity, preference learning, and expert panel eval harness.
