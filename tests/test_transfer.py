"""B3 analogical transfer — structural analogy gated on validate.py lift.

CRITICAL: ``test_transfer_beats_random_pairing_on_the_timesplit_corpus`` is the
ship gate. If lift ≤ 1.0 on the bundled timesplit corpus, the feature must be
cut (TRANSFER_SHIP_STATUS = \"cut\"), not shipped as vanity.
"""

from __future__ import annotations

import json

import pytest

from artificial_emotions.discover import LocalCorpusClient
from artificial_emotions.imagine import (
    HONESTY_IMAGINED,
    IMAGINED_PAYLOAD_KEY,
    assert_imagined_safe,
)
from artificial_emotions.resources import find_data_file
from artificial_emotions.transfer import (
    TRANSFER_GATE_NOTE,
    TRANSFER_SHIP_STATUS,
    TransferLink,
    discover_transfers,
    imagine_transfer,
    transfers_to_imagined,
    validate_transfer_retrospective,
)
from artificial_emotions.validate import split_by_year

TIMESPLIT = "examples/discovery_corpus_timesplit_demo.json"

# Minimal structural ABC shape used for unit checks (same as validate.py CORPUS).
CORPUS = [
    {
        "year": 1979,
        "title": "Fish oil and blood viscosity",
        "concepts": ["Fish oil", "Blood viscosity"],
    },
    {
        "year": 1976,
        "title": "Blood viscosity in Raynaud's",
        "concepts": ["Blood viscosity", "Raynaud disease"],
    },
    # Shared peripheral — structural signal for role similarity.
    {
        "year": 1980,
        "title": "Erythrocyte deformability and fish oil",
        "concepts": ["Fish oil", "Erythrocyte deformability"],
    },
    {
        "year": 1981,
        "title": "Erythrocyte deformability in Raynaud's",
        "concepts": ["Erythrocyte deformability", "Raynaud disease"],
    },
    {
        "year": 1981,
        "title": "Soil nitrogen in grassland",
        "concepts": ["Soil nitrogen", "Grassland ecology"],
    },
    {"year": 1983, "title": "Grazing and grassland", "concepts": ["Grassland ecology", "Grazing"]},
    {
        "year": 1989,
        "title": "Fish oil in Raynaud's: a trial",
        "concepts": ["Fish oil", "Raynaud disease"],
    },
]


# --- ship gate -------------------------------------------------------------------------


def test_transfer_beats_random_pairing_on_the_timesplit_corpus():
    """Ship gate: structural transfer must beat random pairing on held-out future.

    Numbers are asserted explicitly so a vanity pass cannot hide behind
    ``lift is not None``. If this fails, set TRANSFER_SHIP_STATUS = \"cut\".
    """
    report = validate_transfer_retrospective(
        find_data_file(TIMESPLIT),
        seeds=["Fish oil"],
        cutoff_year=1986,
        seed=42,
    )
    assert report.n_proposals >= 1, "transfer produced no proposals from past slice"
    assert report.n_confirmed >= 1, "no transferred analogy confirmed in held-out future"
    assert report.hit_rate is not None and report.hit_rate > 0.0
    assert report.baseline_hit_rate is not None
    assert report.lift is not None, (
        "lift undefined (baseline never hit) — cannot claim the method beats chance; "
        "cut the feature rather than shipping vanity"
    )
    assert report.lift > 1.0, (
        f"transfer lift={report.lift:.3f} did not beat random pairing "
        f"(hit={report.hit_rate:.3f} baseline={report.baseline_hit_rate:.3f}). "
        "CUT — do not ship."
    )
    # Confirmed Raynaud link must be among proposals (historical Swanson case,
    # now under structural role filter).
    confirmed_c = {p["c"] for p in report.proposals if p["confirmed"]}
    assert "Raynaud disease" in confirmed_c
    assert TRANSFER_SHIP_STATUS == "shipped", (
        f"gate cleared (lift={report.lift:.3f}) but TRANSFER_SHIP_STATUS="
        f"{TRANSFER_SHIP_STATUS!r} — update the constant to match reality"
    )


