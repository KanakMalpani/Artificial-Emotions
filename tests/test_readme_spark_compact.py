"""README 60-second demo must match live `spark --compact --json` keys.

Does not freeze question text: the documented keys and types are the contract.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from artificial_emotions.cli import main

_README = Path(__file__).resolve().parents[1] / "README.md"
_SIXTY_SECOND = "## The 60-second demo"

# Keys the 60-second block documents. Live payload must carry these; values may move.
_README_KEYS = ("question", "epistemic_cues", "score_band", "flags")
_CUE_KEYS = ("tags", "primary", "honesty")


def _sixty_second_block() -> str:
    text = _README.read_text(encoding="utf-8")
    start = text.index(_SIXTY_SECOND)
    nxt = text.find("\n## ", start + len(_SIXTY_SECOND))
    return text[start:nxt] if nxt != -1 else text[start:]


def _run_spark(capsys, *argv: str) -> dict:
    assert main(list(argv)) == 0
    out = capsys.readouterr().out
    assert out.strip(), f"no stdout for spark {' '.join(argv)}"
    return json.loads(out)


def test_readme_sixty_second_block_is_honest():
    block = _sixty_second_block()
    assert "emotions spark --domain ai --n 5 --compact --json" in block
    assert "unedited" not in block.lower()
    assert "live compact" in block.lower()
    assert "emotions spark --domain ai --n 5" in block
    for key in _README_KEYS:
        assert f'"{key}"' in block, f"README demo missing documented key {key!r}"
    for key in _CUE_KEYS:
        assert f'"{key}"' in block, f"README epistemic_cues missing {key!r}"
    # The old demo lied: cues were a string list. Live compact_unknown uses an object.
    assert re.search(r'"epistemic_cues"\s*:\s*\{', block)


def test_compact_spark_has_readme_keys_not_frozen_question(capsys):
    payload = _run_spark(capsys, "spark", "--domain", "ai", "--n", "5", "--compact", "--json")
    assert payload.get("rank") == 1
    assert "inject" not in payload
    assert "unknowns" not in payload
    for key in _README_KEYS:
        assert key in payload, f"compact spark missing README key {key!r}"
    assert isinstance(payload["question"], str) and payload["question"].strip()
    cues = payload["epistemic_cues"]
    assert isinstance(cues, dict)
    for key in _CUE_KEYS:
        assert key in cues, f"epistemic_cues missing {key!r}"
    assert isinstance(cues["tags"], list)
    assert isinstance(cues["primary"], str)
    assert isinstance(cues["honesty"], str)
    band = payload["score_band"]
    assert isinstance(band, list) and len(band) == 2
    assert isinstance(payload["flags"], list)


def test_spark_json_without_compact_stays_full_pack(capsys):
    pack = _run_spark(capsys, "spark", "--domain", "ai", "--n", "2", "--json")
    assert "inject" in pack
    assert pack.get("unknowns")
    assert "question" not in pack
