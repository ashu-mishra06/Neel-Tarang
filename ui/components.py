"""UI components (Appendix B) as HTML strings built from engine output.

No Streamlit import and no scoring here: every number shown comes from the
engine's GhatScore / EvidenceRow / Gap objects. Labels come from ui.i18n.
No emoji or pictographs: status is text + a CSS-drawn shape + colour.
"""

from __future__ import annotations

import base64
from html import escape
from pathlib import Path
from typing import Any

from ui import i18n
from ui.theme import TIER

E = escape
SEP = '<span class="sep">|</span>'


def tier_badge(tier: str, lang: str = "en") -> str:
    """Tier tag: text label + shape (CSS ::before) + colour, sentence case."""
    key = tier if tier in TIER else "NoData"
    t, label = TIER[key], i18n.tier(key, lang)
    return (f'<span class="nt-tag {key.lower()}" style="color:{t["fg"]};background:{t["bg"]}" '
            f'aria-label="{E(label)}">{E(label)}</span>')


def confidence_text(level: str, coverage: float, lang: str = "en") -> str:
    return (f'<span class="k">{E(i18n.t("confidence", lang))}</span> '
            f'{E(i18n.confidence(level, lang))} ({coverage:.0%})')


def near_boundary_text(nearest: dict[str, Any], lang: str = "en") -> str:
    distance, line = abs(nearest["distance"]), nearest["line"]
    if lang == "hi":
        side = "नीचे" if nearest["distance"] < 0 else "ऊपर"
        return f"{i18n.tier(line, 'hi')} रेखा ({nearest['value']:g}) से {distance:.1f} अंक {side}"
    side = "below" if nearest["distance"] < 0 else "above"
    return f"{distance:.1f} points {side} the {line} line ({nearest['value']:g})"


def flag_texts(s: Any, lang: str = "en") -> list[str]:
    """Plain-language notes for a ranked ghat (no icons)."""
    t = lambda key: i18n.t(key, lang)  # noqa: E731
    notes = []
    if s.critical:
        notes.append(f"{t('zero_do')} ×{s.critical.count}")
    if s.near_boundary:
        notes.append(f"{t('near_line')}: {near_boundary_text(s.nearest_line, lang)}")
    if s.site_match_uncertain:
        notes.append(t("site_two"))
    if s.unpaired_breaches:
        notes.append(f"{len(s.unpaired_breaches)} {t('not_comparable')}")
    status = getattr(s, "list_status", "designated" if s.on_2026_list else "none")
    if status == "none":
        notes.append(t("not_on_list"))
    elif status == "in_use":
        notes.append(t("in_use_2026"))
    return notes


def persistence_text(s: Any, rules_by_param: dict[str, str], lang: str = "en") -> str:
    """PersistenceBadge as text: 'Repeat: BOD above limit ... in 6 of 6 tables (0 not sampled)'."""
    from scoring.persistence import headline

    r = headline(getattr(s, "persistence", []))
    if r is None:
        return ""
    return E(i18n.persistence_badge(r, rules_by_param.get(r["parameter"], ""), lang))


def ghat_row(s: Any, lang: str = "en", reason: str | None = None,
             rules_by_param: dict[str, str] | None = None) -> str:
    """GhatRow: rank | name, tier, driver, confidence, reason, notes | risk score."""
    lowconf = (f'<span class="nt-lowconf">{E(i18n.t("low_conf", lang))}</span>'
               if s.confidence.level == "Low" else "")
    meta = (f'{tier_badge(s.tier, lang)}{SEP}<span class="k">{E(i18n.t("driver", lang))}</span> '
            f'{E(i18n.driver(s.driver, lang))}{SEP}'
            f'{confidence_text(s.confidence.level, s.confidence.coverage, lang)}{lowconf}')
    notes = [persistence_text(s, rules_by_param or {}, lang)] + [E(n) for n in flag_texts(s, lang)]
    notes_html = " · ".join(n for n in notes if n)
    flags = f'<div class="nt-flags">{notes_html}</div>' if notes_html else ""
    return (f'<div class="nt-row{" lowconf" if lowconf else ""}">'
            f'<div class="nt-rank">{s.rank}</div>'
            f'<div><div class="nt-name">{E(s.ghat)} <span class="nt-wb">{E(s.water_body)}</span>'
            f'</div><div class="nt-meta">{meta}</div>'
            f'<div class="nt-reason">{E(reason or s.reason_short)}</div>{flags}</div>'
            f'<div class="nt-score"><div class="n">{s.risk_score:.1f}</div>'
            f'<div class="l">{E(i18n.t("risk", lang))}</div></div></div>')


