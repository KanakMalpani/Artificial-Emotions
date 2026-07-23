# Examples & proofs

Runnable demos for Artificial Curiosity. Prefer the short product guide:

→ **[`docs/PROOFS.md`](../docs/PROOFS.md)**

| Artifact | Purpose |
|----------|---------|
| `openai_tools.json` | Static OpenAI function-calling schemas |
| `_run_compare.py` | Offline vs literature compare harness |
| `eval_harness.py` | Lightweight eval helpers |
| `run_ai_*_final.json` | Sample offline / literature outputs |

```bash
pip install -e ".[dev]"
curiosity spark --domain ai --n 5
python examples/_run_compare.py
pytest -q
```
