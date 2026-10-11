"""7A persistence badge (core.txt Appendix F.1): repeat vs one-off breaches.

For each ghat x scored parameter x phase (during, pre):
  Y = festival-year tables with a VALID reading
  X = how many of those readings breach the class B limit
  M = tables where the reading is missing (shown, never counted as clean)
Display only. Nothing here feeds the risk score, tier, driver or ranking.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from scoring.limits import Limit
from scoring.loader import VALUE

REPEAT, ONE_OFF, INTERMITTENT, NEVER, TOO_FEW = (
    "Repeat", "One-off", "Intermittent", "Never breached", "Too few tables")


def label_for(x: int, y: int, rules: dict[str, Any]) -> str:
    """Appendix F.1 labels, plus 'Never breached' for X = 0 (the spec leaves it open)."""
    cfg = rules["persistence"]
    if y < cfg["min_tables"]:
        return TOO_FEW
    num, den = cfg["repeat_fraction"]
    if x >= -(-num * y // den):  # ceil(num/den * y) without floating-point error
        return REPEAT
    if x == 1:
        return ONE_OFF
    if x == 0:
        return NEVER
    return INTERMITTENT


def persistence(g: pd.DataFrame, limits: dict[str, Limit], rules: dict[str, Any]
                ) -> list[dict[str, Any]]:
    """One record per scored parameter and phase, for one ghat (an evaluated frame)."""
    out = []
    for phase in rules["persistence"]["phases"]:
        for name in limits:
            rows = g[(g["parameter"] == name) & (g["phase"] == phase)]
            valid = rows[rows["status"] == VALUE]
            x, y = int(valid["breach"].astype(bool).sum()), len(valid)
            out.append({"parameter": name, "phase": phase, "breaches": x, "valid_tables": y,
                        "missing_tables": int((rows["status"] != VALUE).sum()),
                        "label": label_for(x, y, rules)})
    return out


def headline(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The during-phase record to show on the ghat row: a Repeat first, then most breaches."""
    during = [r for r in records if r["phase"] == "during" and r["breaches"] > 0]
    if not during:
        return None
    return max(during, key=lambda r: (r["label"] == REPEAT, r["breaches"], r["valid_tables"]))


def badge_text(r: dict[str, Any], limit: Limit) -> str:
    """'Repeat: BOD above limit during immersion in 5 of 6 tables (0 not sampled)'."""
    word = {"min": "below", "max": "above"}.get(limit.rule, "outside")
    return (f"{r['label']}: {r['parameter']} {word} limit {r['phase']} immersion in "
            f"{r['breaches']} of {r['valid_tables']} tables ({r['missing_tables']} not sampled)")