def no_baseline_card(name: str, why: str = "", lang: str = "en") -> str:
    return (f'<div class="nt-row"><div class="nt-rank">-</div><div>'
            f'<div class="nt-name">{E(name)}</div>'
            f'<div class="nt-meta">{tier_badge("NoData", lang)}</div>'
            f'<div class="nt-reason">{E(i18n.t("no_baseline_text", lang))}</div></div>'
            f'<div></div></div>')


def gap_card(gap: Any, lang: str = "en") -> str:
    """GapCard: title, one-line explanation, affected ghats, items (left rule, no box)."""
    title, detail = i18n.gap_text(gap, lang)
    ghats = f'<p class="nt-note">{E(", ".join(gap.ghats))}</p>' if gap.ghats else ""
    items = "".join(f"<li>{E(i)}</li>" for i in gap.items)
    return (f'<div class="nt-item"><h4>{E(title)}</h4><p>{E(detail)}</p>{ghats}'
            f'{"<ul>" + items + "</ul>" if items else ""}</div>')


def source_link(row: Any) -> str:
    """SourceLink: 'Report 2025, p.28' opening the public PDF at that page."""
    if not row.report_url_with_page:
        return E(row.source_page)  # "user-supplied"
    return (f'<a class="nt-link" href="{E(row.report_url_with_page)}" target="_blank" '
            f'rel="noopener">Report {E(row.year)}, p.{E(row.source_page)}</a>')


def result_cell(row: Any) -> str:
    """Result text; missing/BDL use the dashed 'missing' style, never green, never 0."""
    if row.status in ("missing", "below_detection"):
        return f'<span class="nt-missing">{E(row.result)}</span>'
    if row.unpaired_breach:
        return f"{E(row.result)} (not comparable: no earlier reading in table)"
    return E(row.result)


def value_cell(row: Any) -> str:
    if row.value is None:
        return f'<span class="nt-missing">{E(row.value_as_printed or "—")}</span>'
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
    return f'<table class="nt-ev"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def page_image(path: Path, alt: str) -> str:
    """Inline page image with real alt text (st.image cannot set alt)."""
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f'<div class="nt-page"><img src="data:image/png;base64,{data}" alt="{E(alt)}"></div>'


def brand() -> str:
    """Wordmark for the header row (text only)."""
    return '<div class="nt-brand">Neel Tarang <span>· नील तरंग</span></div>'


def page_header(eyebrow: str, title: str, lede: str = "") -> str:
    """Eyebrow + page title + one-line description: the same on every section."""
    lede_html = f'<p class="nt-lede">{E(lede)}</p>' if lede else ""
    return (f'<p class="nt-eyebrow">{E(eyebrow)}</p>'
            f'<div class="nt-title" role="heading" aria-level="1">{E(title)}</div>{lede_html}')


def h2(text: str) -> str:
    """Section heading (styled div with heading semantics; avoids Streamlit's h2 styles)."""
    return f'<div class="nt-h2" role="heading" aria-level="2">{E(text)}</div>'


def hero(lang: str) -> str:
    """Header for the Ghats page."""
    return page_header(i18n.t("banner", lang), i18n.t("app_tagline", lang))


def kpi_cards(items: list[tuple[str, Any]]) -> str:
    """Stat strip: plain numbers separated by rules (no boxes, no colour coding)."""
    stats = "".join(f'<div class="nt-stat"><div class="n">{E(str(v))}</div>'
                    f'<div class="l">{E(label)}</div></div>' for label, v in items)
    return f'<div class="nt-stats">{stats}</div>'
