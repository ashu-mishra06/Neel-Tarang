"""Neel Tarang (Track 2: Visarjan Ghat Watch) - Streamlit app.

Start with:  streamlit run app.py
Displays engine output only (scoring/); no scoring logic lives here.
Works with no network and no API key.
"""

from __future__ import annotations

import io
import json
from collections import defaultdict
from dataclasses import asdict
from typing import Any

import pandas as pd
import streamlit as st

from scoring.brief import build_briefs, fact_sentence, key_fact
from scoring.config import RULES_PATH, load_rules, repo_path
from scoring.engine import score_all
from scoring.evidence import evidence_for_frame, render_page_image
from scoring.gaps import build_gap_register
from scoring.limits import evaluate_frame, load_limits
from scoring.loader import load_readings
from scoring.reasons import cite
from scoring.rescore import rescore, validate_upload
from ui import charts, i18n
from ui import components as ui
from ui.planner_panel import planner_panel
from ui.theme import css
from ui.upload import changes_table, pending_upload, upload_panel

LANG_KEY = "lang"


def build_data(df: pd.DataFrame, rules: dict[str, Any], limits: Any,
               scores: Any = None) -> dict[str, Any]:
    """Everything the screens show, computed by the engine from one readings table."""
    scores = scores or score_all(df, rules, limits)
    evidence = evidence_for_frame(evaluate_frame(df, limits), limits, rules)
    by_ghat: dict[str, list] = defaultdict(list)
    for row in evidence:
        by_ghat[row.ghat].append(row)
    return {"rules": rules, "scores": scores, "evidence": dict(by_ghat),
            "gaps": build_gap_register(scores, df, rules), "briefs": build_briefs(scores)}


@st.cache_resource(show_spinner="Scoring ghats from the MPPCB readings...")
def load_all(rules_mtime_ns: int) -> dict[str, Any]:
    """Run the engine once; re-run when rules.yaml changes (cache key = its mtime)."""
    rules = load_rules()
    limits = load_limits(rules=rules)
    df = load_readings(rules=rules)
    data = build_data(df, rules, limits)
    data.update(df=df, limits=limits)
    return data


@st.cache_resource(show_spinner="Re-scoring with the uploaded readings...", max_entries=8)
def load_with_upload(rules_mtime_ns: int, upload: bytes) -> dict[str, Any]:
    """Validate the upload; if valid, re-score. Never raises for a bad file."""
    base = load_all(rules_mtime_ns)
    rules, limits = base["rules"], base["limits"]
    result = validate_upload(upload, base["df"], rules, limits)
    if not result.ok:
        return {"data": base, "result": result}
    try:
        merged, _, after, changes = rescore(base["df"], result.rows, rules, limits)
    except Exception as err:  # noqa: BLE001 - show a message, never a stack trace
        return {"data": base, "result": result,
                "error": f"Could not re-score with this file: {err}"}
    data = build_data(merged, rules, limits, after)
    data.update(df=merged, limits=limits)
    return {"data": data, "result": result, "changes": changes}


def html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def fmt(value: float | None, digits: int = 2) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


# ---------- ranked list ----------


def how_to_read(rules: dict[str, Any], lang: str) -> None:
    tiers = rules["scoring"]["tiers"]
    with st.expander(i18n.t("how_title", lang)):
        st.markdown(i18n.t("how_body", lang, high=f"{tiers['high']:g}",
                           medium=f"{tiers['medium']:g}"))


def kpis(data: dict[str, Any], lang: str) -> None:
    """Four stat cards, each with a real supporting line (no invented trends)."""
    scores, tiers = data["scores"], data["rules"]["scoring"]["tiers"]
    low = sum(s.confidence.level == "Low" for s in scores.ranked)
    html(ui.stat_cards([
        (i18n.t("kpi_ranked", lang), len(scores.ranked),
         i18n.t("kpi_ranked_sub", lang, n=len(scores.blind_spots))),
        (i18n.t("kpi_high", lang), sum(s.tier == "High" for s in scores.ranked),
         i18n.t("kpi_high_sub", lang, medium=f"{tiers['medium']:g}", high=f"{tiers['high']:g}")),
        (i18n.t("kpi_lowconf", lang), low, i18n.t("kpi_lowconf_sub", lang)),
        (i18n.t("kpi_unpaired", lang), sum(len(s.unpaired_breaches) for s in scores.ranked),
         i18n.t("kpi_unpaired_sub", lang)),
    ]))


