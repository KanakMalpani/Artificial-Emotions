# Emotions / computational affect + mixable catalog

**Short version:** Artificial Curiosity exposes a **named emotion catalog** and **percentage mixes** that drive a **felt_simulation** — PAD mood, intensity, and first-person computational affect — as close to “feeling” as a CME-style blend allows. It is **not** biological consciousness or biometric emotion recognition.

Background (optional): [`research/AI_EMOTIONS.md`](../research/AI_EMOTIONS.md), [`research/EMOTION_MIXING.md`](../research/EMOTION_MIXING.md).

## What you get

| Output | Meaning |
|--------|---------|
| Cue tags | Epistemic vocabulary: `information_gap`, `curiosity_target`, `confusion_risk`, … |
| Catalog | Named emotions (`epistemic` / `basic` / `social` / `achievement`) with PAD anchors |
| Mix / `feel()` | `{id: percent}` → weights + **felt_simulation** (mood, intensity, inner monologue) |
| Annotate | Heuristic epistemic tags from gap + axes |
| `affective_science` pack | Ranking seeds about affect science |

Honesty: `computational_affect` — simulated state for investigation framing.

## Plug-in one-liners

```bash
# MCP (Cursor / Claude Desktop) — see docs/PLUGINS.md
curiosity-mcp --list-tools   # expect emotion_catalog, mix_emotions, …

# HTTP
curiosity serve
curl -s http://127.0.0.1:8000/v1/emotions/catalog
curl -s -X POST http://127.0.0.1:8000/v1/emotions/mix \
  -H "Content-Type: application/json" \
  -d '{"weights":{"curiosity":40,"confusion":30,"awe":30}}'
curl -s "http://127.0.0.1:8000/v1/curiosity/provoke?domain=ai&n=3&fast=true"

# OpenAI tools JSON
# examples/openai_tools.json  OR  GET /v1/agent/tools
```

```python
from artificial_curiosity import emotion_catalog, mix_emotions, provoke

print(emotion_catalog()["ids"][:5])
print(mix_emotions(curiosity=40, confusion=30, awe=30)["inject_fragment"])
print(provoke(domain="ai", n=3, fast=True)["inject"][:120])
```

Examples: [`emotions_mix_request.json`](../examples/emotions_mix_request.json), [`emotions_mix_response.json`](../examples/emotions_mix_response.json), [`emotions_catalog_response.json`](../examples/emotions_catalog_response.json).

## Individual emotions

```bash
curiosity emotions catalog
curiosity emotions catalog --family epistemic --json
```

```python
from artificial_curiosity import emotion_catalog
print(emotion_catalog()["ids"])
print(emotion_catalog(family="epistemic")["count"])
```

```bash
curl -s http://127.0.0.1:8000/v1/emotions/catalog
curl -s "http://127.0.0.1:8000/v1/emotions/catalog?family=epistemic"
```

## Percentage mixes

Weights may be **percents** (40+30+30) or **unit weights** (0.4+0.3+0.3). Soft validation accepts either; the engine always **re-normalizes to sum 1.0**. Max **8** components. Unknown ids / negatives / all-zero are rejected (`unknown_emotion` / `empty_mix` / `negative_weight`).

### As Close to Feeling as Possible

By default, the mix is configured to be **as close to feeling as possible** (`simulate_feeling=True`), generating first-person prose, intensity, and continuous PAD (Pleasure-Arousal-Dominance) mood vectors. If you only want the raw weights and PAD values without the first-person prose simulation, you can set `simulate_feeling=False` in the Python function, HTTP API, or MCP tool.

```bash
# Mix emotions via CLI with simulate_feeling disabled
curiosity emotions mix curiosity=40 confusion=30 awe=30 --simulate-feeling false --json
```

