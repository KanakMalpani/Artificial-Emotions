# Idea-graph export — honesty & UX (research)

**Status:** Companion to sibling `idea_graph.export_idea_graph` and [`EIG_IDEATION_GRAPHS.md`](EIG_IDEATION_GRAPHS.md).  
**Honesty:** Jaccard similarity ≠ semantic novelty; tag “conflict” ≠ value disagreement from `compare_profiles`.

*Generated: 2026-07-25*

---

## 1. What shipped (shape)

- Nodes: question id, truncated text, optional rank/score/gap/tags/answerability.  
- Edges: `similarity` (Jaccard ≥ threshold) and optional `conflict` (tag pairs).  
- Payload should include `honesty: display_only` / “does not change ranks.”

---

## 2. Recommended consumer UX

| Do | Don’t |
|----|-------|
| Show graph as “relatedness map” | Treat dense similarity as “more valuable” |
| Use conflict edges as **warnings** | Auto-drop nodes without user action |
| Link to profile compare for real value conflict | Claim EIG-level learned edit-and-commit |

---

## 3. Productize next

1. Wire MCP/API if not already; return honesty string.  
2. Optional: add hivemind_mean_cosine on node set into graph metadata.  
3. Eval: graph edge density correlates with hivemind flag (sanity).  
4. Do not feed graph into scorer.

---

## 4. See also

[`HIVEMIND_METRIC_SPEC.md`](HIVEMIND_METRIC_SPEC.md) · [`PROFILE_COMPARE_UX.md`](PROFILE_COMPARE_UX.md)
