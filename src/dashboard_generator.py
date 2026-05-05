"""
dashboard_generator.py - Static dashboard renderer | Owner: Luba

Generates a self-contained HTML dashboard from finalized hospital dicts and
Tool 5 email objects. This sits alongside human_checkpoint.py and never sends
email.
"""

from html import escape
from pathlib import Path
from typing import Any


URGENCY_ORDER = {"high": 0, "medium": 1}


def _safe(value: Any) -> str:
    if value is None:
        return "data unavailable"
    return escape(str(value), quote=True)


def _eligible_hospitals(hospitals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    eligible = [
        hospital
        for hospital in hospitals
        if hospital.get("urgency_tier") in URGENCY_ORDER
    ]
    return sorted(
        eligible,
        key=lambda hospital: (
            URGENCY_ORDER[hospital.get("urgency_tier", "medium")],
            -float(hospital.get("gap_score") or 0),
            hospital.get("facility_name") or "",
        ),
    )


def _email_by_facility(emails: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(email.get("facility_id")): email
        for email in emails
        if email.get("facility_id") is not None
    }


def _summary(hospitals: list[dict[str, Any]], emails: list[dict[str, Any]]) -> str:
    high_count = sum(
        1 for hospital in hospitals
        if hospital.get("urgency_tier") == "high" and hospital.get("data_confidence") != "low"
    )
    medium_count = sum(
        1 for hospital in hospitals
        if hospital.get("urgency_tier") == "medium" and hospital.get("data_confidence") != "low"
    )
    return (
        f"[HIGH] {high_count} accounts | "
        f"[MEDIUM] {medium_count} accounts | "
        f"Total emails queued: {len(emails)}"
    )


def _metric(label: str, value: Any) -> str:
    return f"""
      <div class="metric">
        <span class="metric-label">{escape(label)}</span>
        <span class="metric-value">{_safe(value)}</span>
      </div>
    """


def _lead_angle_label(value: Any) -> str:
    labels = {
        "hcahps_care_transition_gap": "Patient experience gap",
        "hcahps_discharge_gap": "Discharge support gap",
        "state_strength_vs_hospital_lag": "State strength vs hospital lag",
    }
    return labels.get(str(value), value)


def _email_variants(email: dict[str, Any] | None) -> str:
    if email is None:
        return """
        <section class="email-panel empty">
          <h4>Email generation</h4>
          <p>No email object exists for this hospital. Low-confidence hospitals
          are kept visible for review but skipped by Tool 5.</p>
        </section>
        """

    variants = [
        ("moral", "Moral", "Commitment gap", email.get("body_moral")),
        ("clinical", "Clinical", "Patient-care signal", email.get("body_clinical")),
        ("financial", "Financial", "Reimbursement context", email.get("body_financial")),
    ]
    tabs = "\n".join(
        f"""
          <button class="variant-tab{' active' if index == 0 else ''}" data-variant="{escape(key)}">
            <span>{escape(label)}</span>
            <small>{escape(hint)}</small>
          </button>
        """
        for index, (key, label, hint, _body) in enumerate(variants)
    )
    variant_panels = "\n".join(
        f"""
        <article class="variant-content{' active' if index == 0 else ''}" data-variant-panel="{escape(key)}">
          <div class="variant-label">{escape(label)} variant</div>
          <p>{_safe(body)}</p>
        </article>
        """
        for index, (key, label, _hint, body) in enumerate(variants)
    )
    return f"""
      <section class="email-panel">
        <div class="email-meta">
          <div>
            <div class="eyebrow">Email review workspace</div>
            <h4>{_safe(email.get("subject"))}</h4>
            <div class="email-role">Recommended contact: {_safe(email.get("to_role"))}</div>
          </div>
          <span>{_safe(email.get("generation_method"))}</span>
        </div>
        <div class="variant-tabs" role="tablist" aria-label="Email variants">
          {tabs}
        </div>
        <div class="variant-stage">
          {variant_panels}
        </div>
        <div class="copy-note">Review one variant, adapt it if needed, then copy it into your sending tool. ECHO does not send.</div>
      </section>
    """


def _hospital_dom_id(hospital: dict[str, Any]) -> str:
    facility_id = str(hospital.get("facility_id") or "unknown")
    safe_id = "".join(char if char.isalnum() or char in ("-", "_") else "-" for char in facility_id)
    return f"hospital-{safe_id}"


def _account_row(hospital: dict[str, Any], is_active: bool) -> str:
    confidence = hospital.get("data_confidence")
    score = "data unavailable" if confidence == "low" else hospital.get("gap_score")
    active_class = " active" if is_active else ""
    return f"""
      <button class="account-row{active_class}" data-target="{escape(_hospital_dom_id(hospital))}">
        <span>
          <strong>{_safe(hospital.get("facility_name"))}</strong>
          <small>{_safe(hospital.get("urgency_tier"))} / {_safe(hospital.get("lead_angle"))}</small>
        </span>
        <b>{_safe(score)}</b>
      </button>
    """


def _hospital_card(hospital: dict[str, Any], email: dict[str, Any] | None, is_active: bool) -> str:
    confidence = hospital.get("data_confidence")
    score = "data unavailable" if confidence == "low" else hospital.get("gap_score")
    confidence_label = f"{confidence} confidence" if confidence else "confidence unavailable"
    active_class = " active" if is_active else ""
    tier = escape(str(hospital.get("urgency_tier", "")))

    return f"""
    <article id="{escape(_hospital_dom_id(hospital))}" class="hospital-card {tier}{active_class}">
      <div class="card-head">
        <div>
          <div class="eyebrow">{_safe(hospital.get("state"))} / {_safe(hospital.get("facility_id"))}</div>
          <h3>{_safe(hospital.get("facility_name"))}</h3>
        </div>
        <div class="score-block">
          <span class="score">{_safe(score)}</span>
          <span class="score-label">gap score</span>
        </div>
      </div>

      <div class="status-row">
        <span class="badge">{_safe(hospital.get("urgency_tier"))}</span>
        <span class="badge flag">{_safe(hospital.get("urgency_flag"))}</span>
        <span class="badge confidence">{_safe(confidence_label)}</span>
      </div>

      <div class="metrics">
        {_metric("Lead angle", _lead_angle_label(hospital.get("lead_angle")))}
        {_metric("Commitment", hospital.get("commitment_tag"))}
        {_metric("Discharge info star", hospital.get("discharge_info_star"))}
        {_metric("Overall star", hospital.get("overall_star"))}
      </div>

      {_email_variants(email)}
    </article>
    """


def _render_html(hospitals: list[dict[str, Any]], emails: list[dict[str, Any]]) -> str:
    email_lookup = _email_by_facility(emails)
    ordered_hospitals = _eligible_hospitals(hospitals)
    account_rows = "\n".join(
        _account_row(hospital, index == 0)
        for index, hospital in enumerate(ordered_hospitals)
    )
    cards = "\n".join(
        _hospital_card(
            hospital,
            email_lookup.get(str(hospital.get("facility_id"))),
            index == 0,
        )
        for index, hospital in enumerate(ordered_hospitals)
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ECHO Dashboard</title>
  <style>
    :root {{
      --bg: #f6f7f9;
      --panel: #ffffff;
      --ink: #0b1220;
      --muted: #657084;
      --line: #dfe3ea;
      --blue: #1d4ed8;
      --red: #b91c1c;
      --amber: #b45309;
      --green: #047857;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: radial-gradient(circle at top left, #eaf0ff 0, transparent 34rem), var(--bg);
      color: var(--ink);
      font-family: Georgia, "Times New Roman", serif;
      line-height: 1.5;
    }}
    .shell {{ max-width: 1180px; margin: 0 auto; padding: 32px 20px 64px; }}
    .topbar {{
      display: flex;
      justify-content: space-between;
      gap: 20px;
      align-items: flex-end;
      margin-bottom: 22px;
    }}
    .eyebrow {{
      color: var(--muted);
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 11px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }}
    h1, h2, h3, h4, p {{ margin-top: 0; }}
    h1 {{ margin-bottom: 6px; font-size: 38px; letter-spacing: -0.03em; }}
    .notice {{
      background: #fff7ed;
      border: 1px solid #fed7aa;
      color: #7c2d12;
      border-radius: 12px;
      padding: 12px 14px;
      max-width: 390px;
      font-family: ui-sans-serif, system-ui, sans-serif;
      font-size: 13px;
    }}
    .summary {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 18px;
      margin-bottom: 18px;
      box-shadow: 0 10px 30px rgba(15, 23, 42, 0.07);
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-weight: 700;
    }}
    .dashboard-grid {{
      display: grid;
      grid-template-columns: 330px minmax(0, 1fr);
      gap: 18px;
      align-items: start;
    }}
    .account-list {{
      background: rgba(255, 255, 255, 0.92);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 12px;
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
      position: sticky;
      top: 16px;
    }}
    .account-list h2 {{
      font-size: 17px;
      margin: 4px 6px 12px;
    }}
    .account-row {{
      appearance: none;
      width: 100%;
      border: 1px solid transparent;
      background: transparent;
      color: var(--ink);
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      text-align: left;
      padding: 12px;
      border-radius: 13px;
      cursor: pointer;
      font: inherit;
      margin-bottom: 6px;
    }}
    .account-row:hover,
    .account-row.active {{
      background: #f8fafc;
      border-color: var(--line);
    }}
    .account-row strong,
    .account-row small {{
      display: block;
    }}
    .account-row small {{
      color: var(--muted);
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 10px;
      margin-top: 4px;
      text-transform: uppercase;
    }}
    .account-row b {{
      background: #0b1220;
      border-radius: 10px;
      color: white;
      min-width: 58px;
      padding: 8px;
      text-align: center;
      font-family: ui-sans-serif, system-ui, sans-serif;
    }}
    .hospital-card {{
      display: none;
      background: rgba(255, 255, 255, 0.95);
      border: 1px solid var(--line);
      border-left: 5px solid var(--blue);
      border-radius: 18px;
      padding: 22px;
      margin-bottom: 18px;
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
    }}
    .hospital-card.active {{ display: block; }}
    .hospital-card.high {{ border-left-color: var(--red); }}
    .hospital-card.medium {{ border-left-color: var(--amber); }}
    .card-head {{
      display: flex;
      justify-content: space-between;
      gap: 18px;
      align-items: flex-start;
    }}
    h3 {{ margin-bottom: 8px; font-size: 25px; letter-spacing: -0.02em; }}
    .score-block {{
      min-width: 120px;
      background: #0b1220;
      color: white;
      border-radius: 14px;
      padding: 12px;
      text-align: center;
      font-family: ui-sans-serif, system-ui, sans-serif;
    }}
    .score {{ display: block; font-size: 28px; font-weight: 800; }}
    .score-label {{ color: #cbd5e1; font-size: 11px; text-transform: uppercase; }}
    .status-row {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 16px; }}
    .badge {{
      background: #eef2ff;
      color: #1e3a8a;
      border-radius: 999px;
      padding: 4px 9px;
      font-family: ui-sans-serif, system-ui, sans-serif;
      font-size: 12px;
      font-weight: 700;
    }}
    .flag {{ background: #fff1f2; color: #9f1239; }}
    .confidence {{ background: #ecfdf5; color: var(--green); }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 16px;
    }}
    .metric {{
      border: 1px solid var(--line);
      border-radius: 12px;
      min-width: 0;
      padding: 10px;
    }}
    .metric-label {{
      display: block;
      color: var(--muted);
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 11px;
      text-transform: uppercase;
    }}
    .metric-value {{
      display: block;
      font-family: ui-sans-serif, system-ui, sans-serif;
      font-weight: 700;
      overflow-wrap: anywhere;
      word-break: break-word;
    }}
    .email-panel {{
      border-top: 1px solid var(--line);
      padding-top: 16px;
      font-family: ui-sans-serif, system-ui, sans-serif;
    }}
    .email-panel.empty {{ color: var(--muted); }}
    .email-meta {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-start;
      margin-bottom: 14px;
    }}
    .email-meta h4 {{ margin-bottom: 2px; font-size: 17px; }}
    .email-meta span {{
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      border-radius: 999px;
      color: var(--blue);
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 12px;
      padding: 5px 9px;
      white-space: nowrap;
    }}
    .email-role {{ color: var(--muted); }}
    .variant-tabs {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      margin-bottom: 10px;
    }}
    .variant-tab {{
      appearance: none;
      background: #f8fafc;
      border: 1px solid var(--line);
      border-radius: 14px;
      color: var(--ink);
      cursor: pointer;
      font: inherit;
      padding: 11px;
      text-align: left;
    }}
    .variant-tab:hover,
    .variant-tab.active {{
      background: #0b1220;
      border-color: #0b1220;
      color: white;
    }}
    .variant-tab span,
    .variant-tab small {{
      display: block;
    }}
    .variant-tab span {{ font-weight: 800; }}
    .variant-tab small {{
      color: var(--muted);
      font-size: 11px;
      margin-top: 2px;
    }}
    .variant-tab.active small {{ color: #cbd5e1; }}
    .variant-stage {{
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #f8fafc;
      min-height: 170px;
      padding: 16px;
    }}
    .variant-content {{ display: none; }}
    .variant-content.active {{ display: block; }}
    .variant-content p {{
      font-size: 15px;
      line-height: 1.65;
      margin-bottom: 0;
      white-space: pre-wrap;
    }}
    .variant-label {{
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 6px;
    }}
    .copy-note {{
      color: var(--muted);
      font-size: 12px;
      margin-top: 10px;
    }}
    @media (max-width: 760px) {{
      .topbar, .card-head, .email-meta {{ display: block; }}
      .dashboard-grid {{ grid-template-columns: 1fr; }}
      .account-list {{ position: static; }}
      .metrics {{ grid-template-columns: 1fr; }}
      .variant-tabs {{ grid-template-columns: 1fr; }}
      .score-block {{ margin-top: 12px; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <header class="topbar">
      <div>
        <div class="eyebrow">ECHO / Human Review Dashboard</div>
        <h1>Today's Critical Accounts</h1>
        <p>Ranked by commitment-outcome mismatch using schema v0.2 fields.</p>
      </div>
      <aside class="notice">
        No email has been sent. A human must review, copy, and send from their own tool.
      </aside>
    </header>
    <section class="summary">{escape(_summary(hospitals, emails))}</section>
    <section class="dashboard-grid">
      <nav class="account-list" aria-label="Hospital accounts">
        <h2>Hospitals</h2>
        {account_rows}
      </nav>
      <section class="cards">
        {cards}
      </section>
    </section>
  </main>
  <script>
    function selectHospital(targetId) {{
      document.querySelectorAll(".account-row").forEach(function(row) {{
        row.classList.toggle("active", row.dataset.target === targetId);
      }});
      document.querySelectorAll(".hospital-card").forEach(function(card) {{
        card.classList.toggle("active", card.id === targetId);
      }});
    }}

    function selectVariant(card, variantName) {{
      card.querySelectorAll(".variant-tab").forEach(function(tab) {{
        tab.classList.toggle("active", tab.dataset.variant === variantName);
      }});
      card.querySelectorAll(".variant-content").forEach(function(panel) {{
        panel.classList.toggle("active", panel.dataset.variantPanel === variantName);
      }});
    }}

    document.querySelectorAll(".account-row").forEach(function(row) {{
      row.addEventListener("click", function() {{
        selectHospital(row.dataset.target);
      }});
    }});

    document.querySelectorAll(".variant-tab").forEach(function(tab) {{
      tab.addEventListener("click", function() {{
        selectVariant(tab.closest(".hospital-card"), tab.dataset.variant);
      }});
    }});
  </script>
</body>
</html>
"""


def generate_dashboard(
    hospitals: list[dict[str, Any]],
    emails: list[dict[str, Any]],
    output_path: str | Path = "dashboard/echo_dashboard.html",
) -> Path:
    """Write a self-contained HTML dashboard and return the output path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_html(hospitals, emails), encoding="utf-8")
    return path
