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


# ---------- dashboard pieces (reference layout, 11 Oct 2026) ----------


def status(tier: str, lang: str = "en") -> str:
    """Tier as a table status: coloured shape + coloured text (no pill)."""
    key = tier if tier in TIER else "NoData"
    return f'<span class="nt-status {key.lower()}">{E(i18n.tier(key, lang))}</span>'


def stat_cards(items: list[tuple[str, Any, str]]) -> str:
    """Stat cards: label, big number, one real supporting line (no invented trends)."""
    cards = "".join(f'<div class="nt-kpi"><div class="l">{E(label)}</div>'
                    f'<div class="n">{E(str(value))}</div><div class="s">{E(sub)}</div></div>'
                    for label, value, sub in items)
    return f'<div class="nt-kpis">{cards}</div>'


def summary_list(rows: list[tuple[str, str, str]]) -> str:
    """Right-hand summary card rows: name + tier status, value on the right."""
    out = []
    for i, (name, tier_html, value) in enumerate(rows):
        first = " first" if i == 0 else ""
        out.append(f'<div class="nt-sum{first}"><div class="name">{E(name)}<br>{tier_html}</div>'
                   f'<div class="val">{E(value)}</div></div>')
    return "".join(out)


def ranked_table(scores: Any, lang: str, reasons: dict[str, str],
                 rules_by_param: dict[str, str]) -> str:
    """Ranked ghats as one scannable table; notes and reason sit under the ghat name."""
    t = lambda key: E(i18n.t(key, lang))  # noqa: E731
    head = (f'<tr><th>#</th><th>{t("col_ghat")}</th><th>{t("col_tier")}</th>'
            f'<th class="hide-sm">{t("driver")}</th><th class="hide-sm">{t("confidence")}</th>'
            f'<th style="text-align:right">{t("risk")}</th></tr>')
    rows = []
    for s in scores.ranked:
        notes = [persistence_text(s, rules_by_param, lang)] + [E(n) for n in flag_texts(s, lang)]
        notes_html = " · ".join(n for n in notes if n)
        low = (f' <span class="nt-lowconf">{t("low_conf")}</span>'
               if s.confidence.level == "Low" else "")
        rows.append(
            f'<tr><td class="num" style="text-align:left">{s.rank}</td>'
            f'<td><b>{E(s.ghat)}</b> <span class="sub" style="display:inline">'
            f'{E(s.water_body)}</span><span class="sub">{E(reasons.get(s.ghat, ""))}</span>'
            f'<span class="sub">{notes_html}</span></td>'
            f'<td>{status(s.tier, lang)}</td>'
            f'<td class="hide-sm">{E(i18n.driver(s.driver, lang))}</td>'
            f'<td class="hide-sm">{E(i18n.confidence(s.confidence.level, lang))} '
            f'({s.confidence.coverage:.0%}){low}</td>'
            f'<td class="num">{s.risk_score:.1f}</td></tr>')
    return f'<table class="nt-table"><thead>{head}</thead><tbody>{"".join(rows)}</tbody></table>'


def crumb(section: str) -> str:
    return f'<div class="nt-crumb">Neel Tarang &nbsp;/&nbsp; <b>{E(section)}</b></div>'


def card_title(text: str) -> str:
    return f'<div class="nt-card-title" role="heading" aria-level="2">{E(text)}</div>'


# ---------- map spotlight and plain-language verdict (13 Oct 2026) ----------


def spot_overview(scores: Any, lang: str) -> str:
    """Spotlight card when the map shows every ghat."""
    high = sum(s.tier == "High" for s in scores.ranked)
    text = i18n.t("spot_overview_text", lang, n=len(scores.ranked), high=high,
                  nobase=len(scores.blind_spots))
    return (f'<div class="nt-spot"><div class="nt-spot-eyebrow">'
            f'{E(i18n.t("spot_overview", lang))}</div><p class="nt-spot-text">{E(text)}</p>'
            f'{_legend(lang)}</div>')


def _legend(lang: str) -> str:
    items = "".join(f"<li>{status(k, lang)}</li>" for k in ("High", "Medium", "Low", "NoData"))
    return f'<ul class="nt-legend" aria-label="{E(i18n.t("col_tier", lang))}">{items}</ul>'


def headline(s: Any, limits: dict[str, Any], lang: str) -> str:
    """One plain sentence: what the readings suggest for this ghat."""
    from scoring.explain import explain

    return i18n.t(f"suggest_{explain(s, limits).action}", lang)


def spot_card(heading: str, point: dict[str, Any], s: Any, limits: dict[str, Any], n: int,
              lang: str) -> str:
    """Spotlight for the ghat the map is showing: tier, score, one plain sentence."""
    approx = (f' <span class="nt-spot-approx">({E(point["approx"])})</span>'
              if point["approx"] else "")
    top = (f'<div class="nt-spot-eyebrow">{E(heading)}</div>'
           f'<div class="nt-spot-name">{E(point["ghat"])}{approx}</div>')
    if s is None:
        return (f'<div class="nt-spot">{top}<div class="nt-spot-meta">'
                f'{tier_badge("NoData", lang)}</div><p class="nt-spot-text">'
                f'{E(i18n.t("no_baseline_text", lang))}</p></div>')
    meta = (f'{tier_badge(s.tier, lang)}{SEP}{E(i18n.t("spot_rank", lang, rank=s.rank, n=n))}'
            f'{SEP}{E(i18n.t("confidence", lang))}: {E(i18n.confidence(s.confidence.level, lang))}')
    return (f'<div class="nt-spot">{top}<div class="nt-spot-meta">{meta}</div>'
            f'<div class="nt-spot-score"><span class="n">{s.risk_score:.1f}</span> '
            f'<span class="l">{E(i18n.t("risk_of", lang))}</span></div>'
            f'<p class="nt-spot-text">{E(headline(s, limits, lang))}</p></div>')


