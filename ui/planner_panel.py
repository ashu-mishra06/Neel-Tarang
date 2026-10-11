"""PlannerPanel (Appendix B): N selector, include-no-data checkbox, ordered cards."""

from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from scoring.planner import make_plan
from ui import components as ui
from ui import i18n

L = {
    "title": {"en": "🧪 Test planner: I can test N ghats before 20 Oct",
              "hi": "🧪 जाँच योजना: 20 अक्टूबर से पहले N घाटों की जाँच संभव है"},
    "n": {"en": "How many ghats can you test?", "hi": "कितने घाटों की जाँच कर सकते हैं?"},
    "include": {"en": "Include designated ghats with no past readings",
                "hi": "बिना पिछली रीडिंग वाले घोषित घाट भी दिखाएँ"},
    "how": {"en": "Order: risk score × (1 + share of missing readings). High risk and thin data "
                  "come first. This is a suggestion from the data, not an instruction.",
            "hi": "क्रम: जोखिम अंक × (1 + गायब रीडिंग का हिस्सा)। ऊँचा जोखिम और कम आँकड़े पहले। "
                  "यह आँकड़ों से सुझाव है, निर्देश नहीं।"},
    "nobase": {"en": "No past readings: any test is new information.",
               "hi": "कोई पिछली रीडिंग नहीं: कोई भी जाँच नई जानकारी होगी।"},
    "what": {"en": "Data suggests testing dissolved oxygen, BOD and pH before immersion (before "
                   "20 Oct), and again during immersion on the day.",
             "hi": "आँकड़े सुझाव देते हैं: विसर्जन से पहले (20 अक्टूबर से पहले) घुलित ऑक्सीजन, BOD "
                   "और pH की जाँच, और विसर्जन के दिन दोबारा।"},
    "priority": {"en": "priority", "hi": "प्राथमिकता"},
    "coverage": {"en": "data coverage", "hi": "आँकड़ा कवरेज"},
    "missing": {"en": "no {t} table", "hi": "{t} की तालिका नहीं"},
    "unpaired": {"en": "{n} breach(es) not comparable", "hi": "{n} उल्लंघन तुलना योग्य नहीं"},
    "near": {"en": "near the {line} tier line", "hi": "{line} श्रेणी रेखा के पास"},
}


def _t(key: str, lang: str, **kw: Any) -> str:
    return L[key][lang].format(**kw) if kw else L[key][lang]


def _reason_chips(item: Any, lang: str) -> list[str]:
    hi = i18n.BRIEF_HI["festival"] if lang == "hi" else {}
    chips = [f"{i18n.t('risk', lang)} {item.risk_score:.1f}",
             f"{_t('coverage', lang)} {item.coverage:.0%} "
             f"({i18n.confidence(item.confidence, lang)})"]
    for table in item.missing_tables:
        fest, _, year = table.partition(" ")
        chips.append(_t("missing", lang, t=f"{hi.get(fest, fest)} {year}"))
    if item.unpaired:
        chips.append(_t("unpaired", lang, n=item.unpaired))
    if item.near_line:
        chips.append(_t("near", lang, line=i18n.tier(item.near_line, lang)))
    return chips


def planner_panel(data: dict[str, Any], lang: str) -> None:
    rules, scores = data["rules"], data["scores"]
    with st.container(border=True):
        st.markdown(f"#### {_t('title', lang)}")
        cols = st.columns([2, 3])
        n = cols[0].slider(_t("n", lang), 1, len(scores.ranked),
                           rules["planner"]["default_n"], key="plan_n")
        include = cols[1].checkbox(_t("include", lang),
                                   value=rules["planner"]["include_no_data_default"],
                                   key="plan_nodata")
        plan = make_plan(scores, n, include, rules)
        st.caption(_t("how", lang))
        for name in plan.no_baseline:
            ui_html(f'<div class="vgw-card">{ui.tier_badge("NoData", lang)} '
                    f'<b>{escape(name)}</b> - '
                    f'{_t("nobase", lang)}</div>')
        for item in plan.items:
            chips = "".join(f'<span class="vgw-chip">{escape(c)}</span>'
                            for c in _reason_chips(item, lang))
            ui_html(f'<div class="vgw-card"><b>{item.rank_in_plan}. {escape(item.ghat)}</b> '
                    f'{ui.tier_badge(item.tier, lang)} '
                    f'<span class="vgw-muted">{_t("priority", lang)} {item.priority:.1f}</span>'
                    f'<div class="vgw-chips">{chips}</div></div>')
        st.info(_t("what", lang))


def ui_html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)
