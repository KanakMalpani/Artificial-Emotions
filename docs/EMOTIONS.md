# Emotions / epistemic cues

**Short version:** Artificial Curiosity can tag questions with *epistemic* cues (information gap, incongruity, confusion risk, …) and ship an `affective_science` domain pack. These are **UX / investigation-framing annotations**. The software does **not** feel emotions.

Background research (optional): [`research/AI_EMOTIONS.md`](../research/AI_EMOTIONS.md).

## What you get

| Output | Meaning |
|--------|---------|
| Cue tags | Stable vocabulary: `information_gap`, `curiosity_target`, `confusion_risk`, `surprise_signal`, `incongruity`, `boredom_guard` |
| Annotate | Heuristic tags from gap status + surprise / neglectedness / answerability |
| Elicit helpers | Short incongruity → investigation framing for inject packs |
| `affective_science` pack | Ranking seeds about affective science / epistemic elicitation (not a CME) |

Honesty fields on responses: `honesty: "annotation_only"` plus an explicit disclaimer.

## 3-step quickstart

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

MCP tools: `list_epistemic_cues`, `annotate_epistemic`, `emotion_pack`, `elicit_helpers` (plus existing provoke/rank tools). Resource: `curiosity://emotions`.

## Relation to provoke

`curiosity spark` / `GET /v1/curiosity/provoke` already attach `epistemic_cues` on each unknown and include anti-anthropomorphism framing in `inject`. The `/v1/emotions/*` surface makes the same vocabulary usable **without** running a full spark — e.g. annotate a draft question, or pull the affective-science pack for evals.

## Anti-anthropomorphism

Do **not** market these tags as “the AI is curious / confused / surprised.” Prefer:

- information gap / incongruity / investigation target  
- decision aid for what to investigate next  

See also [`LIMITS.md`](LIMITS.md).
