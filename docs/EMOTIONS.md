# Emotions / epistemic cues + mixable catalog

**Short version:** Artificial Curiosity can tag questions with *epistemic* cues, expose a **named emotion catalog**, and **mix** emotions by percentage (e.g. curiosity 40% + confusion 30% + awe 30%). These are **UX / investigation-framing annotations**. The software does **not** feel emotions.

Background research (optional): [`research/AI_EMOTIONS.md`](../research/AI_EMOTIONS.md), [`research/EMOTION_MIXING.md`](../research/EMOTION_MIXING.md), [`research/EMOTION_ACCESS.md`](../research/EMOTION_ACCESS.md).

## What you get

| Output | Meaning |
|--------|---------|
| Cue tags | Stable vocabulary: `information_gap`, `curiosity_target`, `confusion_risk`, `surprise_signal`, `incongruity`, `boredom_guard` |
| Catalog | Named emotions across `epistemic` / `basic` / `social` / `achievement` with optional PAD anchors + elicit hints |
| Mix | `{id: percent\|weight}` → normalized weights (sum=1), blend PAD, cue tags, inject framing |
| Annotate | Heuristic tags from gap status + surprise / neglectedness / answerability |
| Elicit helpers | Short incongruity → investigation framing for inject packs |
| `affective_science` pack | Ranking seeds about affective science / epistemic elicitation (not a CME) |

Honesty fields on responses: `honesty: "annotation_only"` plus an explicit disclaimer.

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

Weights may be **percents** (40+30+30) or **unit weights** (0.4+0.3+0.3). Soft validation accepts either; the engine always **re-normalizes to sum 1.0**. Max **8** components. Unknown ids / negatives / all-zero are rejected.

```bash
curiosity emotions mix curiosity=40 confusion=30 awe=30 --json
```

```python
from artificial_curiosity import mix_emotions

blend = mix_emotions({"curiosity": 40, "confusion": 30, "awe": 30})
assert abs(sum(blend["weights"].values()) - 1.0) < 1e-9
print(blend["percents"], blend["pad"], blend["inject_fragment"])
# also: mix_emotions(curiosity=0.4, confusion=0.3, awe=0.3)
```

```bash
curl -s -X POST http://127.0.0.1:8000/v1/emotions/mix \
  -H "Content-Type: application/json" \
  -d '{"weights":{"curiosity":40,"confusion":30,"awe":30}}'
```

MCP tool: `mix_emotions` with `{"weights": {"curiosity": 40, "confusion": 30, "awe": 30}}`.

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
