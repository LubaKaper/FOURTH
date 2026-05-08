import copy
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dashboard_generator import generate_dashboard
from gap_calculator import calculate_gap_score
from tests.fixtures import HIGH_GAP, LOW_GAP, MEDIUM_GAP, NULL_DATA
from urgency_ranker import add_urgency


def _finalized(fixture: dict) -> dict:
    return add_urgency(calculate_gap_score(copy.deepcopy(fixture)))


def _email(facility_id: str, urgency_tier: str, lead_angle: str) -> dict:
    return {
        "facility_id": facility_id,
        "facility_name": f"Hospital {facility_id}",
        "recipient_role": "VP Patient Experience",
        "subject": "Close the postpartum follow-up gap",
        "email_body": "Babyscripts email body for human review.",
        "product": "Babyscripts",
        "lead_angle": lead_angle,
        "gap_score": 75.0,
        "urgency_tier": urgency_tier,
        "sent_at": None,
        "status": "pending_review",
    }


def _dashboard_inputs() -> tuple[list[dict], list[dict]]:
    high = _finalized(HIGH_GAP)
    medium = _finalized(MEDIUM_GAP)
    low = _finalized(LOW_GAP)
    null_data = _finalized(NULL_DATA)
    emails = [
        _email(high["facility_id"], high["urgency_tier"], high["lead_angle"]),
        _email(medium["facility_id"], medium["urgency_tier"], medium["lead_angle"]),
    ]
    return [low, medium, null_data, high], emails


def test_generate_dashboard_writes_html_file(tmp_path):
    hospitals, emails = _dashboard_inputs()
    output_path = tmp_path / "echo_dashboard.html"

    result = generate_dashboard(hospitals, emails, output_path)

    assert result == output_path
    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")


def test_dashboard_includes_summary_counts(tmp_path):
    hospitals, emails = _dashboard_inputs()
    output_path = tmp_path / "echo_dashboard.html"

    generate_dashboard(hospitals, emails, output_path)
    html = output_path.read_text(encoding="utf-8")

    assert "[HIGH] 1 accounts" in html
    assert "[MEDIUM] 1 accounts" in html
    assert "Total emails queued: 2" in html


def test_dashboard_lists_ranked_high_and_medium_hospitals_only(tmp_path):
    hospitals, emails = _dashboard_inputs()
    output_path = tmp_path / "echo_dashboard.html"

    generate_dashboard(hospitals, emails, output_path)
    html = output_path.read_text(encoding="utf-8")

    assert html.index("Test High Gap Hospital") < html.index("Test Medium Gap Hospital")
    assert "Test Low Gap Hospital" not in html


def test_dashboard_has_clickable_hospital_navigation(tmp_path):
    hospitals, emails = _dashboard_inputs()
    output_path = tmp_path / "echo_dashboard.html"

    generate_dashboard(hospitals, emails, output_path)
    html = output_path.read_text(encoding="utf-8")

    assert '<button class="account-row active" data-target="hospital-330101">' in html
    assert '<article id="hospital-330101" class="hospital-card high active">' in html
    assert "function selectHospital" in html


def test_dashboard_excludes_low_confidence_low_tier_accounts(tmp_path):
    hospitals, emails = _dashboard_inputs()
    output_path = tmp_path / "echo_dashboard.html"

    generate_dashboard(hospitals, emails, output_path)
    html = output_path.read_text(encoding="utf-8")

    assert "Test Null Data Hospital" not in html


def test_dashboard_displays_required_hospital_fields(tmp_path):
    hospitals, emails = _dashboard_inputs()
    output_path = tmp_path / "echo_dashboard.html"

    generate_dashboard(hospitals, emails, output_path)
    html = output_path.read_text(encoding="utf-8")

    assert "NY" in html
    assert "high" in html
    assert "Act this week" in html
    assert "Patient experience gap" in html
    assert "high confidence" in html
    assert "Earned the CMS Birthing-Friendly designation" in html


def test_dashboard_displays_email_body_and_status(tmp_path):
    hospitals, emails = _dashboard_inputs()
    output_path = tmp_path / "echo_dashboard.html"

    generate_dashboard(hospitals, emails, output_path)
    html = output_path.read_text(encoding="utf-8")

    assert "Babyscripts email body for human review." in html
    assert "Babyscripts" in html
    assert "pending_review" in html


def test_dashboard_uses_single_pending_review_email_panel(tmp_path):
    hospitals, emails = _dashboard_inputs()
    output_path = tmp_path / "echo_dashboard.html"

    generate_dashboard(hospitals, emails, output_path)
    html = output_path.read_text(encoding="utf-8")

    assert "Email review workspace" in html
    assert "Recommended contact: VP Patient Experience" in html
    assert '<button class="variant-tab' not in html


def test_dashboard_states_human_must_review_and_send(tmp_path):
    hospitals, emails = _dashboard_inputs()
    output_path = tmp_path / "echo_dashboard.html"

    generate_dashboard(hospitals, emails, output_path)
    html = output_path.read_text(encoding="utf-8")

    assert "No email has been sent" in html
    assert "human must review, copy, and send" in html


def test_dashboard_escapes_dynamic_text(tmp_path):
    hospital = _finalized(HIGH_GAP)
    hospital["facility_name"] = "<script>alert('x')</script>"
    email = _email(hospital["facility_id"], hospital["urgency_tier"], hospital["lead_angle"])
    output_path = tmp_path / "echo_dashboard.html"

    generate_dashboard([hospital], [email], output_path)
    html = output_path.read_text(encoding="utf-8")

    assert "<script>alert('x')</script>" not in html
    assert "&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt;" in html


def test_dashboard_has_no_required_live_network_calls(tmp_path):
    hospitals, emails = _dashboard_inputs()
    output_path = tmp_path / "echo_dashboard.html"

    generate_dashboard(hospitals, emails, output_path)
    html = output_path.read_text(encoding="utf-8")

    assert "https://fonts.googleapis.com" not in html
    assert "https://fonts.gstatic.com" not in html
    assert "<script src=" not in html
