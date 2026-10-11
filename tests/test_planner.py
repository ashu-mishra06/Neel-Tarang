"""7B test planner (Appendix F.2, test T12)."""

from types import SimpleNamespace

import pytest

from scoring.config import load_rules, repo_path
from scoring.planner import WHAT_TO_TEST, make_plan, priority

RULES = load_rules()
REAL = repo_path(RULES["data"]["readings_csv"]).exists()


def ghat(name: str, risk: float, coverage: float, tier: str = "High"):
    conf = SimpleNamespace(coverage=coverage, level="High", missing_items=[])
    return SimpleNamespace(ghat=name, risk_score=risk, tier=tier, confidence=conf,
                           unpaired_breaches=[], near_boundary=False, nearest_line={})


def scores(*ghats, blind=()):
    return SimpleNamespace(ranked=list(ghats),
                           blind_spots=[SimpleNamespace(ghat=b) for b in blind])


def test_priority_formula() -> None:
    assert priority(40.0, 0.75, RULES) == pytest.approx(50.0)  # 40 * (1 + 0.25)
    assert priority(40.0, 1.0, RULES) == pytest.approx(40.0)


def test_order_ties_and_n() -> None:
    s = scores(ghat("B", 40, 1.0), ghat("A", 40, 1.0), ghat("C", 32, 0.75), ghat("D", 50, 1.0))
    plan = make_plan(s, 4, True, RULES)
    # D 50; A,B,C all 40 -> C first (lower coverage), then A, B by name
    assert [i.ghat for i in plan.items] == ["D", "C", "A", "B"]
    assert [i.ghat for i in make_plan(s, 1, True, RULES).items] == ["D"]  # N=1: top only
    assert len(make_plan(s, 2, True, RULES).items) == 2


def test_deterministic() -> None:
    s = scores(ghat("B", 40, 1.0), ghat("A", 40, 1.0))
    assert [i.ghat for i in make_plan(s, 2, True, RULES).items] == \
        [i.ghat for i in make_plan(s, 2, True, RULES).items] == ["A", "B"]


def test_no_data_ghats_listed_separately_without_score() -> None:
    s = scores(ghat("A", 40, 1.0), blind=["Arch Bridge"])
    on = make_plan(s, 1, True, RULES)
    assert on.no_baseline == ["Arch Bridge"] and "Arch Bridge" not in [i.ghat for i in on.items]
    assert make_plan(s, 1, False, RULES).no_baseline == []


def test_wording_suggests_not_instructs() -> None:
    assert WHAT_TO_TEST.startswith("Data suggests testing") and "must" not in WHAT_TO_TEST


def test_n_must_be_positive() -> None:
    with pytest.raises(ValueError):
        make_plan(scores(ghat("A", 1, 1)), 0, True, RULES)


@pytest.mark.skipif(not REAL, reason="organisers' CSV not present")
def test_real_plan_and_ranking_untouched() -> None:
    from scoring.engine import score_all

    real = score_all(rules=RULES)
    before = [(s.ghat, s.rank, s.tier) for s in real.ranked]
    plan = make_plan(real, 3, True, RULES)
    assert [i.ghat for i in plan.items][0] == "Bairagarh (Sant Hirdaram) kund"
    assert plan.no_baseline == ["Arch Bridge"]
    assert [(s.ghat, s.rank, s.tier) for s in real.ranked] == before
    full = make_plan(real, 7, True, RULES)
    names = [i.ghat for i in full.items]
    assert names.index("Malikhedi kund") < names.index("Rani Kamlapati ghat / Kamla Park kund")
