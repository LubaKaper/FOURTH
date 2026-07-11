"""
Fourth — Account Intelligence for Maternal Health GTM (demo app).

Read-only Streamlit viewer over data/demo_results.json — precomputed
output of the real pipeline over real CMS data. No API keys, no email
sending, no pipeline imports.

Run: streamlit run app.py
"""

import json
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st

RESULTS_PATH = Path(__file__).parent / "data" / "demo_results.json"

REQUIRED_TOP_KEYS = {"generated_at", "state", "accounts"}

TIER_LABELS = {"high": "High", "medium": "Medium", "low": "Low"}

THEMES = {
    "mauve_editorial": {
        "label": "Mauve editorial",
        "background": "#C7A2A6",
        "surface": "#FFF8F4",
        "surface_alt": "#F3E3DF",
        "sidebar": "#D8BFC0",
        "hero": "#C7A2A6",
        "table_header": "#E8D4D0",
        "text": "#111111",
        "muted": "#5C5152",
        "border": "#B88F95",
        "primary": "#7C4C55",
        "primary_soft": "#EAD2D2",
        "secondary": "#F8EFE8",
        "secondary_soft": "#F2E4E0",
        "sage": "#7B8F75",
        "clay": "#A85F55",
        "display_font": "'Arial Black', 'Avenir Next', Avenir, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        "body_font": "'Avenir Next', Avenir, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    },
    "mustard_sea": {
        "label": "Linen, mustard + sea",
        "background": "#F8F3EA",
        "surface": "#FFFDF8",
        "surface_alt": "#EFE6D7",
        "sidebar": "#EAF4F3",
        "hero": "#FFF8EA",
        "table_header": "#E8F0EF",
        "text": "#2F3437",
        "muted": "#6F7472",
        "border": "#E6DDD0",
        "primary": "#D6A83A",
        "primary_soft": "#F2E2AF",
        "secondary": "#8CB9BD",
        "secondary_soft": "#DDEDEF",
        "sage": "#7FA878",
        "clay": "#C56B5C",
        "display_font": "Georgia, 'Iowan Old Style', serif",
        "body_font": "'Avenir Next', Avenir, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    },
    "apricot_teal": {
        "label": "Apricot, clay + teal",
        "background": "#FAF4EF",
        "surface": "#FFFDFC",
        "surface_alt": "#F3E4D9",
        "sidebar": "#F6E7DE",
        "hero": "#FFF1E8",
        "table_header": "#F2DED2",
        "text": "#303332",
        "muted": "#746E69",
        "border": "#EADDD3",
        "primary": "#E8A87C",
        "primary_soft": "#F6D7C4",
        "secondary": "#7DA9A3",
        "secondary_soft": "#DCECE9",
        "sage": "#8EA77C",
        "clay": "#B76E5C",
        "display_font": "'Avenir Next', Avenir, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        "body_font": "'Avenir Next', Avenir, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    },
    "sage_butter": {
        "label": "Sage, butter + blue gray",
        "background": "#F7F5EF",
        "surface": "#FEFCF7",
        "surface_alt": "#ECE7DC",
        "sidebar": "#EEF2E8",
        "hero": "#FBF7E6",
        "table_header": "#E6EBDC",
        "text": "#2E3335",
        "muted": "#7B746D",
        "border": "#E4DED4",
        "primary": "#E4C766",
        "primary_soft": "#F5E9B7",
        "secondary": "#8FAEB8",
        "secondary_soft": "#DFE9EC",
        "sage": "#9CAF88",
        "clay": "#B87563",
        "display_font": "'Gill Sans', 'Avenir Next', Avenir, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        "body_font": "'Avenir Next', Avenir, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    },
}

ANGLE_LABELS = {
    "baby_vs_mother_contrast": "Baby vs. mother contrast",
    "hcahps_care_transition_gap": "HCAHPS care transition gap",
    "state_strength_vs_hospital_lag": "State strength vs. hospital lag",
    "financial_unrealized": "Unrealized RPM billing window",
    "smm_rate_gap": "SMM rate gap",
}

# (measure, provenance, meaning) — data honesty shown to every visitor.
SIGNAL_PROVENANCE = [
    ("HCAHPS care transition star", "Hospital-level",
     "CMS HCAHPS H_COMP_6 star rating for the discharge/transition experience."),
    ("Discharge info received %", "Hospital-level",
     "CMS patient-experience survey measure H_DISCH_HELP_Y_P — % of patients who "
     "reported receiving the information they needed for recovery at discharge. "
     "A discharge-readiness signal, NOT a postpartum visit completion rate."),
    ("Well-baby visit %", "State-level proxy",
     "NY Child Core Set 2023 benchmark (91.5%) applied to every hospital; "
     "flagged well_baby_visit_estimated. No hospital-level source exists yet."),
    ("State postpartum visit average", "State benchmark",
     "CMS Medicaid Adult Core Set PPC-AD, NY 2023: 82.4% postpartum visit completion."),
    ("SMM rate", "Not yet available",
     "PC_07a is 'Not Available' in the current CMS release. The smm_rate_gap "
     "lead angle stays dormant until CMS ships it (roadmap: CDC WONDER)."),
    ("Medicaid extension / disparity / mortality rank", "State-level context",
     "State facts applied identically to all NY hospitals; add flat urgency "
     "context points and cannot differentiate hospitals within NY."),
]


def load_results(path: Path = RESULTS_PATH) -> dict[str, Any]:
    """Load and validate the demo payload. Raises ValueError on bad shape."""
    data = json.loads(path.read_text(encoding="utf-8"))
    missing = REQUIRED_TOP_KEYS - set(data)
    if missing:
        raise ValueError(f"demo_results.json missing keys: {', '.join(sorted(missing))}")
    return data


def _fmt(value: Any, suffix: str = "") -> str:
    return "—" if value is None else f"{value}{suffix}"


def _badge(label: str, kind: str = "neutral") -> str:
    return f'<span class="fourth-badge fourth-badge-{kind}">{escape(label)}</span>'


def _theme_css(theme: dict[str, str]) -> str:
    return f"""
<style>
:root {{
  --fourth-bg: {theme["background"]};
  --fourth-surface: {theme["surface"]};
  --fourth-surface-alt: {theme["surface_alt"]};
  --fourth-sidebar: {theme["sidebar"]};
  --fourth-hero: {theme["hero"]};
  --fourth-table-header: {theme["table_header"]};
  --fourth-text: {theme["text"]};
  --fourth-muted: {theme["muted"]};
  --fourth-border: {theme["border"]};
  --fourth-primary: {theme["primary"]};
  --fourth-primary-soft: {theme["primary_soft"]};
  --fourth-secondary: {theme["secondary"]};
  --fourth-secondary-soft: {theme["secondary_soft"]};
  --fourth-sage: {theme["sage"]};
  --fourth-clay: {theme["clay"]};
  --fourth-display-font: {theme["display_font"]};
  --fourth-body-font: {theme["body_font"]};
}}

.stApp {{
  background:
    radial-gradient(circle at 82% 10%, rgba(255, 248, 244, 0.35), transparent 26rem),
    var(--fourth-bg);
  color: var(--fourth-text);
  font-family: var(--fourth-body-font);
}}

[data-testid="stHeader"] {{
  background: transparent;
  height: 2.6rem;
}}

#MainMenu,
footer {{
  visibility: hidden;
  height: 0;
}}

[data-testid="stSidebar"] {{
  background: var(--fourth-sidebar);
  border-right: 1px solid var(--fourth-border);
  box-shadow: 16px 0 50px rgba(17, 17, 17, 0.05);
}}

[data-testid="stSidebar"] * {{
  color: var(--fourth-text);
}}

[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapsedControl"],
button[title="Close sidebar"],
button[title="Open sidebar"] {{
  visibility: visible !important;
  opacity: 1 !important;
  background: rgba(255, 248, 244, 0.82) !important;
  border: 1px solid var(--fourth-border) !important;
  border-radius: 999px !important;
  color: var(--fourth-text) !important;
  box-shadow: 0 10px 24px rgba(17, 17, 17, 0.12) !important;
}}

[data-testid="stSidebarCollapseButton"] svg,
[data-testid="stSidebarCollapsedControl"] svg,
button[title="Close sidebar"] svg,
button[title="Open sidebar"] svg {{
  fill: var(--fourth-text) !important;
  color: var(--fourth-text) !important;
}}

/* Sidebar nav: hide native radio circles, render options as theme pills. */
[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child {{
  display: none;
}}

[data-testid="stSidebar"] [role="radiogroup"] label {{
  display: flex;
  align-items: center;
  border-radius: 12px;
  border: 1px solid transparent;
  padding: 0.5rem 0.75rem;
  margin-bottom: 0.15rem;
  cursor: pointer;
  transition: background 120ms ease, border-color 120ms ease;
}}

[data-testid="stSidebar"] [role="radiogroup"] label:hover {{
  background: rgba(255, 248, 244, 0.5);
}}

[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{
  background: var(--fourth-surface);
  border-color: var(--fourth-border);
  box-shadow: 0 8px 18px rgba(17, 17, 17, 0.08);
}}

[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p {{
  font-weight: 700;
}}

[data-testid="stSidebar"] [role="radiogroup"] p {{
  color: var(--fourth-text) !important;
  -webkit-text-fill-color: var(--fourth-text) !important;
}}

/* Sidebar section label ("View") */
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {{
  font-size: 0.74rem;
  font-weight: 750;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fourth-muted) !important;
  -webkit-text-fill-color: var(--fourth-muted) !important;
}}

/* Palette popover: trigger reads as a header chip; options match sidebar pills. */
[data-testid="stPopover"] button {{
  background: var(--fourth-surface);
  border: 1px solid var(--fourth-border);
  border-radius: 999px;
  color: var(--fourth-text);
  font-weight: 650;
  box-shadow: 0 10px 24px rgba(17, 17, 17, 0.1);
}}

[data-testid="stPopover"] button:hover {{
  border-color: var(--fourth-primary);
  color: var(--fourth-text);
}}

[data-testid="stPopoverBody"] [role="radiogroup"] label > div:first-child {{
  display: none;
}}

[data-testid="stPopoverBody"] [role="radiogroup"] label {{
  display: flex;
  border-radius: 10px;
  border: 1px solid transparent;
  padding: 0.45rem 0.65rem;
  cursor: pointer;
}}

[data-testid="stPopoverBody"] [role="radiogroup"] label:has(input:checked) {{
  background: var(--fourth-primary-soft);
  border-color: var(--fourth-border);
}}

.block-container {{
  /* Clear Streamlit's fixed header (2.6rem) so the top row — the palette
     popover — is never under its click-intercepting toolbar. */
  padding-top: 3.4rem;
  padding-bottom: 3rem;
  max-width: 1280px;
}}

h1, h2, h3 {{
  color: var(--fourth-text);
  letter-spacing: 0;
  font-family: var(--fourth-display-font);
}}

h1 {{
  font-size: 2.4rem;
  font-weight: 720;
  margin-bottom: 0.1rem;
}}

h2, h3 {{
  font-weight: 680;
}}

p, li, caption, div {{
  letter-spacing: 0;
}}

[data-testid="stMarkdownContainer"] {{
  font-family: var(--fourth-body-font);
}}

[data-testid="stCaptionContainer"], .stMarkdown p {{
  color: var(--fourth-muted);
}}

[data-testid="stMetric"] {{
  background: var(--fourth-surface);
  border: 1px solid var(--fourth-border);
  border-radius: 8px;
  padding: 1rem 1.1rem;
  box-shadow: 0 10px 26px rgba(47, 52, 55, 0.06);
}}

[data-testid="stMetricLabel"] p {{
  color: var(--fourth-muted);
  font-size: 0.82rem;
}}

[data-testid="stMetricValue"] {{
  color: var(--fourth-text);
}}

div[data-testid="stSelectbox"] > div,
div[data-testid="stRadio"] > div {{
  color: var(--fourth-text);
}}

.stCodeBlock, pre {{
  border: 1px solid var(--fourth-border);
  border-radius: 8px;
}}

hr {{
  border-color: var(--fourth-border);
}}

.fourth-hero {{
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 0.95fr) minmax(350px, 0.8fr);
  min-height: 420px;
  gap: 2rem;
  align-items: center;
  background: var(--fourth-hero);
  border: 1px solid rgba(17, 17, 17, 0.08);
  border-radius: 8px;
  padding: 2.1rem 2.2rem;
  margin: 0.1rem 0 2rem;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(17, 17, 17, 0.12);
}}

.fourth-hero::before {{
  content: "";
  position: absolute;
  inset: auto 0 0 0;
  height: 38%;
  background: linear-gradient(180deg, transparent, rgba(255, 248, 244, 0.22));
  pointer-events: none;
}}

.fourth-hero h1 {{
  position: relative;
  margin: 0;
  max-width: 760px;
  font-family: var(--fourth-display-font);
  /* Max sized so "INTELLIGENCE." fits the text column without clipping
     behind the device visual at any width. */
  font-size: clamp(2.3rem, 3.5vw, 4rem);
  font-weight: 900;
  line-height: 1;
  text-transform: uppercase;
  color: var(--fourth-text);
  word-break: keep-all;
  overflow-wrap: normal;
  hyphens: none;
  z-index: 1;
}}

.fourth-eyebrow {{
  position: relative;
  color: var(--fourth-text);
  font-size: 0.78rem;
  font-weight: 750;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 1.15rem;
  z-index: 1;
}}

.fourth-hero-copy {{
  position: relative;
  color: rgba(17, 17, 17, 0.7);
  max-width: 620px;
  margin: 1.2rem 0 0;
  font-size: 1.06rem;
  line-height: 1.55;
  z-index: 1;
}}

.fourth-visual {{
  position: relative;
  min-height: 330px;
  z-index: 1;
}}

.fourth-device {{
  position: absolute;
  width: 190px;
  min-height: 270px;
  border-radius: 28px;
  background: var(--fourth-surface);
  border: 8px solid #111111;
  box-shadow: 0 20px 44px rgba(17, 17, 17, 0.24);
  padding: 1.1rem 0.9rem;
}}

.fourth-device-main {{
  right: 118px;
  top: 20px;
}}

.fourth-device-side {{
  right: 6px;
  top: 64px;
  transform: rotate(13deg);
  opacity: 0.95;
}}

.fourth-device-tag {{
  display: inline-flex;
  border-radius: 999px;
  background: var(--fourth-primary-soft);
  color: var(--fourth-primary);
  font-size: 0.68rem;
  padding: 0.18rem 0.5rem;
  margin-bottom: 0.8rem;
  font-weight: 760;
}}

.fourth-device-title {{
  font-weight: 850;
  color: var(--fourth-text);
  font-size: 1.1rem;
  line-height: 1.1;
  margin-bottom: 0.9rem;
}}

.fourth-device-line {{
  height: 0.5rem;
  border-radius: 999px;
  background: var(--fourth-surface-alt);
  margin: 0.44rem 0;
}}

.fourth-device-line.short {{
  width: 58%;
}}

.fourth-mini-controls {{
  position: absolute;
  right: 108px;
  bottom: 6px;
  display: flex;
  gap: 0.62rem;
}}

.fourth-mini-control {{
  min-width: 76px;
  height: 58px;
  border-radius: 16px;
  background: var(--fourth-primary);
  color: var(--fourth-surface);
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 0 0.74rem;
  box-shadow: 0 12px 24px rgba(17, 17, 17, 0.18);
}}

.fourth-mini-value {{
  font-size: 1rem;
  line-height: 1;
  font-weight: 900;
}}

.fourth-mini-label {{
  color: rgba(255, 248, 244, 0.72);
  font-size: 0.58rem;
  line-height: 1;
  margin-top: 0.26rem;
  text-transform: uppercase;
}}

.fourth-stat-strip {{
  display: flex;
  gap: 0.7rem;
  margin-top: 1.35rem;
  flex-wrap: wrap;
}}

.fourth-stat {{
  min-width: 106px;
  background: rgba(255, 248, 244, 0.66);
  border: 1px solid rgba(17, 17, 17, 0.12);
  border-radius: 18px;
  padding: 0.82rem 0.9rem;
}}

.fourth-stat-value {{
  color: var(--fourth-text);
  font-size: 1.25rem;
  font-weight: 780;
  line-height: 1.1;
}}

.fourth-stat-label {{
  color: var(--fourth-muted);
  font-size: 0.72rem;
  text-transform: uppercase;
  margin-top: 0.2rem;
}}

.fourth-kicker {{
  color: rgba(17, 17, 17, 0.62);
  font-size: 0.9rem;
  margin: 0 0 1.2rem 0;
}}

.fourth-section-title {{
  color: var(--fourth-text);
  font-family: var(--fourth-display-font);
  font-size: clamp(2rem, 3vw, 3.3rem);
  line-height: 0.98;
  text-transform: uppercase;
  margin: 0 0 0.65rem;
}}

.fourth-board {{
  display: grid;
  gap: 0.82rem;
}}

.fourth-account-row {{
  display: grid;
  grid-template-columns: 54px minmax(220px, 1.2fr) 98px 110px minmax(180px, 0.9fr) 118px 104px;
  gap: 1rem;
  align-items: center;
  background: var(--fourth-surface);
  border: 1px solid rgba(17, 17, 17, 0.1);
  border-radius: 22px;
  padding: 1rem 1.1rem;
  box-shadow: 0 14px 34px rgba(17, 17, 17, 0.08);
}}

.fourth-board-head {{
  background: rgba(255, 248, 244, 0.42);
  box-shadow: none;
  border-color: transparent;
  padding-top: 0.45rem;
  padding-bottom: 0.45rem;
  color: rgba(17, 17, 17, 0.58);
  font-size: 0.72rem;
  font-weight: 850;
  text-transform: uppercase;
}}

.fourth-table {{
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  overflow: hidden;
  border: 1px solid var(--fourth-border);
  border-radius: 8px;
  background: var(--fourth-surface);
  box-shadow: 0 12px 30px rgba(47, 52, 55, 0.06);
}}

.fourth-table th {{
  text-align: left;
  font-size: 0.76rem;
  text-transform: uppercase;
  color: var(--fourth-muted);
  background: var(--fourth-table-header);
  padding: 0.76rem 0.9rem;
  border-bottom: 1px solid var(--fourth-border);
}}

.fourth-table td {{
  color: var(--fourth-text);
  padding: 0.86rem 0.9rem;
  border-bottom: 1px solid var(--fourth-border);
  vertical-align: top;
}}

.fourth-table tr:last-child td {{
  border-bottom: none;
}}

.fourth-rank {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 16px;
  background: var(--fourth-primary);
  border: 1px solid rgba(17, 17, 17, 0.12);
  color: var(--fourth-surface);
  font-size: 1rem;
  font-weight: 900;
}}

.fourth-hospital-name {{
  font-weight: 650;
  color: var(--fourth-text);
}}

.fourth-score {{
  color: var(--fourth-text);
  font-size: 1.28rem;
  font-weight: 900;
}}

.fourth-muted {{
  color: var(--fourth-muted);
}}

.fourth-badge {{
  display: inline-flex;
  align-items: center;
  min-height: 1.55rem;
  padding: 0.18rem 0.56rem;
  border-radius: 18px;
  border: 1px solid var(--fourth-border);
  font-size: 0.78rem;
  line-height: 1.1;
  white-space: nowrap;
}}

.fourth-badge-high {{
  background: rgba(197, 107, 92, 0.13);
  color: var(--fourth-clay);
  border-color: rgba(197, 107, 92, 0.28);
}}

.fourth-badge-medium {{
  background: var(--fourth-primary-soft);
  color: #755F20;
  border-color: rgba(214, 168, 58, 0.34);
}}

.fourth-badge-low {{
  background: rgba(127, 168, 120, 0.16);
  color: #5F7F5B;
  border-color: rgba(127, 168, 120, 0.32);
}}

.fourth-badge-blue, .fourth-badge-state {{
  background: var(--fourth-secondary-soft);
  color: #3F6970;
  border-color: rgba(140, 185, 189, 0.36);
}}

.fourth-badge-sage, .fourth-badge-hospital {{
  background: rgba(127, 168, 120, 0.15);
  color: #5C7857;
  border-color: rgba(127, 168, 120, 0.3);
}}

.fourth-badge-neutral, .fourth-badge-missing {{
  background: rgba(111, 116, 114, 0.09);
  color: var(--fourth-muted);
}}

.fourth-detail-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.75rem;
  margin: 0.6rem 0 1.2rem;
}}

.fourth-detail-item {{
  background: var(--fourth-surface);
  border: 1px solid var(--fourth-border);
  border-radius: 8px;
  padding: 0.84rem 0.92rem;
}}

.fourth-detail-label {{
  color: var(--fourth-muted);
  font-size: 0.76rem;
  text-transform: uppercase;
  margin-bottom: 0.32rem;
}}

.fourth-detail-value {{
  color: var(--fourth-text);
  font-size: 1rem;
  font-weight: 650;
}}

/* Between phone and full desktop the device visual crowds the headline —
   drop it earlier than the full mobile breakpoint. */
@media (max-width: 1150px) {{
  .fourth-hero {{
    grid-template-columns: 1fr;
    min-height: auto;
  }}

  .fourth-visual {{
    display: none;
  }}
}}

@media (max-width: 760px) {{
  .block-container {{
    padding-left: 1rem;
    padding-right: 1rem;
  }}

  h1 {{
    font-size: 2rem;
  }}

  .fourth-hero {{
    grid-template-columns: 1fr;
    padding: 1.1rem;
    min-height: auto;
  }}

  .fourth-stat-strip {{
    display: grid;
    grid-template-columns: 1fr;
  }}

  .fourth-visual {{
    display: none;
  }}

  .fourth-account-row {{
    grid-template-columns: 40px 1fr;
    gap: 0.75rem;
  }}

  .fourth-account-row > div:nth-child(n + 3) {{
    grid-column: 2;
  }}

  .fourth-table {{
    display: block;
    overflow-x: auto;
  }}
}}
</style>
"""


def apply_theme(theme_key: str) -> None:
    st.markdown(_theme_css(THEMES[theme_key]), unsafe_allow_html=True)


def _markdown_table(rows: list[dict[str, Any]]) -> str:
    """Render a GitHub-style markdown table from a list of dicts.

    Column order follows the first row's key order; pipes are escaped and
    newlines collapsed so a value cannot break the table structure. Used
    instead of st.dataframe(): the small tables here don't need
    interactivity, and st.dataframe()'s DataFrame/Arrow native conversion
    segfaulted the interpreter in this environment on any script-rerun
    thread after the first (see commit message).
    """
    if not rows:
        return ""
    headers = list(rows[0].keys())

    def esc(value: Any) -> str:
        return " ".join(str(value).replace("|", "\\|").split())

    lines = [
        "| " + " | ".join(esc(h) for h in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(esc(row.get(h, "")) for h in headers) + " |")
    return "\n".join(lines)


def _html_table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{cell}</td>" for cell in row)
        body_rows.append(f"<tr>{cells}</tr>")
    return (
        '<table class="fourth-table">'
        f"<thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )


def render_header(data: dict[str, Any]) -> None:
    account_count = len(data.get("accounts", []))
    email_count = sum(1 for account in data.get("accounts", []) if account.get("email"))
    state = escape(str(data.get("state", "NY")))
    st.markdown(
        f"""
<section class="fourth-hero">
  <div>
    <div class="fourth-eyebrow">Fourth / {state} maternal health GTM</div>
    <h1>Maternal health<br>account intelligence.</h1>
    <p class="fourth-hero-copy">
      CMS account signals, postpartum context, and claim-validated Babyscripts drafts
      in one review workspace.
    </p>
    <div class="fourth-stat-strip">
      <div class="fourth-stat">
        <div class="fourth-stat-value">{account_count}</div>
        <div class="fourth-stat-label">accounts</div>
      </div>
      <div class="fourth-stat">
        <div class="fourth-stat-value">{email_count}</div>
        <div class="fourth-stat-label">drafts</div>
      </div>
      <div class="fourth-stat">
        <div class="fourth-stat-value">CMS</div>
        <div class="fourth-stat-label">grounded</div>
      </div>
    </div>
  </div>
  <div class="fourth-visual" aria-hidden="true">
    <div class="fourth-device fourth-device-side">
      <div class="fourth-device-tag">Review</div>
      <div class="fourth-device-title">Claim check</div>
      <div class="fourth-device-line"></div>
      <div class="fourth-device-line short"></div>
      <div class="fourth-device-line"></div>
      <div class="fourth-device-line short"></div>
    </div>
    <div class="fourth-device fourth-device-main">
      <div class="fourth-device-tag">Priority</div>
      <div class="fourth-device-title">Nassau University Medical Center</div>
      <div class="fourth-device-line"></div>
      <div class="fourth-device-line"></div>
      <div class="fourth-device-line short"></div>
      <div class="fourth-device-line"></div>
    </div>
    <div class="fourth-mini-controls">
      <div class="fourth-mini-control"><span class="fourth-mini-value">77</span><span class="fourth-mini-label">gap score</span></div>
      <div class="fourth-mini-control"><span class="fourth-mini-value">BF</span><span class="fourth-mini-label">CMS flag</span></div>
      <div class="fourth-mini-control"><span class="fourth-mini-value">NY</span><span class="fourth-mini-label">market</span></div>
    </div>
  </div>
</section>
""",
        unsafe_allow_html=True,
    )


def _breakdown_panel(title: str, values: dict[str, Any] | None) -> str:
    if not values:
        return ""
    rows = []
    for label, raw_value in values.items():
        value = float(raw_value or 0)
        width = max(4, min(100, value * 4))
        readable = label.replace("_", " ").title()
        rows.append(
            '<div class="fourth-detail-item">'
            f'<div class="fourth-detail-label">{escape(readable)}</div>'
            f'<div class="fourth-detail-value">{escape(str(raw_value))}</div>'
            '<div style="height: 6px; margin-top: 0.62rem; border-radius: 999px; '
            'background: var(--fourth-surface-alt); overflow: hidden;">'
            f'<div style="width: {width}%; height: 100%; background: var(--fourth-secondary);"></div>'
            '</div></div>'
        )
    return (
        f'<div class="fourth-detail-label" style="margin: 0.2rem 0 0.65rem;">{escape(title)}</div>'
        f'<div class="fourth-detail-grid">{"".join(rows)}</div>'
    )


def render_accounts(data: dict[str, Any]) -> None:
    st.markdown(f'<h2 class="fourth-section-title">Top accounts — {escape(data["state"])}</h2>', unsafe_allow_html=True)
    st.markdown(
        f'<p class="fourth-kicker">Generated {escape(data["generated_at"])} from CMS public data.</p>',
        unsafe_allow_html=True,
    )
    rows = [
        '<div class="fourth-account-row fourth-board-head">'
        "<div></div><div>Hospital</div><div>Gap</div><div>Urgency</div>"
        "<div>Lead angle</div><div>Confidence</div><div>Email</div></div>"
    ]
    for idx, account in enumerate(data["accounts"], start=1):
        rows.append(
            '<div class="fourth-account-row">'
            f'<div><span class="fourth-rank">{idx}</span></div>'
            f'<div class="fourth-hospital-name">{escape(account["facility_name"])}</div>'
            f'<div class="fourth-score">{escape(str(account["gap_score"]))}</div>'
            f'<div>{_badge(TIER_LABELS.get(account["urgency_tier"], account["urgency_tier"]), account["urgency_tier"])}</div>'
            f'<div>{escape(ANGLE_LABELS.get(account["lead_angle"], account["lead_angle"]))}</div>'
            f'<div>{_badge(str(account["data_confidence"]).title(), "sage" if account["data_confidence"] == "high" else "neutral")}</div>'
            f'<div>{_badge("Drafted", "blue") if account.get("email") else "<span class=\"fourth-muted\">Not drafted</span>"}</div>'
            "</div>"
        )
    st.markdown(f'<div class="fourth-board">{"".join(rows)}</div>', unsafe_allow_html=True)


def render_account_detail(data: dict[str, Any]) -> None:
    names = [a["facility_name"] for a in data["accounts"]]
    chosen = st.selectbox("Account", names)
    account = next(a for a in data["accounts"] if a["facility_name"] == chosen)

    left, right = st.columns(2)
    with left:
        st.metric("Gap score", account["gap_score"])
        st.markdown(
            '<div class="fourth-detail-grid">'
            '<div class="fourth-detail-item"><div class="fourth-detail-label">Urgency</div>'
            f'<div class="fourth-detail-value">{_badge(TIER_LABELS.get(account["urgency_tier"], account["urgency_tier"]), account["urgency_tier"])}</div></div>'
            '<div class="fourth-detail-item"><div class="fourth-detail-label">Lead angle</div>'
            f'<div class="fourth-detail-value">{escape(ANGLE_LABELS.get(account["lead_angle"], account["lead_angle"]))}</div></div>'
            "</div>",
            unsafe_allow_html=True,
        )
        if account.get("email"):
            st.markdown(
                '<div class="fourth-detail-item"><div class="fourth-detail-label">Angle reason</div>'
                f'<div class="fourth-detail-value">{escape(account["email"]["angle_reason"])}</div></div>',
                unsafe_allow_html=True,
            )
    with right:
        st.markdown(
            _breakdown_panel("Gap breakdown", account.get("gap_breakdown"))
            + _breakdown_panel("Urgency breakdown", account.get("urgency_breakdown")),
            unsafe_allow_html=True,
        )

    st.divider()
    st.write("**Signals** (provenance in Methodology)")
    st.markdown(_html_table(
        ["Signal", "Value"],
        [
            [escape("Discharge info received (hospital)"), escape(_fmt(account.get("discharge_info_pct"), "%"))],
            [escape("Care transition star (hospital)"), escape(_fmt(account.get("hcahps_care_transition_star"), "/5"))],
            [escape("Well-baby visits (state proxy)"), escape(_fmt(account.get("well_baby_visit_pct"), "%"))],
            [escape("State postpartum visit avg"), escape(_fmt(account.get("state_postpartum_avg"), "%"))],
            [escape("SMM rate"), escape(_fmt(account.get("smm_rate")))],
            [escape("Readmission penalty"), escape(_fmt(account.get("readmission_penalty")))],
        ],
    ), unsafe_allow_html=True)

    st.divider()
    email = account.get("email")
    if not email:
        st.info("No email drafted for this account (below threshold or low confidence).")
        return
    st.write(f"**To:** {email['recipient_role']}  ·  **Status:** `{email['status']}`  ·  "
             f"**Claim validation:** `{email['claim_validation']}`")
    st.write(f"**Subject:** {email['subject']}")
    st.code(email["email_body"], language=None)


def render_methodology() -> None:
    st.subheader("How Fourth works")
    st.markdown(
        """
```text
commitment_ingester → outcome_scorer → gap_calculator → urgency_ranker
      → account_selector → outbound_generator → approvals → send controls
```

**Gap score (0–100), three layers:** commitment strength (0–25, CMS
Birthing-Friendly designation + MMSM participation) · outcome gap (0–50,
discharge-info lag vs. state benchmark, HCAHPS care transition, readmission
penalty, SMM when available) · urgency context (0–25, state-level factors).

**Claim validation.** The LLM drafts only the email body. Deterministic code
then rejects any draft containing a percentage not within 1 point of a real
source field, any star rating that doesn't match the hospital's HCAHPS data,
unsupported claim language, or the internal gap score. Rejected drafts fall
back to deterministic templates. The LLM cannot introduce a number this app
displays.

**Send safety.** Emails hold at `pending_review` for human review. The send
path (not exposed here) enforces an approval gate, a final send gate, a
30-day dedup cooldown, and an append-only audit log with body hashes.
        """
    )
    st.subheader("Signal provenance — what's real, what's proxy")
    rows = []
    for signal, provenance, meaning in SIGNAL_PROVENANCE:
        if provenance == "Hospital-level":
            badge = _badge(provenance, "hospital")
        elif "State" in provenance:
            badge = _badge(provenance, "state")
        elif provenance == "Not yet available":
            badge = _badge(provenance, "missing")
        else:
            badge = _badge(provenance, "neutral")
        rows.append([escape(signal), badge, escape(meaning)])
    st.markdown(_html_table(["Signal", "Provenance", "Meaning"], rows), unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(page_title="Fourth — Account Intelligence", page_icon="🏥", layout="wide")
    if "palette" not in st.session_state:
        st.session_state.palette = next(iter(THEMES))
    apply_theme(st.session_state.palette)

    if not RESULTS_PATH.exists():
        st.warning("Demo data not generated yet. Run:")
        st.code(".venv/bin/python scripts/export_demo_results.py")
        st.stop()
    try:
        data = load_results()
    except (ValueError, json.JSONDecodeError) as exc:
        st.error(f"demo_results.json is invalid: {exc}")
        st.stop()

    _, palette_col = st.columns([0.82, 0.18])
    with palette_col:
        with st.popover("🎨 Palette"):
            st.radio(
                "Palette",
                options=list(THEMES),
                format_func=lambda key: THEMES[key]["label"],
                key="palette",
                label_visibility="collapsed",
            )

    render_header(data)
    view = st.sidebar.radio("View", ["Ranked accounts", "Account detail", "Methodology"])
    if view == "Ranked accounts":
        render_accounts(data)
    elif view == "Account detail":
        render_account_detail(data)
    else:
        render_methodology()


if __name__ == "__main__":
    main()
