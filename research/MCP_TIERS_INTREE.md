# MCP tool tiers — in-tree map (research)

**Status:** Aligns [`MCP_PROGRESSIVE_DISCLOSURE.md`](MCP_PROGRESSIVE_DISCLOSURE.md) with product `mcp_tool_tiers()` / `CURIOSITY_MCP_TIER`.  
**Honesty:** Default `full` preserves prior host behavior; tiers reduce surface, not attack proof.

*Generated: 2026-07-25*

---

## 1. Observed contract

| Piece | Role |
|-------|------|
| Env `CURIOSITY_MCP_TIER` | `core` / `investigate` / `affect` / `research` / `full` |
| `/v1/agent` → `tool_tiers` | Machine-readable map |
| Affect tools | Opt-in tier — don’t force into core |

Keep mcp_lint on all exposed descriptions. Limits discoverability stays in core.

---

## 2. Productize next

1. Document env in PLUGINS.md if missing.  
2. Web/agent card one-liner: “Affect tools are opt-in.”  
3. Eval: core tier never omits dual-use/risk tools needed for safety.

---

## 3. See also

[`AGENT_PLUGIN_UX.md`](AGENT_PLUGIN_UX.md) · [`MCP_THREAT_TAXONOMY.md`](MCP_THREAT_TAXONOMY.md)
