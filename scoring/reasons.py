"""Plain-words reason text, filled from numbers by templates.

Rules: quote single readings or matched before/during pairs only, never
averages across different tables; give a source page for every number; no
health wording.
"""

from typing import Any

import pandas as pd

from scoring.limits import Limit, limit_text, worsen
from scoring.loader import VALUE


def num(value: float) -> str:
    """Compact number as printed: 4.3, 7.25, 0.6, 12."""
    return f"{value:g}"


def _unit(limit: Limit) -> str:
    return f" {limit.unit}" if limit.unit else ""


USER_SUPPLIED_CITE = "user-supplied reading"


def cite(year: str, *pages: str) -> str:
    """'Report 2025 p.28' or 'Report 2025 p.28/29'; uploaded rows (no page) say so."""
    real = list(dict.fromkeys(str(p).strip() for p in pages if str(p).strip()))
    if not real:
        return USER_SUPPLIED_CITE
    text = f"Report {year} p.{'/'.join(real)}"
    has_user = any(not str(p).strip() for p in pages)
    return f"{text} + user-supplied" if has_user else text


_pages = cite


def baseline_sentence(g: pd.DataFrame, parameter: str, limit: Limit) -> str | None:
    """'BOD breached its limit (...) in X of Y pre-immersion readings; worst ...'."""
    pre = g[(g["parameter"] == parameter) & (g["phase"] == "pre") & (g["status"] == VALUE)]
    breaches = pre[pre["breach"].astype(bool)]
    if breaches.empty:
        return None
    w = breaches.sort_values(["exceedance", "year"], ascending=False).iloc[0]
    return (f"{parameter} breached its limit ({limit_text(limit)}) in {len(breaches)} of "
            f"{len(pre)} pre-immersion readings; worst {num(w['value_num'])}{_unit(limit)} "
            f"({w['festival']} {w['year']}, {_pages(w['year'], w['source_page'])}).")


def worst_pair(pairs: list[dict[str, Any]], limits: dict[str, Limit]) -> dict[str, Any] | None:
    """The matched pair that got worse the most (scaled per parameter), if any got worse."""
    scored = [(worsen(limits[p["parameter"]], p["pre"], p["during"]), p) for p in pairs]
    scored = [s for s in scored if s[0] > 0]
    return max(scored, key=lambda s: (s[0], s[1]["year"]))[1] if scored else None


def pair_sentence(pair: dict[str, Any], limit: Limit) -> str:
    u = _unit(limit)
    return (f"Largest matched change during immersion: {pair['parameter']} "
            f"{num(pair['pre'])}{u} before to {num(pair['during'])}{u} during "
            f"({pair['festival']} {pair['year']}, limit {limit_text(limit)}; "
            f"{_pages(pair['year'], pair['pre_page'], pair['during_page'])}).")


def _unpaired_item(u: dict[str, Any]) -> str:
    unit = f" {u['unit']}" if u["unit"] else ""
    return (f"{u['parameter']} {num(u['value'])}{unit} ({u['festival']} {u['year']} "
            f"{u['phase']}, {_pages(u['year'], u['source_page'])}; {u['why']})")


def unpaired_sentence(unpaired: list[dict[str, Any]], examples: int = 2) -> str | None:
    """Breaching readings that could not be compared; quotes up to `examples` of them."""
    if not unpaired:
        return None
    shown = sorted(unpaired, key=lambda x: (x["exceedance"], x["year"]), reverse=True)[:examples]
    lead = "1 breaching reading was" if len(unpaired) == 1 else \
        f"{len(unpaired)} breaching readings were"
    more = f" and {len(unpaired) - len(shown)} more" if len(unpaired) > len(shown) else ""
    return (f"{lead} not compared with an earlier reading in the same table: "
            f"{'; '.join(_unpaired_item(u) for u in shown)}{more}.")


def reason_parts(
    g: pd.DataFrame, baseline_parameter: str | None, pairs: list[dict[str, Any]],
    unpaired: list[dict[str, Any]], critical_readings: list[dict[str, Any]],
    limits: dict[str, Limit],
) -> dict[str, str | None]:
    """The reason sentences, by name: critical (first), baseline, pair, unpaired."""
    pair = worst_pair(pairs, limits)
    return {
        "critical": critical_sentence(critical_readings),
        "baseline": baseline_sentence(g, baseline_parameter, limits[baseline_parameter])
        if baseline_parameter else None,
        "pair": pair_sentence(pair, limits[pair["parameter"]]) if pair else
        "No matched reading got worse during immersion." if pairs else
        "No table has both pre- and during-immersion readings to compare.",
        "unpaired": unpaired_sentence(unpaired),
    }


def critical_sentence(readings: list[dict[str, Any]]) -> str | None:
    """'Reported 0 mg/l dissolved oxygen 4 time(s) (Report 2023 p.26/60; ...)'."""
    if not readings:
        return None
    by_year: dict[str, list[str]] = {}
    for r in readings:
        by_year.setdefault(str(r["year"]), []).append(str(r["source_page"]))
    pages = "; ".join(_pages(y, *ps) for y, ps in sorted(by_year.items()))
    return (f"Reported 0 mg/l dissolved oxygen {len(readings)} time(s) ({pages}); "
            "team's own flag, not a CPCB limit.")


def reason_text(parts: dict[str, str | None]) -> str:
    """All reason sentences that apply, in a fixed order."""
    text = " ".join(p for p in parts.values() if p)
    return text or "No pre-immersion readings breached a limit."


def short_reason(parts: dict[str, str | None], worsens: bool | None, poor: bool) -> str:
    """One sentence for the ranked list: the one that matches the driver label."""
    order = ["pair", "baseline"] if worsens and not poor else ["baseline", "pair"]
    order = ["critical", *order]
    return next((parts[k] for k in order if parts[k]), reason_text(parts))
