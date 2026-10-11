"""Matched before/during pairs, the physical "worsens" anchor, and unpaired breaches.

A matched pair is one festival-year table with a valid PRE and a valid DURING
reading for the same parameter. Averages are only ever taken over matched
pairs, never across different tables.
"""

from typing import Any

import pandas as pd

from scoring.limits import Limit
from scoring.loader import VALUE

Key = tuple[str, str, str]  # (festival, year, parameter)


def table_readings(g: pd.DataFrame, limits: dict[str, Limit]) -> dict[Key, dict[str, Any]]:
    """Valid scored readings grouped by table: {(festival, year, parameter): {phase: row}}."""
    valid = g[(g["status"] == VALUE) & g["parameter"].isin(limits)]
    tables: dict[Key, dict[str, Any]] = {}
    for row in valid.itertuples():
        tables.setdefault((row.festival, row.year, row.parameter), {})[row.phase] = row
    return tables


def physical_worsening(limit: Limit, pre: float, during: float) -> float:
    """Signed change in the 'worse' direction, in the parameter's own units.

    DO: pre - during. BOD: during - pre. pH: change in distance outside 6.5-8.5.
    """
    if limit.rule == "min":
        return pre - during
    if limit.rule == "max":
        return during - pre
    return limit.distance_outside(during) - limit.distance_outside(pre)


def matched_pairs(g: pd.DataFrame, limits: dict[str, Limit]) -> list[dict[str, Any]]:
    """Every table with valid pre and during readings, with its source pages."""
    out = []
    for (festival, year, parameter), phases in sorted(table_readings(g, limits).items()):
        if "pre" not in phases or "during" not in phases:
            continue
        pre, during, limit = phases["pre"], phases["during"], limits[parameter]
        out.append({
            "festival": festival, "year": year, "parameter": parameter,
            "pre": float(pre.value_num), "during": float(during.value_num),
            "pre_page": pre.source_page, "during_page": during.source_page,
            "worsening": physical_worsening(limit, pre.value_num, during.value_num),
            "pre_breach": bool(pre.breach), "during_breach": bool(during.breach),
        })
    return out


def anchor_by_parameter(
    pairs: list[dict[str, Any]], limits: dict[str, Limit], rules: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    """Per parameter: matched-pair means and whether the physical anchor is met."""
    cfg = rules["scoring"]["driver"]
    out = {}
    for name, limit in limits.items():
        mine = [p for p in pairs if p["parameter"] == name]
        if not mine:
            continue
        n = len(mine)
        mean_pre = sum(p["pre"] for p in mine) / n
        mean_during = sum(p["during"] for p in mine) / n
        mean_worse = sum(p["worsening"] for p in mine) / n
        crossing = bool(cfg["crossing"]) and limit.distance_outside(mean_pre) == 0 \
            and limit.distance_outside(mean_during) > 0
        threshold = cfg["worsening_mg_l"].get(name)
        by_size = threshold is not None and mean_worse >= threshold
        out[name] = {
            "pairs": n, "paired_pre_mean": mean_pre, "paired_during_mean": mean_during,
            "mean_worsening": mean_worse, "crossing": crossing,
            "meets_anchor": by_size or crossing,
            "because": ([f"mean worsening {mean_worse:.2f} >= {threshold:g}"] if by_size else [])
            + (["paired mean crosses the limit"] if crossing else []),
        }
    return out


def worsens(anchor: dict[str, dict[str, Any]]) -> tuple[bool | None, list[str]]:
    """(True/False, triggering parameters), or (None, []) if there are no matched pairs."""
    if not anchor:
        return None, []
    hits = [f"{name}: {'; '.join(a['because'])}" for name, a in anchor.items() if a["meets_anchor"]]
    return bool(hits), hits


def unpaired_breaches(g: pd.DataFrame, limits: dict[str, Limit]) -> list[dict[str, Any]]:
    """During/after readings that breach but are not used in any festival comparison.

    These do not change the score. They lower confidence and are shown as
    evidence, so a breach is never dropped silently.
    """
    tables = table_readings(g, limits)
    out = []
    for key, phases in sorted(tables.items()):
        for phase in ("during", "after"):
            row = phases.get(phase)
            if row is None or not bool(row.breach):
                continue
            if "pre" not in phases:
                why = "no valid pre-immersion reading in this table"
            elif phase == "after" and "during" not in phases:
                why = "no valid during-immersion reading in this table"
            else:
                continue
            festival, year, parameter = key
            out.append({
                "parameter": parameter, "value": float(row.value_num),
                "unit": limits[parameter].unit, "festival": festival, "year": year,
                "phase": phase, "source_page": row.source_page,
                "exceedance": float(row.exceedance), "why": why,
            })
    return out
