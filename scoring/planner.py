"""7B test planner (core.txt Appendix F.2): "I can test N ghats before 20 Oct".

priority = risk_score * (1 + u_weight * (1 - coverage)): high risk AND thin data
come first. Ties: lower coverage first, then name. Designated ghats with no
data are listed separately ("No baseline") and never get a score or a tier.
Display only: nothing here feeds the ranking. Wording: "data suggests testing".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

WHAT_TO_TEST = ("Data suggests testing dissolved oxygen, BOD and pH before immersion "
                "(before 20 Oct), and again during immersion on the day.")


@dataclass
class PlanItem:
    ghat: str
    rank_in_plan: int
    priority: float
    risk_score: float
    tier: str
    coverage: float
    uncertainty: float
    confidence: str
    reasons: list[str] = field(default_factory=list)
    missing_tables: list[str] = field(default_factory=list)  # e.g. "Durga 2025"
    unpaired: int = 0
    near_line: str | None = None


@dataclass
class Plan:
    n: int
    items: list[PlanItem]
    no_baseline: list[str]
    what_to_test: str = WHAT_TO_TEST


def priority(risk: float, coverage: float, rules: dict[str, Any]) -> float:
    return risk * (1 + rules["planner"]["u_weight"] * (1 - coverage))


def _reasons(s: Any) -> list[str]:
    """Plain reasons built from engine numbers only."""
    out = [f"{s.tier} tier, risk {s.risk_score:.1f}",
           f"data coverage {s.confidence.coverage:.0%} ({s.confidence.level} confidence)"]
    out += [m for m in s.confidence.missing_items if m.startswith("no ") and m.endswith(" table")]
    if s.unpaired_breaches:
        out.append(f"{len(s.unpaired_breaches)} breach(es) with no earlier reading to compare")
    if s.near_boundary:
        out.append(f"score near the {s.nearest_line['line']} tier line")
    return out


def make_plan(scores: Any, n: int, include_no_data: bool, rules: dict[str, Any]) -> Plan:
    """The first n ghats by priority, plus the separate 'No baseline' list."""
    if n < 1:
        raise ValueError("n must be at least 1")
    ordered = sorted(scores.ranked, key=lambda s: (
        -round(priority(s.risk_score, s.confidence.coverage, rules), 9),
        s.confidence.coverage, s.ghat))
    items = [PlanItem(ghat=s.ghat, rank_in_plan=i, priority=priority(
                 s.risk_score, s.confidence.coverage, rules),
                 risk_score=s.risk_score, tier=s.tier, coverage=s.confidence.coverage,
                 uncertainty=1 - s.confidence.coverage, confidence=s.confidence.level,
                 reasons=_reasons(s),
                 missing_tables=[m.removeprefix("no ").removesuffix(" table")
                                 for m in s.confidence.missing_items
                                 if m.startswith("no ") and m.endswith(" table")],
                 unpaired=len(s.unpaired_breaches),
                 near_line=s.nearest_line["line"] if s.near_boundary else None)
             for i, s in enumerate(ordered[:n], start=1)]
    no_baseline = [b.ghat for b in scores.blind_spots] if include_no_data else []
    return Plan(n=n, items=items, no_baseline=no_baseline)
