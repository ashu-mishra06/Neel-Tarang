"""UI components (Appendix B) as HTML strings built from engine output.

No Streamlit import and no scoring here: every number shown comes from the
engine's GhatScore / EvidenceRow / Gap objects. Labels come from ui.i18n.
"""

from __future__ import annotations

import base64
from html import escape
from pathlib import Path
from typing import Any

from ui import i18n
from ui.theme import CONFIDENCE_ICON, MISSING, TIER

E = escape


def tier_badge(tier: str, lang: str = "en") -> str:
    """Tier as icon + text + colour. Unknown tiers fall back to the NoData style."""
    key = tier if tier in TIER else "NoData"
    t, label = TIER[key], i18n.tier(key, lang)
    return (f'<span class="vgw-badge" style="color:{t["fg"]};background:{t["bg"]};'
            f'border-color:{t["fg"]}" aria-label="{E(label)}">{t["icon"]} {E(label)}</span>')


def confidence_chip(level: str, coverage: float, lang: str = "en") -> str:
    return (f'<span class="vgw-chip">{CONFIDENCE_ICON.get(level, "")} '
            f'{E(i18n.t("confidence", lang))}: {E(i18n.confidence(level, lang))} '
            f'({coverage:.0%} {E(i18n.t("of_expected", lang))})</span>')


def near_boundary_text(nearest: dict[str, Any], lang: str = "en") -> str:
    distance, line = abs(nearest["distance"]), nearest["line"]
    if lang == "hi":
        side = "नीचे" if nearest["distance"] < 0 else "ऊपर"
        return f"{i18n.tier(line, 'hi')} रेखा ({nearest['value']:g}) से {distance:.1f} अंक {side}"
    side = "below" if nearest["distance"] < 0 else "above"
    return f"{distance:.1f} points {side} the {line} line ({nearest['value']:g})"


def flag_chips(s: Any, lang: str = "en") -> list[str]:
    """Warning chips for a ranked ghat (dashed border; text, not colour)."""
    t = lambda key: i18n.t(key, lang)  # noqa: E731
    chips = []
    if s.near_boundary:
        chips.append(f"≈ {t('near_line')}: {near_boundary_text(s.nearest_line, lang)}")
    if s.site_match_uncertain:
        chips.append(f"? {t('site_two')}")
    if s.critical:
        chips.append(f"! {t('zero_do')} ×{s.critical.count}")
    if s.unpaired_breaches:
        chips.append(f"⊘ {len(s.unpaired_breaches)} {t('not_comparable')}")
    status = getattr(s, "list_status", "designated" if s.on_2026_list else "none")
    if status == "none":
        chips.append(t("not_on_list"))
    elif status == "in_use":
        chips.append(t("in_use_2026"))
    return [f'<span class="vgw-chip warn">{E(c)}</span>' for c in chips]


def persistence_chip(s: Any, rules_by_param: dict[str, str], lang: str = "en") -> str:
    """PersistenceBadge: icon + text ('X of Y tables', 'n not sampled'), not colour alone."""
    from scoring.persistence import headline

    r = headline(getattr(s, "persistence", []))
    if r is None:
        return ""
    icon = "↻" if r["label"] == "Repeat" else "•"
    text = i18n.persistence_badge(r, rules_by_param.get(r["parameter"], ""), lang)
    return f'<span class="vgw-chip">{icon} {E(text)}</span>'


def ghat_row(s: Any, lang: str = "en", reason: str | None = None,
             rules_by_param: dict[str, str] | None = None) -> str:
    """GhatRow: rank, name, water body, tier, driver, confidence, flags, one-line reason."""
    lowconf = " lowconf" if s.confidence.level == "Low" else ""
    chips = [tier_badge(s.tier, lang),
             f'<span class="vgw-chip">{E(i18n.t("driver", lang))}: '
             f'{E(i18n.driver(s.driver, lang))}</span>',
             confidence_chip(s.confidence.level, s.confidence.coverage, lang),
             f'<span class="vgw-chip">{E(i18n.t("risk", lang))} {s.risk_score:.1f}</span>']
    return (f'<div class="vgw-row{lowconf}"><div class="vgw-rank">{s.rank}</div><div>'
            f'<div class="vgw-title">{E(s.ghat)}<span class="vgw-wb">{E(s.water_body)}</span>'
            f'</div><div class="vgw-chips">{"".join(chips)}</div>'
            f'<div class="vgw-chips">{persistence_chip(s, rules_by_param or {}, lang)}'
            f'{"".join(flag_chips(s, lang))}</div>'
            f'<div class="vgw-reason">{E(reason or s.reason_short)}</div></div></div>')


