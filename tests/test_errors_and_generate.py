"""Offline coverage for the ValueError→code bridge, `python -m`, and generation soft-fails."""

from __future__ import annotations

import pytest

from artificial_emotions import errors
from artificial_emotions.errors import (
    ERR_EMPTY_MIX,
    ERR_MIX_TOO_LARGE,
    ERR_NEGATIVE_WEIGHT,
    ERR_UNKNOWN_EMOTION,
    ERR_UNKNOWN_FAMILY,
    ERR_UNKNOWN_GAP_STATUS,
    ERR_UNKNOWN_PACK,
    ERR_UNKNOWN_PROFILE,
    ERR_VALIDATION,
    CuriosityError,
    classify_value_error,
    error_payload,
)
from artificial_emotions.generate import generate_candidates
from artificial_emotions.models import CuriosityConfig


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        # "unknown emotion pack" contains "unknown emotion" — the specific code wins.
        ("Unknown emotion pack 'zzz'. Available: affective_science", ERR_UNKNOWN_PACK),
        ("Unknown pack 'zzz'", ERR_UNKNOWN_PACK),
        ("Unknown emotion id(s): zzz", ERR_UNKNOWN_EMOTION),
        ("Unknown family 'zzz'", ERR_UNKNOWN_FAMILY),
        ("Unknown profile 'zzz'", ERR_UNKNOWN_PROFILE),
        ("Unknown ValueProfile 'zzz'", ERR_UNKNOWN_PROFILE),
        ("Unknown gap_status 'zzz'", ERR_UNKNOWN_GAP_STATUS),
        ("Unknown gap status 'zzz'", ERR_UNKNOWN_GAP_STATUS),
        ("Empty mix", ERR_EMPTY_MIX),
        ("All mix weights are zero", ERR_EMPTY_MIX),
        ("Negative weight for joy", ERR_NEGATIVE_WEIGHT),
        ("Too many components in mix", ERR_MIX_TOO_LARGE),
        ("something else entirely", ERR_VALIDATION),
    ],
)
def test_classify_value_error_codes_are_stable(message: str, expected: str):
    err = classify_value_error(ValueError(message))
    assert err.code == expected
    assert err.message == message
    assert isinstance(err, ValueError)


def test_classify_value_error_passes_typed_errors_through():
    original = CuriosityError(ERR_UNKNOWN_PACK, "boom", details={"available": []})
    assert classify_value_error(original) is original


def test_curiosity_error_to_dict_omits_empty_details():
    assert CuriosityError(ERR_VALIDATION, "bad").to_dict() == {
        "code": ERR_VALIDATION,
        "message": "bad",
    }
    with_details = CuriosityError(ERR_VALIDATION, "bad", details={"field": "n"}).to_dict()
    assert with_details["details"] == {"field": "n"}


def test_curiosity_error_defaults_to_http_400():
    assert CuriosityError(ERR_VALIDATION, "bad").http_status == 400
    assert CuriosityError(ERR_VALIDATION, "bad", http_status=404).http_status == 404


def test_error_payload_envelope_shape():
    assert error_payload("code", "msg") == {"error": {"code": "code", "message": "msg"}}
    assert error_payload("code", "msg", details={"k": 1})["error"]["details"] == {"k": 1}


def test_error_codes_are_unique():
    codes = [v for k, v in vars(errors).items() if k.startswith("ERR_")]
    assert len(codes) == len(set(codes))


def test_dunder_main_prints_surface_help(capsys):
    from artificial_emotions.__main__ import main

    assert main() == 0
    err = capsys.readouterr().err
    assert "curiosity spark" in err
    assert "curiosity-mcp" in err


def test_generate_candidates_offline_respects_candidate_cap():
    cfg = CuriosityConfig(domain="ai", use_llm=False, use_literature=False, n_candidates=5)
    out = generate_candidates(cfg)
    assert 0 < len(out) <= 5
    assert all(q.question for q in out)


def test_generate_candidates_dedupes_pack_questions():
    cfg = CuriosityConfig(
        domain="ai",
        use_llm=False,
        use_literature=False,
        n_candidates=32,
        load_bundled_packs=True,
    )
    out = generate_candidates(cfg)
    texts = [q.question.strip().lower() for q in out]
    assert len(texts) == len(set(texts))


def test_generate_candidates_soft_fails_to_seeds_without_llm_credentials(monkeypatch):
    """use_llm=True with no key must fall back to seeds, not raise."""
    for var in ("LLM_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    cfg = CuriosityConfig(domain="ai", use_llm=True, use_literature=False, n_candidates=4)
    out = generate_candidates(cfg)
    assert out
    assert all(q.source != "llm" for q in out)


def test_generate_candidates_soft_fails_when_llm_raises(monkeypatch):
    """A throwing LLM must degrade to seeds — generation is never a hard dependency."""
    import artificial_emotions.generate as gen

    class Exploding:
        def chat_json(self, system: str, user: str):
            raise RuntimeError("upstream 500")

    monkeypatch.setattr(gen, "_llm_for_config", lambda _cfg: Exploding())
    cfg = CuriosityConfig(domain="ai", use_llm=True, use_literature=False, n_candidates=4)
    out = gen.generate_candidates(cfg)
    assert out
    assert all(q.source != "llm" for q in out)


def test_generate_candidates_skips_malformed_llm_items(monkeypatch):
    import artificial_emotions.generate as gen

    class Partial:
        def chat_json(self, system: str, user: str):
            return {
                "questions": [
                    {"question": "Which mechanism explains X under Y?"},
                    {"operationalization": "no question key at all"},
                ]
            }

    monkeypatch.setattr(gen, "_llm_for_config", lambda _cfg: Partial())
    cfg = CuriosityConfig(domain="ai", use_llm=True, use_literature=False, n_candidates=6)
    out = gen.generate_candidates(cfg)
    llm_items = [q for q in out if q.source == "llm"]
    assert len(llm_items) == 1
    assert llm_items[0].question == "Which mechanism explains X under Y?"
    assert llm_items[0].operationalization
