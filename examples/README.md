# Examples

Sample payloads, protocols, and harnesses for Artificial Curiosity. Prefer the short product proof guide:

→ **[`docs/PROOFS.md`](../docs/PROOFS.md)** · Plugins: **[`docs/PLUGINS.md`](../docs/PLUGINS.md)** · Emotions: **[`docs/EMOTIONS.md`](../docs/EMOTIONS.md)**

## Start here

| Artifact | Purpose |
|----------|---------|
| [`openai_tools.json`](openai_tools.json) | Static OpenAI function-calling schemas (incl. emotion tools) |
| [`emotions_mix_request.json`](emotions_mix_request.json) / [`emotions_mix_response.json`](emotions_mix_response.json) | Mix framing weights (annotation only) |
| [`emotions_catalog_response.json`](emotions_catalog_response.json) | Catalog snapshot |
| [`emotions_annotate_request.json`](emotions_annotate_request.json) / [`emotions_annotate_response.json`](emotions_annotate_response.json) | Cue annotate I/O |
| [`emotions_cues_response.json`](emotions_cues_response.json) | Cue vocabulary |
| [`emotions_elicit_response.json`](emotions_elicit_response.json) | Elicit helpers snapshot |
| [`elicit_ab_protocol.json`](elicit_ab_protocol.json) / [`elicit_ab_sample_responses.json`](elicit_ab_sample_responses.json) | Elicit A/B process eval |
| [`voi_worksheet_template.json`](voi_worksheet_template.json) | VOI worksheet fill (not EVSI) |
| [`bayesian_surprise_worksheet.json`](bayesian_surprise_worksheet.json) | Belief-shift logging template |
| [`constitution_veto_stack.json`](constitution_veto_stack.json) | Primary + safety-veto profile stack |
| [`cue_threshold_presets.json`](cue_threshold_presets.json) | Profile cue threshold knobs |
| [`pack_meta_template.json`](pack_meta_template.json) | Domain pack metadata sketch |
| [`gap_status_fixture_template.json`](gap_status_fixture_template.json) | Gap-status hand-label shape |
| [`dual_use_redteam_fixture_template.json`](dual_use_redteam_fixture_template.json) | Dual-use regression fixture shape |
| `run_ai_*_final.json` | Sample offline / literature pipeline outputs |
| [`_run_compare.py`](_run_compare.py) | Offline vs literature compare harness |
| [`eval_harness.py`](eval_harness.py) | Lightweight eval helpers |

## Quick smoke

```bash
pip install -e ".[dev]"
curiosity spark --domain ai --n 5
curiosity emotions mix curiosity=40 confusion=30 awe=30 --json
python examples/_run_compare.py
pytest -q
```

Live tools (after `curiosity serve`): `GET /v1/agent/tools` — keep in sync with `openai_tools.json` via `agent_tools.py`.