def test_transfer_lift_collapses_to_chance_on_a_dense_corpus():
    """Anti-vanity: when the future confirms everything, lift → ~1.0."""
    path = find_data_file(TIMESPLIT)
    docs = json.loads(path.read_text(encoding="utf-8"))
    # Collect every concept from the past slice and dump them into one future doc.
    past, _ = split_by_year(docs, 1986)
    all_concepts: list[str] = []
    seen: set[str] = set()
    for d in past:
        for c in d.get("concepts") or []:
            name = str(c).strip()
            if name and name.lower() not in seen:
                seen.add(name.lower())
                all_concepts.append(name)
    dense = list(docs) + [
        {
            "year": 1990,
            "title": "Everything together",
            "concepts": all_concepts,
        }
    ]
    report = validate_transfer_retrospective(dense, seeds=["Fish oil"], cutoff_year=1986, seed=42)
    # If transfer proposed nothing, the dense control is vacuous — skip honestly.
    if not report.proposals:
        pytest.skip("no transfer proposals; dense-corpus lift undefined")
    assert report.baseline_hit_rate == pytest.approx(1.0)
    assert report.lift == pytest.approx(1.0, abs=0.01)


def test_ship_status_documents_the_gate():
    assert TRANSFER_SHIP_STATUS in {"shipped", "cut"}
    assert "lift" in TRANSFER_GATE_NOTE.lower()
    assert TRANSFER_SHIP_STATUS in TRANSFER_GATE_NOTE.lower() or (
        "shipped" in TRANSFER_GATE_NOTE.lower() or "cut" in TRANSFER_GATE_NOTE.lower()
    )


# --- method behaviour ------------------------------------------------------------------


def test_structural_signal_required_rejects_pure_bridge_without_role_overlap():
    """A lone A–B / B–C bridge with no shared periphery must not count as transfer."""
    thin = [
        {"year": 1979, "title": "A-B", "concepts": ["Fish oil", "Blood viscosity"]},
        {"year": 1976, "title": "B-C", "concepts": ["Blood viscosity", "Raynaud disease"]},
        # Unrelated filler so the corpus is non-empty for other concepts.
        {"year": 1980, "title": "Soil", "concepts": ["Soil nitrogen", "Grassland ecology"]},
    ]
    client = LocalCorpusClient(documents=thin)
    links = discover_transfers("Fish oil", client=client, require_structural_signal=True)
    assert links == []
    # Without the structural filter, classic ABC would still fire.
    abc_like = discover_transfers("Fish oil", client=client, require_structural_signal=False)
    assert any(link.c == "Raynaud disease" for link in abc_like)


def test_shared_peripheral_produces_a_transfer():
    past = [d for d in CORPUS if int(d["year"]) < 1986]
    client = LocalCorpusClient(documents=past)
    links = discover_transfers("Fish oil", client=client)
    assert links
    assert any(link.c == "Raynaud disease" for link in links)
    top = next(link for link in links if link.c == "Raynaud disease")
    assert top.shared_peripherals >= 1 or top.role_similarity > 0.0
    assert top.b == "Blood viscosity"


def test_future_slice_is_hidden_from_transfer():
    past, future = split_by_year(CORPUS, 1986)
    assert all(int(d["year"]) < 1986 for d in past)
    assert LocalCorpusClient(documents=past).cooccurrence_count("Fish oil", "Raynaud disease") == 0
    assert LocalCorpusClient(documents=future).cooccurrence_count("Fish oil", "Raynaud disease") > 0


# --- ImaginedContent quarantine --------------------------------------------------------


def test_transfers_emit_quarantined_imagined_content():
    link = TransferLink(
        a="Fish oil",
        b="Blood viscosity",
        c="Raynaud disease",
        role_similarity=0.25,
        shared_peripherals=1,
        structure_score=2.5,
        cooccurrence=0,
        gap=0.25,
    )
    imagined = transfers_to_imagined([link])
    assert len(imagined) == 1
    item = imagined[0]
    assert item.kind == "transfer"
    assert item.status == "imagined"
    assert item.confidence is None
    assert item.driven_by == ("respect", "envy", "recognition")
    assert "Fish oil" in item.grounded_in
    assert item.invented
    assert "Transfer" in item.content or "transfer" in item.content.lower()