def overview_chart(data: dict[str, Any], lang: str) -> None:
    html(ui.card_title(i18n.t("chart_title", lang)))
    labels = {"baseline": i18n.t("part_baseline", lang),
              "festival": i18n.t("part_festival", lang), "risk": i18n.t("risk", lang)}
    tiers = {k: i18n.tier(k, lang) for k in ("High", "Medium", "Low", "NoData")}
    st.vega_lite_chart(charts.risk_breakdown(data["scores"], data["rules"], labels, tiers),
                       width="stretch")
    st.caption(i18n.t("chart_caption", lang))


def summary_card(data: dict[str, Any], lang: str) -> None:
    html(ui.card_title(i18n.t("summary", lang)))
    top = data["scores"].ranked[:3]
    html(ui.summary_list([(s.ghat, ui.status(s.tier, lang), f"{s.risk_score:.1f}") for s in top]))
    st.caption(i18n.t("risk", lang))


def row_reason(s: Any, data: dict[str, Any], lang: str) -> str:
    """English: the engine's one-line reason. Hindi: the reviewed brief sentence."""
    if lang == "en":
        return s.reason_short
    return fact_sentence(key_fact(s, data["limits"]), "hi")


def ranked_list(data: dict[str, Any], lang: str) -> None:
    """Ranked table, then one detail view for the chosen ghat (progressive disclosure)."""
    scores, rules = data["scores"], data["rules"]
    rules_by_param = {k: v.rule for k, v in data["limits"].items()}
    with st.container(border=True, key="card-ranked"):
        html(ui.card_title(i18n.t("tab_rank", lang)))
        how_to_read(rules, lang)
        reasons = {s.ghat: row_reason(s, data, lang) for s in scores.ranked}
        html(ui.ranked_table(scores, lang, reasons, rules_by_param))
        tiers = rules["scoring"]["tiers"]
        st.caption(i18n.t("tier_note", lang, medium=f"{tiers['medium']:g}",
                          high=f"{tiers['high']:g}", n=len(scores.ranked)))
        if scores.blind_spots:
            html(ui.h2(i18n.t("no_baseline_title", lang)))
            for b in scores.blind_spots:
                html(ui.no_baseline_card(b.ghat, b.why, lang))
    with st.container(border=True, key="card-detail"):
        html(ui.card_title(i18n.t("details_card", lang)))
        names = [s.ghat for s in scores.ranked]
        name = st.selectbox(i18n.t("choose_ghat", lang), names, key="detail_ghat")
        s = next(x for x in scores.ranked if x.ghat == name)
        html(ui.ghat_row(s, lang, row_reason(s, data, lang), rules_by_param))
        ghat_detail(s, data, lang)


def gaps_card(data: dict[str, Any], lang: str, gaps_page: Any) -> None:
    with st.container(border=True, key="card-gaps"):
        html(ui.card_title(i18n.t("gaps_card", lang)))
        for g in data["gaps"]:
            if g.id in ("missing_tables", "designated_not_in_data", "single_column_tables"):
                html(ui.gap_card(g, lang))
        st.page_link(gaps_page, label=i18n.t("see_gaps", lang), icon=":material/arrow_forward:")


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
        "Source": cite(p["year"], p["pre_page"], p["during_page"]),
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


def pairs_charts(s: Any, data: dict[str, Any], lang: str) -> None:
    st.caption(i18n.t("pairs_chart_caption", lang))
    unpaired = ("no earlier reading in this table" if lang == "en"
                else "इस तालिका में पहले की रीडिंग नहीं")
    for name, limit in data["limits"].items():
        spec = charts.pairs_chart(s, name, limit, unpaired,
                                  *(("बिगड़ा", "वैसा ही या बेहतर") if lang == "hi" else ()))
        st.markdown(f"**{i18n.parameter(name, lang)}**")
        if spec is None:
            st.caption(i18n.t("no_pairs", lang))
        else:
            st.vega_lite_chart(spec, width="stretch")


