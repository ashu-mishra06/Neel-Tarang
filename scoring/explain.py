"""Plain-language facts behind one ghat's rank, for the detail view and map.

Answers the three questions an officer asks, using engine output only:
  1 Was the water already poor before immersion?   (baseline part)
  2 Did it get worse during immersion?              (festival part, matched pairs)
  3 How sure are we?                                (confidence)
Numbers are formatted here once, so English and Hindi show the same strings.
No new scoring: every value is read from GhatScore.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from scoring.limits import Limit, limit_text
from scoring.reasons import cite, num, worst_pair

# What the readings point to, keyed by (poor before, worse during).
ACTIONS = {(True, True): "both", (True, False): "baseline", (False, True): "festival"}


@dataclass
class Explanation:
    """Shared facts for one ranked ghat; the UI words them in EN or HI."""

    poor_before: bool
    before_state: str  # poor | mild (breaches, small margins) | ok
    during_state: str  # yes | some (a pair worsened, below the anchor) | no | unknown
    baseline: str  # baseline part and its cut-off, pre-formatted
    baseline_cutoff: str
    before_parameter: str
    before_breaches: int
    before_valid: int
    before_limit: str
    worsens: bool | None  # None = no matched before/during pairs
    pair: dict[str, str] | None  # largest matched worsening, pre-formatted
    action: str  # both | baseline | festival | watch
    confidence: str
    coverage_pct: str
    missing_tables: list[str] = field(default_factory=list)
    not_sampled: int = 0
    unpaired: int = 0
    site_uncertain: bool = False
    critical_count: int = 0


def _before(s: Any, limits: dict[str, Limit]) -> tuple[str, int, int, str]:
    """The parameter with the highest share of pre-immersion breaches."""
    valid = [p for p in s.parameters if p.pre_valid]
    if not valid:
        return "", 0, 0, ""
    top = max(valid, key=lambda p: (p.pre_breaches / p.pre_valid, p.pre_breaches))
    return top.parameter, top.pre_breaches, top.pre_valid, limit_text(limits[top.parameter])


def _pair(s: Any, limits: dict[str, Limit]) -> dict[str, str] | None:
    pair = worst_pair(s.matched_pairs, limits)
    if pair is None:
        return None
    limit = limits[pair["parameter"]]
    return {"parameter": pair["parameter"], "pre": num(pair["pre"]),
            "during": num(pair["during"]), "unit": limit.unit,
            "limit": limit_text(limit), "festival": pair["festival"],
            "year": str(pair["year"]),
            "source": cite(pair["year"], pair["pre_page"], pair["during_page"])}


def _confidence_parts(items: list[str]) -> tuple[list[str], int, int]:
    """Split confidence.missing_items into missing tables, empty cells, unpaired breaches."""
    tables = [i[3:-6] for i in items if i.startswith("no ") and i.endswith(" table")]
    unpaired = sum(i.startswith("unpaired breach") for i in items)
    return tables, len(items) - len(tables) - unpaired, unpaired


def _states(poor: bool, breaches: int, worse: bool | None,
            pair: dict[str, str] | None) -> tuple[str, str]:
    before = "poor" if poor else ("mild" if breaches else "ok")
    if worse is None:
        return before, "unknown"
    return before, "yes" if worse else ("some" if pair else "no")


def explain(s: Any, limits: dict[str, Limit]) -> Explanation:
    """Explanation for one GhatScore."""
    param, breaches, valid, limit = _before(s, limits)
    poor = bool(s.driver_detail.get("poor_before"))
    worse, pair = s.worsens, _pair(s, limits)
    before_state, during_state = _states(poor, breaches, worse, pair)
    tables, not_sampled, unpaired = _confidence_parts(s.confidence.missing_items)
    d = s.driver_detail
    return Explanation(
        poor_before=poor, before_state=before_state, during_state=during_state,
        baseline="—" if d.get("baseline") is None else f"{d['baseline']:.2f}",
        baseline_cutoff=f"{d['baseline_cutoff']:g}", before_parameter=param,
        before_breaches=breaches,
        before_valid=valid, before_limit=limit, worsens=worse, pair=pair,
        action=ACTIONS.get((poor, bool(worse)), "watch"),
        confidence=s.confidence.level, coverage_pct=f"{s.confidence.coverage:.0%}",
        missing_tables=tables, not_sampled=not_sampled, unpaired=unpaired,
        site_uncertain=s.site_match_uncertain,
        critical_count=s.critical.count if s.critical else 0)