def test_imagine_transfer_payload_is_quarantined():
    past = [d for d in CORPUS if int(d["year"]) < 1986]
    payload = imagine_transfer("Fish oil", corpus=past)
    assert payload["honesty"] == HONESTY_IMAGINED
    assert payload["confidence"] is None
    assert payload["kind"] == "transfer"
    assert payload["ship_status"] == TRANSFER_SHIP_STATUS
    assert payload.get("ok") is True
    assert IMAGINED_PAYLOAD_KEY in payload
    assert payload[IMAGINED_PAYLOAD_KEY]
    for key in ("ranked", "items", "results", "questions", "candidates"):
        assert key not in payload
    ok, offenders = assert_imagined_safe(payload)
    assert ok, offenders
    for entry in payload[IMAGINED_PAYLOAD_KEY]:
        assert entry["status"] == "imagined"
        assert entry["confidence"] is None
        assert entry["kind"] == "transfer"


def test_imagine_transfer_never_feeds_ranking():
    from artificial_emotions.errors import CuriosityError
    from artificial_emotions.imagine import ImaginedContent, refuse_ranking_injection

    path = find_data_file(TIMESPLIT)
    docs = json.loads(path.read_text(encoding="utf-8"))
    past, _ = split_by_year(docs, 1986)
    payload = imagine_transfer("Fish oil", corpus=past)
    assert payload[IMAGINED_PAYLOAD_KEY], "expected at least one imagined transfer"
    ranking: list[dict] = []
    for raw in payload[IMAGINED_PAYLOAD_KEY]:
        item = ImaginedContent(
            content=raw["content"],
            kind=raw["kind"],
            driven_by=tuple(raw["driven_by"]),
            grounded_in=tuple(raw["grounded_in"]),
            invented=tuple(raw["invented"]),
        )
        with pytest.raises(CuriosityError, match="gap verification|cannot be injected"):
            refuse_ranking_injection(item, ranking, gap_verified=False)


# --- CLI -------------------------------------------------------------------------------


def test_cli_validate_transfer_method(capsys):
    from artificial_emotions.cli import main

    path = str(find_data_file(TIMESPLIT))
    assert (
        main(
            [
                "validate",
                "--method",
                "transfer",
                "--corpus",
                path,
                "--cutoff",
                "1986",
                "--seeds",
                "Fish oil",
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["method"] == "transfer"
    assert payload["n_confirmed"] >= 1
    assert payload["lift_over_baseline"] is not None
    assert payload["lift_over_baseline"] > 1.0


def test_cli_imagine_transfer(capsys, tmp_path):
    from artificial_emotions.cli import main

    # Use pre-cutoff docs only — the full timesplit file already joins A–C
    # in the future slice, so transfer correctly finds no remaining gap there.
    path = find_data_file(TIMESPLIT)
    docs = json.loads(path.read_text(encoding="utf-8"))
    past, _ = split_by_year(docs, 1986)
    past_path = tmp_path / "past_only.json"
    past_path.write_text(json.dumps(past), encoding="utf-8")

    assert (
        main(
            [
                "imagine",
                "transfer",
                "--seed",
                "Fish oil",
                "--corpus",
                str(past_path),
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["honesty"] == HONESTY_IMAGINED
    assert payload["kind"] == "transfer"
    assert payload["confidence"] is None
    assert payload[IMAGINED_PAYLOAD_KEY]
    assert any("Raynaud" in (e.get("content") or "") for e in payload[IMAGINED_PAYLOAD_KEY])


def test_cli_imagine_transfer_requires_corpus_and_seed():
    from artificial_emotions.cli import main

    assert main(["imagine", "transfer"]) == 2


def test_validation_is_deterministic():
    path = find_data_file(TIMESPLIT)
    a = validate_transfer_retrospective(
        path, seeds=["Fish oil"], cutoff_year=1986, seed=7
    ).to_dict()
    b = validate_transfer_retrospective(
        path, seeds=["Fish oil"], cutoff_year=1986, seed=7
    ).to_dict()
    assert a == b
