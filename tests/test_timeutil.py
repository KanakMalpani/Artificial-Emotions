"""Shared UTC clock / ISO parse — mood, scars, and memory must agree."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from artificial_emotions.timeutil import parse_iso, utc_now, utc_now_iso


def test_parse_iso_accepts_z_naive_and_offset():
    z = parse_iso("2026-07-30T12:00:00Z")
    offset = parse_iso("2026-07-30T12:00:00+00:00")
    naive = parse_iso("2026-07-30T12:00:00")
    assert z == offset == naive == datetime(2026, 7, 30, 12, 0, tzinfo=UTC)


def test_parse_iso_converts_non_utc_offset_and_strips():
    plus = parse_iso(" 2026-07-30T13:30:00+01:30 ")
    assert plus == datetime(2026, 7, 30, 12, 0, tzinfo=UTC)


def test_parse_iso_returns_none_for_missing_or_junk():
    assert parse_iso(None) is None
    assert parse_iso("") is None
    assert parse_iso("   ") is None
    assert parse_iso("not-a-timestamp") is None


def test_utc_now_is_timezone_aware():
    now = utc_now()
    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)
    iso = utc_now_iso()
    parsed = parse_iso(iso)
    assert parsed is not None
    assert parsed.utcoffset() == timedelta(0)
