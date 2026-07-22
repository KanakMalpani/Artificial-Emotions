# Architecture

```
┌─────────────┐   ┌──────────────┐   ┌─────────────┐
│ ValueProfile│──▶│ Curiosity    │──▶│ Ranked Qs + │
│ Domain/Topic│   │ Engine       │   │ Briefs      │
└─────────────┘   └──────┬───────┘   └─────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
   Generate         Verify Gap        Score+Gate
   (seeds/LLM)      (OpenAlex)     (heuristic/LLM)
        │                │                │
        └──────────▶ Diversify ◀──────────┘
```

## Modules

| Module | Path | Role |
|--------|------|------|
| models | `models.py` | Schema + value profile |
| seeds | `seeds.py` | Curated offline unknowns |
| generate | `generate.py` | Seed + optional LLM forge |
| openalex | `openalex.py` | Literature retrieval |
| verify | `verify.py` | Gap status classification |
| scoring | `scoring.py` | Axes + aggregate + gates |
| judge | `judge.py` | Optional LLM scoring |
| diversity | `diversity.py` | Near-dup suppression |
| brief | `brief.py` | Investigation briefs |
| pipeline | `pipeline.py` | Orchestration |
| api | `api.py` | FastAPI |
| cli | `cli.py` | Terminal UX |

## Trust boundaries

- Network: OpenAlex (public), optional OpenAI-compatible endpoint.
- No secrets in repo; API key via env only.
- Literature classifier is heuristic — confidence reflected in output.

## Extension points

1. Swap OpenAlex for Semantic Scholar / OpenScholar.
2. Add embedding-based diversity (replace Jaccard).
3. Add human preference logging → learn value profile weights.
4. Add longitudinal outcome tracking for calibration.