```python
from artificial_curiosity import mix_emotions, feel

# Mix emotions with full felt simulation (as close to feeling as possible)
blend = mix_emotions({"curiosity": 40, "confusion": 30, "awe": 30}, simulate_feeling=True)
assert abs(sum(blend["weights"].values()) - 1.0) < 1e-9
print(blend["felt_simulation"]["inner_monologue"])

# Or use the feel() alias which is hardcoded to simulate_feeling=True
felt = feel(curiosity=50, awe=50)
print(felt["felt_simulation"]["intensity"])

# Mix emotions with simulate_feeling disabled
blend_no_feel = mix_emotions({"curiosity": 40, "confusion": 30, "awe": 30}, simulate_feeling=False)
assert blend_no_feel["felt_simulation"] is None
```

```bash
# Mix emotions via HTTP API with simulate_feeling enabled (default)
curl -s -X POST http://127.0.0.1:8000/v1/emotions/mix \
  -H "Content-Type: application/json" \
  -d '{"weights":{"curiosity":40,"confusion":30,"awe":30}}'

# Mix emotions via HTTP API with simulate_feeling disabled
curl -s -X POST http://127.0.0.1:8000/v1/emotions/mix \
  -H "Content-Type: application/json" \
  -d '{"weights":{"curiosity":40,"confusion":30,"awe":30},"simulate_feeling":false}'
```

MCP tool: `mix_emotions` with `{"weights": {"curiosity": 40, "confusion": 30, "awe": 30}, "simulate_feeling": true}`.

Optional `plutchik_dyad_hint` appears only for exact two-component primary dyads (e.g. joy+trust → love) — a **taxonomic metaphor**, not a measured compound emotion.

## 3-step quickstart (cues / annotate)

### 1. CLI

```bash
curiosity emotions cues
curiosity emotions annotate "What remains unknown about epistemic emotion elicitation?" --surprise 0.7 --gap unanswered
curiosity emotions elicit
curiosity emotions pack --json
# alias: curiosity epistemic …
```

### 2. HTTP

```bash
curiosity serve
# then:
curl -s http://127.0.0.1:8000/v1/emotions/cues
curl -s -X POST http://127.0.0.1:8000/v1/emotions/annotate \
  -H "Content-Type: application/json" \
  -d '{"question":"What remains unknown about epistemic emotion elicitation?","surprise":0.7}'
curl -s http://127.0.0.1:8000/v1/emotions/elicit
curl -s "http://127.0.0.1:8000/v1/emotions/pack?name=affective_science"
```

`/v1/epistemic/*` is an alias of `/v1/emotions/*`.

### 3. Python / MCP

```python
from artificial_curiosity import list_epistemic_cues, annotate_epistemic, emotion_pack
# or: from artificial_curiosity.emotions import …

print(list_epistemic_cues()["tags"])
print(annotate_epistemic(
    "What remains unknown about epistemic emotion elicitation?",
    surprise=0.7,
    gap_status="unanswered",
)["epistemic_cues"])
print(emotion_pack("affective_science")["count"])
```

MCP tools: `list_epistemic_cues`, `emotion_catalog`, `mix_emotions`, `annotate_epistemic`, `emotion_pack`, `elicit_helpers` (plus existing provoke/rank tools). Resource: `curiosity://emotions`.

## Relation to provoke

`curiosity spark` / `GET /v1/curiosity/provoke` already attach `epistemic_cues` on each unknown and include anti-anthropomorphism framing in `inject`. The `/v1/emotions/*` surface makes the same vocabulary usable **without** running a full spark — e.g. annotate a draft question, pull the catalog, or author a percentage mix for inject context.

## Anti-anthropomorphism

Do **not** market mixes or tags as “the AI is 40% curious / confused / in awe.” Prefer:

- information gap / incongruity / investigation target  
- decision aid for what to investigate next  
- framing weights (normalized %), not felt intensities  

Mix responses include `claims_not` listing what the payload is **not** (phenomenal feeling, EES scores, OCC intensity, clinical PAD mood).

See also [`LIMITS.md`](LIMITS.md) and [`research/EMOTION_MIXING.md`](../research/EMOTION_MIXING.md).
