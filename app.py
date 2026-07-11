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
    "maternal_intelligence": {
        "label": "Maternal intelligence",
        "background": "#f7ebe9",
        "surface": "#ffffff",
        "surface_alt": "#f3ecec",
        "sidebar": "#f9f2f1",
        "hero": "#6d4b53",
        "hero_ink": "#f3c7cf",
        "hero_body": "rgba(255, 248, 247, 0.82)",
        "table_header": "#f0e4e2",
        "text": "#1e1b1b",
        "muted": "#6e6162",
        "border": "#e7dad8",
        "primary": "#593a41",
        "primary_soft": "#f0dede",
        "secondary": "#c48f99",
        "secondary_soft": "#f6e3e6",
        "sage": "#8aa382",
        "clay": "#b3705f",
        "display_font": "'Plus Jakarta Sans', 'Avenir Next', -apple-system, sans-serif",
        "body_font": "'Plus Jakarta Sans', 'Avenir Next', -apple-system, sans-serif",
    },
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
    hero_ink = theme.get("hero_ink", theme["text"])
    hero_body = theme.get("hero_body", theme["muted"])
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;700;800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0&display=swap');

:root {{
  --fourth-bg: {theme["background"]};
  --fourth-surface: {theme["surface"]};
  --fourth-surface-alt: {theme["surface_alt"]};
  --fourth-sidebar: {theme["sidebar"]};
  --fourth-hero: {theme["hero"]};
  --fourth-hero-ink: {hero_ink};
  --fourth-hero-body: {hero_body};
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

.material-symbols-outlined {{
  font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
  display: inline-block;
  line-height: 1;
  vertical-align: middle;
}}

.stApp {{
  background: var(--fourth-bg);
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

/* ── Sidebar: tonal panel, pill nav, no shadows ─────────────────────── */
[data-testid="stSidebar"] {{
  background: var(--fourth-sidebar);
  border-right: 1px solid var(--fourth-border);
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
  background: var(--fourth-surface) !important;
  border: 1px solid var(--fourth-border) !important;
  border-radius: 999px !important;
  color: var(--fourth-text) !important;
  box-shadow: none !important;
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
  padding: 0.55rem 0.8rem;
  margin-bottom: 0.15rem;
  cursor: pointer;
  transition: background 120ms ease, border-color 120ms ease;
}}

[data-testid="stSidebar"] [role="radiogroup"] label:hover {{
  background: var(--fourth-surface-alt);
}}

[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{
  background: var(--fourth-primary);
  border-color: var(--fourth-primary);
}}

[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p {{
  color: var(--fourth-surface) !important;
  -webkit-text-fill-color: var(--fourth-surface) !important;
  font-weight: 700;
}}

[data-testid="stSidebar"] [role="radiogroup"] p {{
  color: var(--fourth-text) !important;
  -webkit-text-fill-color: var(--fourth-text) !important;
  font-family: var(--fourth-body-font);
}}

/* Sidebar section label ("View") */
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {{
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--fourth-muted) !important;
  -webkit-text-fill-color: var(--fourth-muted) !important;
}}

/* ── Palette popover ────────────────────────────────────────────────── */
[data-testid="stPopover"] button {{
  background: var(--fourth-surface);
  border: 1px solid var(--fourth-border);
  border-radius: 999px;
  color: var(--fourth-text);
  box-shadow: none;
}}

[data-testid="stPopover"] button p {{
  font-family: var(--fourth-body-font);
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--fourth-text);
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

/* ── Layout & type ──────────────────────────────────────────────────── */
.block-container {{
  /* Clear Streamlit's fixed header (2.6rem) so the top row — the palette
     popover — is never under its click-intercepting toolbar. */
  padding-top: 3.4rem;
  padding-bottom: 3rem;
  max-width: 1240px;
}}

h1, h2, h3 {{
  color: var(--fourth-text);
  font-family: var(--fourth-display-font);
  letter-spacing: -0.02em;
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
  border-radius: 16px;
  padding: 1rem 1.1rem;
  box-shadow: none;
}}

[data-testid="stMetricLabel"] p {{
  color: var(--fourth-muted);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}}

[data-testid="stMetricValue"] {{
  color: var(--fourth-text);
  font-family: var(--fourth-display-font);
}}

div[data-testid="stSelectbox"] > div,
div[data-testid="stRadio"] > div {{
  color: var(--fourth-text);
}}

.stCodeBlock, pre {{
  border: 1px solid var(--fourth-border);
  border-radius: 12px;
}}

hr {{
  border-color: var(--fourth-border);
}}

/* ── Hero: deep plum block, tonal, no device mockups ────────────────── */
.fourth-hero {{
  background: var(--fourth-hero);
  border-radius: 24px;
  padding: 3rem 3.2rem 2.8rem;
  margin: 0.1rem 0 1rem;
}}

.fourth-eyebrow {{
  display: inline-flex;
  background: rgba(255, 248, 247, 0.14);
  color: var(--fourth-hero-ink);
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  border-radius: 999px;
  padding: 0.4rem 0.9rem;
  margin-bottom: 1.3rem;
}}

.fourth-hero h1 {{
  margin: 0;
  max-width: 640px;
  font-family: var(--fourth-display-font);
  font-size: clamp(2.1rem, 3.4vw, 3.2rem);
  font-weight: 800;
  line-height: 1.1;
  letter-spacing: -0.02em;
  text-transform: none;
  color: var(--fourth-hero-ink);
}}

/* Beat the global ".stMarkdown p" muted-color rule on hero copy. */
.fourth-hero p.fourth-hero-copy {{
  color: var(--fourth-hero-body);
  max-width: 560px;
  margin: 1.1rem 0 1.6rem;
  font-size: 1.05rem;
  line-height: 1.6;
}}

.fourth-btn {{
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  border-radius: 999px;
  padding: 0.7rem 1.4rem;
  font-size: 0.92rem;
  font-weight: 700;
  text-decoration: none !important;
  margin-right: 0.7rem;
  transition: transform 120ms ease;
}}

.fourth-btn:hover {{
  transform: translateY(-2px);
}}

.fourth-btn-filled {{
  background: var(--fourth-primary-soft);
  color: var(--fourth-primary) !important;
}}

.fourth-btn-ghost {{
  border: 2px solid rgba(255, 248, 247, 0.4);
  color: var(--fourth-hero-ink) !important;
}}

/* ── Stat cards: flat, icon chip, tonal ─────────────────────────────── */
.fourth-stat-row {{
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin: 0 0 1.6rem;
}}

.fourth-stat-card {{
  background: var(--fourth-surface);
  border-radius: 24px;
  padding: 24px;
  transition: transform 200ms ease;
}}

.fourth-stat-card:hover {{
  transform: translateY(-2px);
}}

.fourth-icon-chip {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 14px;
  background: var(--fourth-primary-soft);
  color: var(--fourth-primary);
  margin-bottom: 0.9rem;
}}

.fourth-stat-label {{
  color: var(--fourth-muted);
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}}

.fourth-stat-value {{
  color: var(--fourth-text);
  font-family: var(--fourth-display-font);
  font-size: 2.3rem;
  font-weight: 800;
  line-height: 1.15;
}}

.fourth-stat-note {{
  color: var(--fourth-muted);
  font-size: 0.84rem;
  margin-top: 0.25rem;
}}

/* ── Section headings ───────────────────────────────────────────────── */
.fourth-section-title {{
  color: var(--fourth-text);
  font-family: var(--fourth-display-font);
  font-size: 1.55rem;
  font-weight: 800;
  letter-spacing: -0.01em;
  text-transform: none;
  line-height: 1.2;
  margin: 0 0 0.35rem;
}}

.fourth-kicker {{
  color: var(--fourth-muted);
  font-size: 0.88rem;
  margin: 0 0 1.1rem 0;
}}

/* ── Cards & account board ──────────────────────────────────────────── */
.fourth-card {{
  background: var(--fourth-surface);
  border-radius: 24px;
  padding: 24px;
}}

.fourth-board {{
  display: grid;
  gap: 4px;
}}

.fourth-account-row {{
  display: grid;
  grid-template-columns: 52px minmax(200px, 1.25fr) 76px 104px minmax(160px, 0.9fr) 104px 100px;
  gap: 0.9rem;
  align-items: center;
  background: var(--fourth-surface);
  border-radius: 16px;
  padding: 0.85rem 1rem;
  transition: background 120ms ease;
}}

.fourth-account-row:hover {{
  background: var(--fourth-surface-alt);
}}

.fourth-board-head {{
  background: transparent;
  padding-top: 0.4rem;
  padding-bottom: 0.4rem;
  color: var(--fourth-muted);
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}}

.fourth-rank {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.4rem;
  height: 2.4rem;
  border-radius: 999px;
  background: var(--fourth-primary);
  color: var(--fourth-surface);
  font-size: 0.95rem;
  font-weight: 800;
}}

.fourth-hospital-name {{
  font-weight: 700;
  color: var(--fourth-text);
}}

.fourth-score {{
  color: var(--fourth-text);
  font-family: var(--fourth-display-font);
  font-size: 1.2rem;
  font-weight: 800;
}}

.fourth-muted {{
  color: var(--fourth-muted);
}}

/* ── Badges: pill, low-vibrancy ─────────────────────────────────────── */
.fourth-badge {{
  display: inline-flex;
  align-items: center;
  min-height: 1.55rem;
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
  border: none;
  font-size: 0.76rem;
  font-weight: 700;
  line-height: 1.1;
  white-space: nowrap;
}}

.fourth-badge-high {{
  background: #f6ddd6;
  color: #8f4436;
}}

.fourth-badge-medium {{
  background: var(--fourth-primary-soft);
  color: var(--fourth-primary);
}}

.fourth-badge-low {{
  background: #e4eadf;
  color: #5f7f5b;
}}

.fourth-badge-blue, .fourth-badge-state {{
  background: var(--fourth-secondary-soft);
  color: #6b5257;
}}

.fourth-badge-sage, .fourth-badge-hospital {{
  background: #e3e9de;
  color: #5c7857;
}}

.fourth-badge-neutral, .fourth-badge-missing {{
  background: var(--fourth-surface-alt);
  color: var(--fourth-muted);
}}

/* ── Tables (signals, provenance) ───────────────────────────────────── */
.fourth-table {{
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  overflow: hidden;
  border-radius: 16px;
  background: var(--fourth-surface);
}}

.fourth-table th {{
  text-align: left;
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--fourth-muted);
  background: var(--fourth-table-header);
  padding: 0.76rem 0.95rem;
}}

.fourth-table td {{
  color: var(--fourth-text);
  padding: 0.86rem 0.95rem;
  border-bottom: 1px solid var(--fourth-surface-alt);
  vertical-align: top;
}}

.fourth-table tr:last-child td {{
  border-bottom: none;
}}

/* ── Detail grid ────────────────────────────────────────────────────── */
.fourth-detail-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.75rem;
  margin: 0.6rem 0 1.2rem;
}}