def no_baseline_card(name: str, why: str = "", lang: str = "en") -> str:
    return (f'<div class="vgw-row">{tier_badge("NoData", lang)}<div>'
            f'<div class="vgw-title">{E(name)}</div>'
            f'<div class="vgw-reason">{E(i18n.t("no_baseline_text", lang))}</div></div></div>')


def gap_card(gap: Any, lang: str = "en") -> str:
    """GapCard: title, one-line explanation, affected ghats, items."""
    title, detail = i18n.gap_text(gap, lang)
    ghats = f'<div class="vgw-muted">{E(", ".join(gap.ghats))}</div>' if gap.ghats else ""
    items = "".join(f"<li>{E(i)}</li>" for i in gap.items)
    return (f'<div class="vgw-card"><h4>⚑ {E(title)}</h4>'
            f'<div class="vgw-reason">{E(detail)}</div>{ghats}'
            f'{"<ul>" + items + "</ul>" if items else ""}</div>')


def source_link(row: Any) -> str:
    """SourceLink: 'Report 2025, p.28' opening the public PDF at that page."""
    if not row.report_url_with_page:
        return E(row.source_page)  # "user-supplied"
    return (f'<a class="vgw-link" href="{E(row.report_url_with_page)}" target="_blank" '
            f'rel="noopener">Report {E(row.year)}, p.{E(row.source_page)}</a>')


def result_cell(row: Any) -> str:
    """Result text; missing/BDL use the dashed 'missing' style, never green, never 0."""
    if row.status in ("missing", "below_detection"):
        return f'<span class="vgw-missing">{MISSING["icon"]} {E(row.result)}</span>'
    if row.unpaired_breach:
        return f"{E(row.result)} (not comparable: no earlier reading in table)"
    return E(row.result)


def value_cell(row: Any) -> str:
    if row.value is None:
        return f'<span class="vgw-missing">{E(row.value_as_printed or "—")}</span>'
    unit = f" {E(row.unit)}" if row.unit else ""
    return f"{E(row.value_as_printed)}{unit}"


def evidence_table(rows: list[Any]) -> str:
    """EvidenceTable: parameter, value, limit, result, year, festival, phase, source."""
    head = "".join(f"<th>{h}</th>" for h in (
        "Parameter", "Value", "Limit", "Result", "Year", "Festival", "Phase", "Source"))
    body = "".join(
        f"<tr><td>{E(r.parameter)}</td><td>{value_cell(r)}</td><td>{E(r.limit)}</td>"
        f"<td>{result_cell(r)}</td><td>{E(r.year)}</td><td>{E(r.festival)}</td>"
        f"<td>{E(r.phase)}</td><td>{source_link(r)}</td></tr>" for r in rows)
    return f'<table class="vgw-ev"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def page_image(path: Path, alt: str) -> str:
    """Inline page image with real alt text (st.image cannot set alt)."""
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f'<div class="vgw-page"><img src="data:image/png;base64,{data}" alt="{E(alt)}"></div>'


def brand() -> str:
    """Small brand mark for the header row."""
    return ('<div class="vgw-brand"><div class="vgw-logo">🌊</div><div>'
            '<div class="vgw-name">Neel Tarang · नील तरंग</div>'
            '<div class="vgw-sub">Visarjan Ghat Watch · Bhopal</div></div></div>')


def hero(lang: str) -> str:
    """Minimal page lead: one gradient line, one context pill."""
    return (f'<div class="vgw-lead">{E(i18n.t("app_tagline", lang))}</div>'
            f'<span class="vgw-pill">{E(i18n.t("banner", lang))}</span>')


def kpi_cards(items: list[tuple[str, Any]]) -> str:
    """Plain number cards (no colour coding)."""
    cards = "".join(f'<div class="vgw-kpi"><div class="n">{E(str(v))}</div>'
                    f'<div class="l">{E(label)}</div></div>' for label, v in items)
    return f'<div class="vgw-kpis">{cards}</div>'
