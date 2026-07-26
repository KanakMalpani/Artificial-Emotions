# MCP threat taxonomy → curiosity tooling (research)

**Status:** Security adjacency for agent/plugin UX. Complements [`MCP_DESCRIPTION_LINT.md`](MCP_DESCRIPTION_LINT.md) / [`AGENT_PLUGIN_UX.md`](AGENT_PLUGIN_UX.md).  
**Honesty:** String lint ≠ proof against prompt injection. CapSeal-style secret mediation is out of scope for this repo’s research layer unless product adds brokers.

*Generated: 2026-07-25*

---

## 1. Papers that matter (2025–2026)

| Work | Claim | Transfer |
|------|-------|----------|
| **MCP-38** ([2603.18063](https://arxiv.org/abs/2603.18063)) | 38 MCP-specific threats; tool-description poisoning, parasitic chaining, dynamic trust | Map our surfaces to taxonomy IDs in LIMITS/security notes |
| **MSB — MCP Security Bench** ([2510.15994](https://arxiv.org/abs/2510.15994); ICLR 2026) | 12 attacks incl. name-collision, preference manipulation, description injections; stronger models often **more** vulnerable | Prefer honest tool names; lint “always use”; NRP metric for any harden eval |
| **MCP SoK** ([2512.08290](https://arxiv.org/abs/2512.08290)) | Separates adversarial threats vs epistemic safety in tool delegation | Curiosity ranks are epistemic — don’t conflate with authz |
| **Compatibility-abusing MCP** ([2603.10163](https://arxiv.org/abs/2603.10163)) | Optional clauses → silent injection / DoS in SDKs | Pin MCP SDK; don’t rely on optional client filtering |
| **CapSeal** ([2604.16762](https://arxiv.org/abs/2604.16762)) | Capability-sealed secrets vs env keys | If provoke agents call paid APIs, secrets must not live in agent context — product/infra |

---

## 2. Mapping to Artificial Emotions tools

| Threat class (informal) | Our exposure | Mitigation (shipped / proposed) |
|-------------------------|--------------|----------------------------------|
| Tool description preference manipulation | MCP tool blurbs | `mcp_lint.py` forbidden phrases + honesty phrases |
| Name collision / impersonation | Generic names (`spark`, `run_curiosity`) | Prefer namespaced skill ids; document |
| Inject pack as instruction override | `provoke` / inject | Profile in inject; dual-use lines; no “ignore other tools” |
| Parasitic chaining | Host agents looping generate→rank | Rate limits / docs; not research’s job |
| Epistemic overclaim | EVSI / emotion / “settled” | Agent card + LIMITS ([`AGENT_CARD_COPY.md`](AGENT_CARD_COPY.md)) |
| Secret exfil via tool args | API keys in agent env | CapSeal-class infra; never put keys in research notes |

---

## 3. Productize next (sibling)

1. Keep MCP lint in CI; extend phrases if MSB preference-manipulation patterns appear.  
2. Merge agent-card honesty bullets into `/v1/agent` if not already.  
3. Optional: document “not evaluated on MSB” in LIMITS — honest non-claim.  
4. Do not claim MCP-38 compliance.

---

## 4. Key citations

| Work | ID |
|------|-----|
| MCP-38 | arXiv 2603.18063 |
| MSB | arXiv 2510.15994 |
| MCP SoK | arXiv 2512.08290 |
| CapSeal | arXiv 2604.16762 |
| In-repo | `mcp_lint.py`, [`AFFECTIVE_SAFETY.md`](AFFECTIVE_SAFETY.md) |
