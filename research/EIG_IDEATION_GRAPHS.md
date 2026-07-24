# Evolving Idea Graphs (EIG) — ideation adjacency (research)

**Status:** Competitor note for multi-agent ideation with persistent graph state.  
**Honesty:** EIG optimizes **idea proposals** (novelty/feasibility/clarity). Artificial Curiosity ranks **unknowns under ValueProfile**. Steal graph-state discipline; don’t replace verify+rank.

*Generated: 2026-07-25 | Paper: Dong et al. arXiv [2605.04922](https://arxiv.org/abs/2605.04922)*

---

## 1. What EIG claims

- Multi-agent ideation usually coordinates via ephemeral text (chats/drafts) → hard to track weaknesses.
- **Evolving Idea Graphs:** nodes = claims; edges = support/conflict; unresolved weaknesses stay visible.
- Learned controller: (a) which graph edit agents should run; (b) when to **commit** final proposal.
- Reported gains on AI Idea Bench 2025 / LiveIdeaBench vs baselines; ablations credit explicit graph state.

---

## 2. Transfer

| EIG idea | Our analogue |
|----------|--------------|
| Persistent graph of claims | RankedQuestion + gap notes + critique issues |
| Support/conflict edges | Profile compare / constitutional veto (values conflict) |
| Edit-and-commit | Human confirm before prefs rewrite weights |
| Feasibility node attribute | `answerability` / SFBench-style axis ([`ANSWERABILITY_FEASIBILITY.md`](ANSWERABILITY_FEASIBILITY.md)) |

**Productize (optional, P2):** Export top-n as a tiny JSON “idea graph” for agents (`nodes: questions`, `edges: similarity|conflict`) — display/debug only; no silent re-rank.

---

## 3. Positioning

Curiosity remains **upstream**: choose valuable unanswered questions. EIG-like systems refine proposals **after** a question is chosen (co-scientist adjacency — [`CO_SCIENTIST_LANDSCAPE.md`](CO_SCIENTIST_LANDSCAPE.md)).

---

## 4. Key citations

| Work | ID |
|------|-----|
| EIG | arXiv 2605.04922 |
| SFBench | arXiv 2606.29630 |
| VERITAS | arXiv 2604.12144 |
