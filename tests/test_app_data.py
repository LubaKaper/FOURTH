"""app.py's loader validates demo_results.json before rendering."""

import json

import pytest

from app import load_results


def test_load_results_rejects_missing_keys(tmp_path):
    bad = tmp_path / "demo_results.json"
    bad.write_text(json.dumps({"accounts": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="generated_at"):
        load_results(bad)


def test_load_results_accepts_valid_payload(tmp_path):
    good = tmp_path / "demo_results.json"
    good.write_text(
        json.dumps(
            {
                "generated_at": "2026-07-10T00:00:00+00:00",
                "state": "NY",
                "accounts": [
                    {"facility_id": "330101", "facility_name": "Test", "gap_score": 70.0,
                     "urgency_tier": "high", "lead_angle": "baby_vs_mother_contrast",
                     "data_confidence": "high", "email": None}
                ],
            }
        ),
        encoding="utf-8",
    )
    data = load_results(good)
    assert data["state"] == "NY"
    assert len(data["accounts"]) == 1
