# MCP progressive disclosure (research)

**Status:** UX spike extending [`AGENT_PLUGIN_UX.md`](AGENT_PLUGIN_UX.md) / ScaleMCP lessons.  
**Honesty:** Fewer tools ≠ safer if the remaining tools overclaim; lint still required.

*Generated: 2026-07-25*

---

## 1. Problem

Hosts that load **all** curiosity tools into context increase:

- Preference-manipulation surface (MSB)  
- Accidental provoke / mix misuse  
- Token cost  

Progressive disclosure: expose a **small core**, then deeper tools on demand.

---

## 2. Suggested tiers

| Tier | Tools (illustrative) | When |
|------|----------------------|------|
| **Core** | `list_profiles`, `run_curiosity` / spark, `list_domains` | Default MCP connect |
| **Investigate** | `critique_brief`, `soundness_pass`, `compare_profiles`, `suggest_next_pair` | After first ranked list |
| **Affect (opt-in)** | `list_epistemic_cues`, `mix_emotions`, elicit helpers | Explicit user/agent enable |
| **Research** | `voi_worksheet`, `surprise_worksheet`, `export_idea_graph`, `cross_model_vote` | Power users / eval |

Affect tier must stay behind an enable flag — aligns with [`AFFECTIVE_SAFETY.md`](AFFECTIVE_SAFETY.md).

---

## 3. Productize next

1. Optional `AC_MCP_TIER=core|full` env or agent-card `tool_tiers`.  
2. Keep mcp_lint on every tier.  
3. Document tier map in `/v1/agent`.  
4. Do not hide dual-use / limits tools — limits should stay in core discoverability (`curiosity://limits`).

---

## 4. See also

[`MCP_THREAT_TAXONOMY.md`](MCP_THREAT_TAXONOMY.md) · [`MCP_DESCRIPTION_LINT.md`](MCP_DESCRIPTION_LINT.md) · [`AGENT_CARD_COPY.md`](AGENT_CARD_COPY.md)
