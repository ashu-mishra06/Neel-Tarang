"""Visarjan Ghat Watch - Streamlit app.

Start with:  streamlit run app.py
Displays engine output only (scoring/); no scoring logic lives here.
Works with no network and no API key.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd
import streamlit as st

from scoring.config import load_rules, repo_path
from scoring.engine import score_all, write_json
from scoring.evidence import evidence_for_frame, render_page_image
from scoring.gaps import build_gap_register, write_gap_register
from scoring.limits import evaluate_frame, load_limits
from scoring.loader import load_readings
from ui import components as ui
from ui.theme import css

BANNER = "Durga visarjan: 20 Oct 2026 | Standard: CPCB class B | Data: MPPCB 2023-2025"


@st.cache_resource(show_spinner="Scoring ghats from the MPPCB readings...")
def load_all() -> dict[str, Any]:
    """Run the engine once per session: scores, evidence, gaps."""
    rules = load_rules()
    limits = load_limits(rules=rules)
    df = load_readings(rules=rules)
    scores = score_all(df, rules, limits)
    evidence = evidence_for_frame(evaluate_frame(df, limits), limits, rules)
    by_ghat: dict[str, list] = defaultdict(list)
    for row in evidence:
        by_ghat[row.ghat].append(row)
    return {"rules": rules, "scores": scores, "evidence": dict(by_ghat),
            "gaps": build_gap_register(scores, df, rules)}


def html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def fmt(value: float | None, digits: int = 2) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


# ---------- ranked list ----------


def how_to_read(rules: dict[str, Any]) -> None:
    t, d = rules["scoring"]["tiers"], rules["scoring"]["driver"]
    with st.expander("How to read this list"):
        st.markdown(
            f"- **Tier** comes from the risk score (0-100): High ≥ {t['high']:g}, "
            f"Medium ≥ {t['medium']:g}, else Low. A reported dissolved oxygen of 0 mg/l lifts "
            "a ghat to at least High (team's own flag, not a CPCB limit).\n"
            "- **Driver** says *why*: *poor before* = water already breaches class B before "
            f"immersion (baseline ≥ {d['baseline']:g}); *worsens* = matched before/during "
            "readings get worse by at least 1 mg/l DO or BOD, or cross the limit.\n"
            "- **Confidence** = share of expected readings that exist, lowered for missing "
            "tables, uncertain site names and breaches that cannot be compared. A data hole "
            "never counts as clean.\n"
            "- A **dashed outline** marks low confidence; **≈** marks a score near a tier line.\n"
            "- Readings are compared with CPCB class B limits only. No health conclusions.")


def select_ghat(name: str) -> None:
    st.session_state["detail_ghat"] = name


def ranked_list(data: dict[str, Any]) -> None:
    scores = data["scores"]
    how_to_read(data["rules"])
    for s in scores.ranked:
        html(ui.ghat_row(s))
        st.button(f"Details: {s.ghat}", key=f"btn_{s.rank}", on_click=select_ghat,
                  args=(s.ghat,))
    no_baseline = [b for b in scores.blind_spots]
    if no_baseline:
        st.subheader("No baseline")
        st.caption("Designated or listed ghats with no usable past readings. Not ranked.")
        for b in no_baseline:
            html(ui.no_baseline_card(b.ghat, b.why))


# ---------- detail ----------


def driver_explanation(s: Any) -> str:
    d = s.driver_detail
    poor = "yes" if d["poor_before"] else "no"
    anchor = {True: "met", False: "not met", None: "no matched pairs"}[d["worsens_anchor_met"]]
    because = f" ({'; '.join(d['worsens_because'])})" if d["worsens_because"] else ""
    return (f"Poor before immersion: **{poor}** (baseline {fmt(d['baseline'], 3)} vs cut-off "
            f"{d['baseline_cutoff']:g}, an Appendix A placeholder). Worsens anchor: "
            f"**{anchor}**{because}. Festival score {fmt(d['festival_score'], 3)} "
            f"(worst parameter).")


def parameter_table(s: Any) -> pd.DataFrame:
    return pd.DataFrame([{
        "Parameter": p.parameter, "Limit": p.limit,
        "Pre readings breaching": f"{p.pre_breaches} of {p.pre_valid}",
        "Baseline part": fmt(p.baseline, 3), "Festival value": fmt(p.festival, 3),
        "Matched pairs": p.matched_pairs,
        "Paired mean before → during": "—" if p.paired_pre_mean is None else
        f"{p.paired_pre_mean:.2f} → {p.paired_during_mean:.2f}",
        "Mean worsening": fmt(p.mean_worsening),
        "Crosses limit": "yes" if p.crossing else "no",
        "Anchor met": "yes" if p.meets_anchor else "no",
    } for p in s.parameters])


def pairs_table(s: Any) -> pd.DataFrame:
    return pd.DataFrame([{
        "Table": f"{p['festival']} {p['year']}", "Parameter": p["parameter"],
        "Before": p["pre"], "During": p["during"], "Worsening": round(p["worsening"], 2),
        "Page": f"Report {p['year']} p.{p['pre_page']}",
    } for p in s.matched_pairs])


def confidence_block(s: Any) -> None:
    c = s.confidence
    st.markdown(f"**Confidence: {c.level}** - {c.valid} of {c.expected} expected readings "
                f"({c.coverage:.0%}).")
    for reason in c.cap_reasons:
        st.markdown(f"- {reason}")
    if c.downgraded_for_unpaired:
        st.markdown("- lowered one level: breaches that cannot be compared")
    if c.missing_items:
        with st.expander(f"Missing items ({len(c.missing_items)})"):
            st.markdown("\n".join(f"- {m}" for m in c.missing_items))


def evidence_section(rows: list[Any], rules: dict[str, Any], show_images: bool) -> None:
    pages: dict[tuple, list] = defaultdict(list)
    for r in rows:
        pages[(r.year, r.festival, r.source_page)].append(r)
    for (year, festival, page), group in sorted(pages.items()):
        st.markdown(f"**{festival} {year}** - {ui.source_link(group[0])}",
                    unsafe_allow_html=True)
        left, right = st.columns([3, 2]) if show_images else (st.container(), None)
        with left:
            html(ui.evidence_table(group))
        if right is not None and group[0].report_url_with_page:
            with right:
                try:
                    path = render_page_image(year, page, rules)
                    html(ui.page_image(path, f"Report {year} page {page}: {festival} {year} "
                                             f"table for {group[0].ghat}"))
                except (FileNotFoundError, ValueError) as err:
                    st.info(f"Page image not available: {err}")


def detail(data: dict[str, Any]) -> None:
    scores, rules = data["scores"], data["rules"]
    names = [s.ghat for s in scores.ranked]
    st.subheader("Ghat detail")
    if st.session_state.get("detail_ghat") not in names:
        st.session_state["detail_ghat"] = names[0]
    name = st.selectbox("Show details for", names, key="detail_ghat")
    s = next(x for x in scores.ranked if x.ghat == name)
    html(ui.ghat_row(s))
    if s.site_match_uncertain:
        st.warning(s.site_match_note)
    cols = st.columns(3)
    cols[0].metric("Risk score", f"{s.risk_score:.1f}", help="0-100; decides the tier")
    cols[1].metric("Baseline (before immersion)", fmt(s.baseline, 3),
                   help="0.5 x breach rate + 0.5 x mean exceedance, pre-immersion readings")
    cols[2].metric("Festival effect (worst parameter)", fmt(s.festival, 3),
                   help="How much readings got worse during/after immersion")
    st.markdown(driver_explanation(s))
    st.markdown(f"**Why:** {s.reason}")
    st.markdown("**By parameter**")
    st.dataframe(parameter_table(s), hide_index=True, width="stretch")
    if s.matched_pairs:
        st.markdown("**Matched before/during pairs** (same table)")
        st.dataframe(pairs_table(s), hide_index=True, width="stretch")
    if s.unpaired_breaches:
        st.markdown("**Breaches that cannot be compared** (not in the score; lower confidence)")
        for u in s.unpaired_breaches:
            unit = f" {u['unit']}" if u["unit"] else ""
            st.markdown(f"- {u['parameter']} {u['value']:g}{unit}, {u['festival']} {u['year']} "
                        f"{u['phase']}, Report {u['year']} p.{u['source_page']} - {u['why']}")
    if s.critical:
        st.markdown(f"**{s.critical.note}**")
        st.markdown("\n".join(f"- {r['festival']} {r['year']} {r['phase']}, "
                              f"Report {r['year']} p.{r['source_page']}"
                              for r in s.critical.readings))
    confidence_block(s)
    ghat_gaps = [g for g in data["gaps"] if s.ghat in g.ghats]
    if ghat_gaps:
        st.markdown("**Gaps for this ghat**")
        for g in ghat_gaps:
            html(ui.gap_card(g))
    st.markdown("**Evidence** - every reading, with the report page it came from")
    scope = st.radio("Show", ["Scored parameters (pH, DO, BOD)", "All parameters"],
                     horizontal=True, key="ev_scope")
    show_images = st.toggle("Show page images", value=True, key="ev_images")
    rows = data["evidence"].get(s.ghat, [])
    if scope.startswith("Scored"):
        rows = [r for r in rows if r.scored]
    evidence_section(rows, rules, show_images)


# ---------- gaps and method ----------


def gaps_tab(data: dict[str, Any]) -> None:
    st.markdown("Everything the data does not cover. Missing data is shown as missing, "
                "never as clean.")
    st.markdown("**Confidence levels:** High ≥ 90% of expected readings, Medium ≥ 70%, "
                "else Low; capped at Medium if the latest Durga table is missing or the site "
                "name is uncertain; one level lower if a breach cannot be compared.")
    for g in data["gaps"]:
        html(ui.gap_card(g))


def method_tab(data: dict[str, Any]) -> None:
    rules = data["rules"]
    st.markdown("**Download the derived data** (all numbers come from the engine):")
    cols = st.columns(3)
    scores_path = write_json(data["scores"])
    gaps_path = write_gap_register(data["gaps"])
    evidence_path = repo_path(rules["evidence_csv"])
    cols[0].download_button("ghat_scores.json", scores_path.read_bytes(), "ghat_scores.json")
    cols[1].download_button("gap_register.json", gaps_path.read_bytes(), "gap_register.json")
    if evidence_path.exists():
        cols[2].download_button("evidence.csv", evidence_path.read_bytes(), "evidence.csv")
    method = repo_path("docs/METHOD.md")
    st.markdown(method.read_text(encoding="utf-8") if method.exists() else "METHOD.md missing")


def main() -> None:
    st.set_page_config(page_title="Visarjan Ghat Watch", page_icon="🌊", layout="wide")
    html(css())
    st.title("Visarjan Ghat Watch")
    html(f'<div class="vgw-banner">{BANNER}</div>')
    data = load_all()
    ranking, gaps, method = st.tabs(["Ranked ghats", "Gaps & caveats", "Method & data"])
    with ranking:
        ranked_list(data)
        st.divider()
        detail(data)
    with gaps:
        gaps_tab(data)
    with method:
        method_tab(data)
    st.caption("Readings compared with CPCB class B limits only; no health conclusions. "
               "Persona inferred from the problem statement, not from interviews.")


main()