.fourth-detail-item {{
  background: var(--fourth-surface);
  border-radius: 16px;
  padding: 0.9rem 1rem;
}}

.fourth-detail-label {{
  color: var(--fourth-muted);
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: 0.32rem;
}}

.fourth-detail-value {{
  color: var(--fourth-text);
  font-size: 1rem;
  font-weight: 700;
}}

/* ── Provenance donut ───────────────────────────────────────────────── */
.fourth-donut-wrap {{
  display: flex;
  justify-content: center;
  margin: 1rem 0 1.2rem;
}}

.fourth-donut {{
  width: 168px;
  height: 168px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}}

.fourth-donut-hole {{
  width: 118px;
  height: 118px;
  border-radius: 50%;
  background: var(--fourth-surface);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}}

.fourth-donut-value {{
  font-family: var(--fourth-display-font);
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--fourth-text);
  line-height: 1;
}}

.fourth-donut-label {{
  color: var(--fourth-muted);
  font-size: 0.62rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-top: 0.3rem;
}}

.fourth-legend-row {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.42rem 0;
  font-size: 0.86rem;
  color: var(--fourth-text);
}}

.fourth-legend-dot {{
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 0.5rem;
}}

/* ── Responsive ─────────────────────────────────────────────────────── */
@media (max-width: 1150px) {{
  .fourth-stat-row {{
    grid-template-columns: 1fr;
  }}
}}