def _answer(state: str, word: str) -> str:
    """Answer chip: text always present; the class only adds a quiet colour."""
    return f'<span class="nt-answer {E(state)}">{E(word)}</span>'


def _question(title: str, answer_html: str, fact: str, note: str) -> str:
    fact_html = f'<p class="nt-q-fact">{E(fact)}</p>' if fact else ""
    note_html = f'<p class="nt-q-note">{E(note)}</p>' if note else ""
    return (f'<div class="nt-q"><div class="nt-q-title">{E(title)}</div>{answer_html}'
            f'{fact_html}{note_html}</div>')


def _before_block(e: Any, lang: str) -> str:
    t = lambda key, **kw: i18n.t(key, lang, **kw)  # noqa: E731
    fact = (t("before_fact", param=i18n.parameter(e.before_parameter, lang),
              limit=i18n.limit_words(e.before_limit, lang), x=e.before_breaches,
              y=e.before_valid) if e.before_valid else "")
    note = {"poor": t("before_poor_note", b=e.baseline, cut=e.baseline_cutoff),
            "mild": t("before_mild_note", b=e.baseline, cut=e.baseline_cutoff)}.get(
        e.before_state, "")
    state = {"poor": "bad", "mild": "some", "ok": "good"}[e.before_state]
    return _question(t("q_before"), _answer(state, t(f"a_before_{e.before_state}")), fact, note)


def _during_block(e: Any, lang: str) -> str:
    t = lambda key, **kw: i18n.t(key, lang, **kw)  # noqa: E731
    fact = ""
    if e.pair and e.during_state in ("yes", "some"):
        p = e.pair
        fact = t("during_fact", param=i18n.parameter(p["parameter"], lang), pre=p["pre"],
                 during=p["during"], unit=p["unit"], festival=i18n.festival(p["festival"], lang),
                 year=p["year"], source=p["source"])
    state = {"yes": "bad", "some": "some", "no": "good", "unknown": "unknown"}[e.during_state]
    return _question(t("q_during"), _answer(state, t(f"a_during_{e.during_state}")), fact,
                     t(f"during_{e.during_state}_note"))


def _sure_block(e: Any, lang: str) -> str:
    t = lambda key, **kw: i18n.t(key, lang, **kw)  # noqa: E731
    notes = []
    if e.missing_tables:
        tables = ", ".join(" ".join(i18n.festival(w, lang) for w in m.split())
                           for m in e.missing_tables)
        notes.append(t("sure_tables", tables=tables))
    if e.not_sampled:
        notes.append(t("sure_cells", n=e.not_sampled))
    if e.unpaired:
        notes.append(t("sure_unpaired", n=e.unpaired))
    if e.site_uncertain:
        notes.append(t("sure_site"))
    state = {"High": "good", "Medium": "some", "Low": "bad"}.get(e.confidence, "unknown")
    return _question(t("q_sure"), _answer(state, i18n.confidence(e.confidence, lang)),
                     t("sure_fact", have=e.coverage_pct),
                     " · ".join(notes) if notes else t("sure_all"))


def verdict(s: Any, limits: dict[str, Any], lang: str,
            rules_by_param: dict[str, str] | None = None) -> str:
    """Detail header: ghat, tier, score, then three plain questions and a suggestion."""
    from scoring.explain import explain

    e = explain(s, limits)
    t = lambda key, **kw: i18n.t(key, lang, **kw)  # noqa: E731
    zero = (f'<p class="nt-callout">{E(t("zero_do_note", n=e.critical_count))}</p>'
            if e.critical_count else "")
    head = (f'<div class="nt-v-head"><div><div class="nt-v-name">{s.rank}. {E(s.ghat)}</div>'
            f'<div class="nt-meta">{E(s.water_body)}{SEP}{tier_badge(s.tier, lang)}{SEP}'
            f'{E(i18n.driver(s.driver, lang))}</div></div>'
            f'<div class="nt-score" title="{E(t("help_risk"))}"><div class="n">'
            f'{s.risk_score:.1f}</div><div class="l">{E(t("risk_of"))}</div></div></div>')
    grid = (f'<div class="nt-qs">{_before_block(e, lang)}{_during_block(e, lang)}'
            f'{_sure_block(e, lang)}</div>')
    suggest = (f'<div class="nt-suggest"><div class="nt-q-title">{E(t("suggest_title"))}</div>'
               f'<p>{E(t(f"suggest_{e.action}"))}</p></div>')
    shown = (t("zero_do"), t("not_comparable"))  # already said above
    flags = [persistence_text(s, rules_by_param or {}, lang)]
    flags += [E(n) for n in flag_texts(s, lang) if not any(x in n for x in shown)]
    flags = [f for f in flags if f]
    flags_html = f'<div class="nt-flags">{" · ".join(flags)}</div>' if flags else ""
    return f'<div class="nt-verdict">{head}{zero}{grid}{suggest}{flags_html}</div>'