def ghat_detail(s: Any, data: dict[str, Any], lang: str = "en") -> None:
    """Detail for one ranked ghat (inside its expander), split into four tabs."""
    rules, key = data["rules"], f"g{s.rank}"
    if s.site_match_uncertain:
        st.warning(s.site_match_note)
    cols = st.columns(3)
    cols[0].metric(i18n.t("risk", lang), f"{s.risk_score:.1f}")
    cols[1].metric(i18n.t("part_baseline", lang), fmt(s.baseline, 3))
    cols[2].metric(i18n.t("part_festival", lang), fmt(s.festival, 3))
    chart_tab, numbers_tab, pages_tab, gaps_tab_ = st.tabs([
        i18n.t("d_chart", lang), i18n.t("d_numbers", lang),
        i18n.t("d_evidence", lang), i18n.t("d_gaps", lang)])
    with chart_tab:
        pairs_charts(s, data, lang)
    with numbers_tab:
        st.markdown(f"**{i18n.t('full_reason', lang)}:** {s.reason}")
        st.markdown(driver_explanation(s))
        st.dataframe(parameter_table(s), hide_index=True, width="stretch")
        st.markdown("**Breaches per table (persistence)** - missing tables are listed, "
                    "never counted as clean")
        st.dataframe(pd.DataFrame(s.persistence).rename(columns={
            "breaches": "breached (X)", "valid_tables": "tables with a reading (Y)",
            "missing_tables": "not sampled (M)"}), hide_index=True, width="stretch")
        if s.matched_pairs:
            st.dataframe(pairs_table(s), hide_index=True, width="stretch")
        if s.unpaired_breaches:
            st.markdown("**Breaches that cannot be compared** (not in the score; lower confidence)")
            for u in s.unpaired_breaches:
                unit = f" {u['unit']}" if u["unit"] else ""
                st.markdown(f"- {u['parameter']} {u['value']:g}{unit}, {u['festival']} "
                            f"{u['year']} {u['phase']}, {cite(u['year'], u['source_page'])} - "
                            f"{u['why']}")
        if s.critical:
            st.markdown(f"**{s.critical.note}**")
            st.markdown("\n".join(f"- {r['festival']} {r['year']} {r['phase']}, "
                                  f"{cite(r['year'], r['source_page'])}"
                                  for r in s.critical.readings))
        confidence_block(s)
    with pages_tab:
        scope = st.radio("Show", ["Scored parameters (pH, DO, BOD)", "All parameters"],
                         horizontal=True, key=f"scope_{key}")
        show_images = st.toggle("Show report page images", value=s.rank == 1,
                                key=f"img_{key}")
        rows = data["evidence"].get(s.ghat, [])
        if scope.startswith("Scored"):
            rows = [r for r in rows if r.scored]
        evidence_section(rows, rules, show_images)
    with gaps_tab_:
        for g in [g for g in data["gaps"] if s.ghat in g.ghats]:
            html(ui.gap_card(g, lang))


def brief_tab(data: dict[str, Any], lang: str) -> None:
    options = ["हिन्दी", "English"] if lang == "hi" else ["English", "हिन्दी"]
    choice = st.radio(i18n.t("brief_lang", lang), options, horizontal=True, key="brief_lang")
    code = "hi" if choice == "हिन्दी" else "en"
    brief = data["briefs"][code]
    if code == "hi":
        st.success(i18n.t("brief_reviewed", lang))
    st.caption(i18n.t("copy_hint", lang))
    st.code(brief["text"], language=None, wrap_lines=True)
    cols = st.columns(2)
    cols[0].download_button(i18n.t("dl_text", lang), brief["text"].encode("utf-8"),
                            f"neel_tarang_brief_{code}.txt", mime="text/plain")
    cols[1].download_button(i18n.t("dl_html", lang), brief["html"].encode("utf-8"),
                            f"neel_tarang_brief_{code}.html", mime="text/html")


# ---------- gaps and method ----------


def gaps_tab(data: dict[str, Any], lang: str = "en") -> None:
    st.markdown(i18n.t("gaps_intro", lang))
    st.markdown("**Confidence levels:** High ≥ 90% of expected readings, Medium ≥ 70%, "
                "else Low; capped at Medium if the latest Durga table is missing or the site "
                "name is uncertain; one level lower if a breach cannot be compared.")
    for g in data["gaps"]:
        html(ui.gap_card(g, lang))


def method_tab(data: dict[str, Any]) -> None:
    st.markdown("**Download the derived data** (all numbers come from the engine):")
    cols = st.columns(3)
    scores_json = json.dumps(data["scores"].to_dict(), indent=2, ensure_ascii=False)
    gaps_json = json.dumps([asdict(g) for g in data["gaps"]], indent=2, ensure_ascii=False)
    buf = io.StringIO()
    pd.DataFrame([asdict(r) for rows in data["evidence"].values() for r in rows]).to_csv(
        buf, index=False)
    cols[0].download_button("ghat_scores.json", scores_json.encode("utf-8"), "ghat_scores.json")
    cols[1].download_button("gap_register.json", gaps_json.encode("utf-8"), "gap_register.json")
    cols[2].download_button("evidence.csv", buf.getvalue().encode("utf-8"), "evidence.csv")
    method = repo_path("docs/METHOD.md")
    st.markdown(method.read_text(encoding="utf-8") if method.exists() else "METHOD.md missing")