@media (max-width: 760px) {{
  .block-container {{
    padding-left: 1rem;
    padding-right: 1rem;
  }}

  .fourth-hero {{
    padding: 1.4rem 1.3rem;
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
    accounts = data.get("accounts", [])
    account_count = len(accounts)
    email_count = sum(1 for account in accounts if account.get("email"))
    validated_count = sum(
        1
        for account in accounts
        if account.get("email") and account["email"].get("claim_validation") == "passed"
    )
    validated_pct = f"{round(100 * validated_count / email_count)}%" if email_count else "—"
    state = escape(str(data.get("state", "NY")))

    st.markdown(
        f"""
<section class="fourth-hero">
  <div class="fourth-eyebrow">Fourth / {state} maternal health GTM</div>
  <h1>Account intelligence that puts maternal care first.</h1>
  <p class="fourth-hero-copy">
    CMS account signals, postpartum context, and claim-validated Babyscripts
    drafts in one review workspace. Every number traces to a public source.
  </p>
  <div>
    <a class="fourth-btn fourth-btn-filled" href="https://github.com/LubaKaper/FOURTH" target="_blank">View the pipeline</a>
    <a class="fourth-btn fourth-btn-ghost" href="https://data.cms.gov/provider-data/" target="_blank">CMS data sources</a>
  </div>
</section>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
<div class="fourth-stat-row">
  <div class="fourth-stat-card">
    <div class="fourth-icon-chip"><span class="material-symbols-outlined">apartment</span></div>
    <div class="fourth-stat-label">Ranked accounts</div>
    <div class="fourth-stat-value">{account_count}</div>
    <div class="fourth-stat-note">CMS Birthing-Friendly hospitals in {state}.</div>
  </div>
  <div class="fourth-stat-card">
    <div class="fourth-icon-chip"><span class="material-symbols-outlined">edit_note</span></div>
    <div class="fourth-stat-label">Drafts pending review</div>
    <div class="fourth-stat-value">{email_count}</div>
    <div class="fourth-stat-note">Every draft waits for a human. Nothing auto-sends.</div>
  </div>
  <div class="fourth-stat-card">
    <div class="fourth-icon-chip"><span class="material-symbols-outlined">verified</span></div>
    <div class="fourth-stat-label">Claims validated</div>
    <div class="fourth-stat-value">{validated_pct}</div>
    <div class="fourth-stat-note">Drafted emails that passed source-grounding checks.</div>
  </div>
</div>
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


def _initials(name: str) -> str:
    words = [w for w in name.split() if w[:1].isalpha()]
    return (words[0][0] + (words[1][0] if len(words) > 1 else "")).upper() if words else "–"


def _provenance_card() -> str:
    """Signal-provenance donut — the honest version of a 'health heatmap'.

    Counts come from SIGNAL_PROVENANCE so the chart always matches the
    methodology table.
    """
    hospital = sum(1 for _, p, _ in SIGNAL_PROVENANCE if p == "Hospital-level")
    state = sum(1 for _, p, _ in SIGNAL_PROVENANCE if "State" in p)
    missing = sum(1 for _, p, _ in SIGNAL_PROVENANCE if p == "Not yet available")
    total = hospital + state + missing
    h_pct = round(100 * hospital / total)
    s_pct = round(100 * state / total)
    donut = (
        f"conic-gradient(var(--fourth-primary) 0% {h_pct}%, "
        f"var(--fourth-secondary) {h_pct}% {h_pct + s_pct}%, "
        f"var(--fourth-surface-alt) {h_pct + s_pct}% 100%)"
    )
    return f"""
<div class="fourth-card">
  <div class="fourth-section-title" style="font-size: 1.15rem;">Signal provenance</div>
  <p class="fourth-kicker" style="margin-bottom: 0.2rem;">
    What each score is built from — and what it isn't.
  </p>
  <div class="fourth-donut-wrap">
    <div class="fourth-donut" style="background: {donut};">
      <div class="fourth-donut-hole">
        <div class="fourth-donut-value">{h_pct}%</div>
        <div class="fourth-donut-label">hospital-level</div>
      </div>
    </div>
  </div>
  <div class="fourth-legend-row">
    <span><span class="fourth-legend-dot" style="background: var(--fourth-primary);"></span>Hospital-level signals</span>
    <strong>{hospital}</strong>
  </div>
  <div class="fourth-legend-row">
    <span><span class="fourth-legend-dot" style="background: var(--fourth-secondary);"></span>State-level context</span>
    <strong>{state}</strong>
  </div>
  <div class="fourth-legend-row">
    <span><span class="fourth-legend-dot" style="background: var(--fourth-surface-alt);"></span>Awaiting CMS release</span>
    <strong>{missing}</strong>
  </div>
  <p class="fourth-kicker" style="margin: 0.8rem 0 0;">
    Full definitions live in the Methodology view.
  </p>
</div>
"""


def render_accounts(data: dict[str, Any]) -> None:
    board_col, side_col = st.columns([0.66, 0.34], gap="medium")

    with board_col:
        st.markdown(
            f'<h2 class="fourth-section-title">Account priority — {escape(data["state"])}</h2>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<p class="fourth-kicker">Generated {escape(data["generated_at"])} from CMS public data.</p>',
            unsafe_allow_html=True,
        )
        rows = [
            '<div class="fourth-account-row fourth-board-head">'
            "<div></div><div>Hospital</div><div>Gap</div><div>Urgency</div>"
            "<div>Lead angle</div><div>Confidence</div><div>Email</div></div>"
        ]
        not_drafted = '<span class="fourth-muted">Not drafted</span>'
        for account in data["accounts"]:
            email_cell = _badge("Drafted", "blue") if account.get("email") else not_drafted
            rows.append(
                '<div class="fourth-account-row">'
                f'<div><span class="fourth-rank">{escape(_initials(account["facility_name"]))}</span></div>'
                f'<div class="fourth-hospital-name">{escape(account["facility_name"])}</div>'
                f'<div class="fourth-score">{escape(str(account["gap_score"]))}</div>'
                f'<div>{_badge(TIER_LABELS.get(account["urgency_tier"], account["urgency_tier"]), account["urgency_tier"])}</div>'
                f'<div class="fourth-muted">{escape(ANGLE_LABELS.get(account["lead_angle"], account["lead_angle"]))}</div>'
                f'<div>{_badge(str(account["data_confidence"]).title(), "sage" if account["data_confidence"] == "high" else "neutral")}</div>'
                f"<div>{email_cell}</div>"
                "</div>"
            )
        st.markdown(
            f'<div class="fourth-card" style="padding: 12px;"><div class="fourth-board">{"".join(rows)}</div></div>',
            unsafe_allow_html=True,
        )

    with side_col:
        st.markdown(_provenance_card(), unsafe_allow_html=True)


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
        with st.popover("Palette"):
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
