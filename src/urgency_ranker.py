"""
urgency_ranker.py - Tool 4

Adds ADR urgency context and finalizes gap_score to 0-100.
"""

from typing import Any

from constants import NY_STATE_URGENCY_CONTEXT


VALID_TIERS = {"high", "medium", "low"}
VALID_FLAGS = {"🔴 Act this week", "🟡 Monitor", "🟢 Not ready"}
STATE_URGENCY_CONTEXT = {
    # State facts, not per-hospital signals — sources cited in constants.py.
    "NY": {
        "medicaid_extended": NY_STATE_URGENCY_CONTEXT["medicaid_extended"],
        "racial_disparity_flag": NY_STATE_URGENCY_CONTEXT["racial_disparity_flag"],
    }
}


def _add_urgency_context_fields(hospital: dict[str, Any]) -> None:
    state = str(hospital.get("state") or "").upper()
    defaults = STATE_URGENCY_CONTEXT.get(
        state,
        {"medicaid_extended": False, "racial_disparity_flag": False},
    )
    hospital.setdefault("medicaid_extended", defaults["medicaid_extended"])
    hospital.setdefault("racial_disparity_flag", defaults["racial_disparity_flag"])


def _urgency_context_points(hospital: dict[str, Any]) -> int:
    points = 0
    if hospital.get("state_mortality_rank") == "bottom_quartile":
        points += 10
    if hospital.get("racial_disparity_flag"):
        points += 8
    if hospital.get("medicaid_extended"):
        points += 7
    return min(points, 25)


def _urgency_breakdown(hospital: dict[str, Any]) -> dict[str, int]:
    return {
        "state_mortality_rank": 10 if hospital.get("state_mortality_rank") == "bottom_quartile" else 0,
        "racial_disparity": 8 if hospital.get("racial_disparity_flag") else 0,
        "medicaid_extended": 7 if hospital.get("medicaid_extended") else 0,
    }


def _tier_and_flag(score: float) -> tuple[str, str]:
    if score >= 70:
        return "high", "🔴 Act this week"
    if score >= 40:
        return "medium", "🟡 Monitor"
    return "low", "🟢 Not ready"


def add_urgency(hospital: dict[str, Any]) -> dict[str, Any]:
    if "gap_score" not in hospital:
        raise KeyError("gap_score is required. Run calculate_gap_score() first.")
    if "gap_breakdown" not in hospital:
        raise KeyError("gap_breakdown is required. Run calculate_gap_score() first.")

    _add_urgency_context_fields(hospital)
    urgency_points = _urgency_context_points(hospital)
    final_score = min(float(hospital["gap_score"]) + urgency_points, 100.0)
    tier, flag = _tier_and_flag(final_score)

    hospital["gap_score"] = final_score
    hospital["gap_breakdown"]["urgency_context"] = urgency_points
    hospital["urgency_tier"] = tier
    hospital["urgency_flag"] = flag
    hospital["urgency_breakdown"] = _urgency_breakdown(hospital)

    if tier not in VALID_TIERS:
        raise ValueError(f"Invalid urgency_tier: {tier}")
    if flag not in VALID_FLAGS:
        raise ValueError(f"Invalid urgency_flag: {flag}")

    return hospital
