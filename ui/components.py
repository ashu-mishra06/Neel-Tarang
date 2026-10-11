"""UI components (Appendix B) as HTML strings built from engine output.

No Streamlit import and no scoring here: every number shown comes from the
engine's GhatScore / EvidenceRow / Gap objects.
"""

from __future__ import annotations

import base64
from html import escape
from pathlib import Path
from typing import Any

from ui.theme import CONFIDENCE_ICON, MISSING, TIER

E = escape


def tier_badge(tier: str) -> str:
    """Tier as icon + text + colour. Unknown tiers fall back to the NoData style."""
    t = TIER.get(tier, TIER["NoData"])
    return (f'<span class="vgw-badge" style="color:{t["fg"]};background:{t["bg"]};'
            f'border-color:{t["fg"]}" aria-label="Tier {E(t["label"])}">'
            f'{t["icon"]} {E(t["label"])}</span>')


def confidence_chip(level: str, coverage: float) -> str:
    return (f'<span class="vgw-chip" aria-label="Confidence {E(level)}">'
            f'{CONFIDENCE_ICON.get(level, "")} Confidence: {E(level)} '
            f'({coverage:.0%} of expected readings)</span>')


def near_boundary_text(nearest: dict[str, Any]) -> str:
    side = "below" if nearest["distance"] < 0 else "above"
    return (f'{abs(nearest["distance"]):.1f} points {side} the {nearest["line"]} line '
            f'({nearest["value"]:g})')


def flag_chips(s: Any) -> list[str]:
    """Warning chips for a ranked ghat (dashed border; text, not colour)."""
    chips = []
    if s.near_boundary:
        chips.append(f"≈ Near tier line: {near_boundary_text(s.nearest_line)}")
    if s.site_match_uncertain:
        chips.append("? Site may be two places")
    if s.critical:
        chips.append(f"! Reported 0 mg/l DO ×{s.critical.count} (team's own flag)")
    if s.unpaired_breaches:
        chips.append(f"⊘ {len(s.unpaired_breaches)} breach(es) not comparable")
    if not s.on_2026_list:
        chips.append("Not on reported 2026 list - confirm with BMC")
    return [f'<span class="vgw-chip warn">{E(c)}</span>' for c in chips]


def ghat_row(s: Any) -> str:
    """GhatRow: rank, name, water body, tier, driver, confidence, flags, one-line reason."""
    lowconf = " lowconf" if s.confidence.level == "Low" else ""
    chips = [tier_badge(s.tier), f'<span class="vgw-chip">Driver: {E(s.driver)}</span>',
             confidence_chip(s.confidence.level, s.confidence.coverage),
             f'<span class="vgw-chip">Risk score {s.risk_score:.1f} / 100</span>']
    return (f'<div class="vgw-row{lowconf}"><div class="vgw-rank">{s.rank}</div><div>'
            f'<div class="vgw-title">{E(s.ghat)}<span class="vgw-wb">{E(s.water_body)}</span>'
            f'</div><div class="vgw-chips">{"".join(chips)}</div>'
            f'<div class="vgw-chips">{"".join(flag_chips(s))}</div>'
            f'<div class="vgw-reason">{E(s.reason_short)}</div></div></div>')


def no_baseline_card(name: str, why: str) -> str:
    return (f'<div class="vgw-row">{tier_badge("NoData")}<div>'
            f'<div class="vgw-title">{E(name)}</div>'
            f'<div class="vgw-reason">{E(why)}. No score and no tier. Any test here is new '
            f'information.</div></div></div>')


def gap_card(gap: Any) -> str:
    """GapCard: title, one-line explanation, affected ghats, items."""
    ghats = f'<div class="vgw-muted">Affects: {E(", ".join(gap.ghats))}</div>' if gap.ghats else ""
    items = "".join(f"<li>{E(i)}</li>" for i in gap.items)
    return (f'<div class="vgw-card"><h4>⚑ {E(gap.title)}</h4>'
            f'<div class="vgw-reason">{E(gap.detail)}</div>{ghats}'
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