# ---------- pages (one per section in the top navigation) ----------


def section_header(key: str, lang: str, action: Any = None, action_label: str = "") -> None:
    """Page title + one-line description, with an optional primary action on the right."""
    left, right = st.columns([4, 1.3], vertical_alignment="bottom")
    with left:
        html(ui.page_header(i18n.t("banner", lang), i18n.t(f"nav_{key}", lang),
                            i18n.t(f"lede_{key}", lang)))
    if action is not None:
        with right, st.container(key="actions"):
            st.page_link(action, label=action_label, icon=":material/add:")


def page_ghats(data: dict[str, Any], state: dict[str, Any], lang: str,
               pages: dict[str, Any]) -> None:
    section_header("ghats", lang, pages["readings"], i18n.t("nav_upload", lang))
    if state.get("changes"):
        st.info(i18n.t("in_use_banner", lang, label=state["label"]))
    kpis(data, lang)
    left, right = st.columns([2.1, 1], gap="medium")
    with left, st.container(border=True, key="card-chart"):
        overview_chart(data, lang)
    with right, st.container(border=True, key="card-summary"):
        summary_card(data, lang)
    ranked_list(data, lang)
    gaps_card(data, lang, pages["gaps"])


def page_upload(state: dict[str, Any], lang: str) -> None:
    section_header("upload", lang)
    left, right = st.columns([2, 3], gap="medium")
    with left, st.container(border=True, key="card-upload"):
        upload_panel(state, lang)
    with right:
        if state.get("changes"):
            with st.container(border=True, key="card-changes"):
                changes_table(state, state["label"])


def page_gaps(data: dict[str, Any], lang: str) -> None:
    section_header("gaps", lang)
    with st.container(border=True, key="card-gaplist"):
        gaps_tab(data, lang)
    with st.container(border=True, key="card-method"):
        method_tab(data)


def main() -> None:
    st.set_page_config(page_title="Neel Tarang · नील तरंग", page_icon=":material/water:",
                       layout="wide", initial_sidebar_state="expanded")
    html(css())
    st.logo(str(repo_path("ui/assets/logo.svg")), size="large",
            icon_image=str(repo_path("ui/assets/logo_icon.svg")))
    lang = "en" if st.session_state.get(LANG_KEY) else "hi"
    mtime = RULES_PATH.stat().st_mtime_ns
    upload, label = pending_upload()
    state: dict[str, Any] = {"label": label}
    if upload is None:
        data = load_all(mtime)
    else:
        state.update(load_with_upload(mtime, upload))
        data = state["data"]
    pages: dict[str, Any] = {}

    def ghats() -> None:
        page_ghats(data, state, lang, pages)

    def planner() -> None:
        section_header("planner", lang)
        with st.container(border=True, key="card-planner"):
            planner_panel(data, lang)

    def brief() -> None:
        section_header("brief", lang)
        with st.container(border=True, key="card-brief"):
            brief_tab(data, lang)

    def readings() -> None:
        page_upload(state, lang)

    def gaps() -> None:
        page_gaps(data, lang)

    pages.update(
        ghats=st.Page(ghats, title=i18n.t("nav_ghats", lang), icon=":material/home:",
                      url_path="ghats", default=True),
        planner=st.Page(planner, title=i18n.t("nav_planner", lang), icon=":material/fact_check:",
                        url_path="planner"),
        brief=st.Page(brief, title=i18n.t("nav_brief", lang), icon=":material/description:",
                      url_path="brief"),
        readings=st.Page(readings, title=i18n.t("nav_upload", lang),
                         icon=":material/upload_file:", url_path="readings"),
        gaps=st.Page(gaps, title=i18n.t("nav_gaps", lang), icon=":material/rule:",
                     url_path="gaps"),
    )
    nav = st.navigation(list(pages.values()))
    with st.sidebar:
        st.caption("Language / भाषा")
        st.toggle("English", key=LANG_KEY, help="हिन्दी / English")
    with st.container(key="topbar"):
        left, right = st.columns([4, 1.3], vertical_alignment="center")
        left.markdown(ui.crumb(nav.title), unsafe_allow_html=True)
        with right:
            st.page_link(pages["gaps"], label=i18n.t("help", lang), icon=":material/help:")
    nav.run()
    st.caption(i18n.t("footer", lang))
    if lang == "hi":
        st.caption(i18n.t("ui_draft", lang))


if __name__ == "__main__":
    main()
