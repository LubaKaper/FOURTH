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


def test_markdown_table_escapes_structure_breaking_characters():
    from app import _markdown_table

    rows = [{"Name": "St. Mary's | Unit\nAnnex", "Score": None}]
    table = _markdown_table(rows)
    lines = table.splitlines()

    assert len(lines) == 3  # header, separator, one data row
    assert lines[0] == "| Name | Score |"
    assert "St. Mary's \\| Unit Annex" in lines[2]
    assert "None" in lines[2]


def test_markdown_table_empty_rows_returns_empty_string():
    from app import _markdown_table

    assert _markdown_table([]) == ""


def test_theme_options_are_available_for_sidebar_switching():
    from app import THEMES

    # "maternal_intelligence" (Stitch design system) is the default theme.
    assert list(THEMES) == [
        "maternal_intelligence",
        "mauve_editorial",
        "mustard_sea",
        "apricot_teal",
        "sage_butter",
    ]
    assert THEMES["maternal_intelligence"]["primary"] == "#593a41"
    assert THEMES["mauve_editorial"]["background"] == "#C7A2A6"
    assert THEMES["mustard_sea"]["secondary"] == "#8CB9BD"


def test_theme_css_uses_selected_palette_values():
    from app import THEMES, _theme_css

    css = _theme_css(THEMES["apricot_teal"])

    assert "--fourth-bg: #FAF4EF" in css
    assert "--fourth-primary: #E8A87C" in css
    assert "--fourth-secondary: #7DA9A3" in css


def test_badge_escapes_html():
    from app import _badge

    badge = _badge("<script>", "high")

    assert "<script>" not in badge
    assert "&lt;script&gt;" in badge
    assert "fourth-badge-high" in badge
