"""7A persistence badge (Appendix F.1, test T11)."""

import pandas as pd
import pytest

from scoring.config import load_rules, repo_path
from scoring.persistence import (
    INTERMITTENT,
    NEVER,
    ONE_OFF,
    REPEAT,
    TOO_FEW,
    headline,
    label_for,
)

RULES = load_rules()
REAL = repo_path(RULES["data"]["readings_csv"]).exists()


@pytest.mark.parametrize(
    "x, y, expected",
    [(5, 6, REPEAT), (4, 6, REPEAT), (3, 6, INTERMITTENT), (1, 6, ONE_OFF), (0, 6, NEVER),
     (4, 5, REPEAT), (3, 5, INTERMITTENT), (2, 3, REPEAT), (3, 2, TOO_FEW), (0, 0, TOO_FEW)],
)
def test_labels(x: int, y: int, expected: str) -> None:
    assert label_for(x, y, RULES) == expected


def _manual(ghat: str, parameter: str, phase: str, breach) -> tuple[int, int, int]:
    """Independent count straight from the organisers' CSV with plain pandas."""
    d = pd.read_csv(repo_path(RULES["data"]["readings_csv"]), dtype=str, keep_default_na=False)
    rows = d[(d["site"] == ghat) & (d["parameter"] == parameter) & (d["phase"] == phase)]
    values = pd.to_numeric(rows["value"], errors="coerce").dropna()
    return int(breach(values).sum()), len(values), int((rows["value"] == "").sum())


@pytest.mark.skipif(not REAL, reason="organisers' CSV not present")
@pytest.mark.parametrize(
    "ghat, parameter, phase, breach",
    [
        ("Bairagarh (Sant Hirdaram) kund", "Dissolved oxygen", "during", lambda v: v < 5),
        ("Bairagarh (Sant Hirdaram) kund", "BOD", "pre", lambda v: v > 3),
        ("Khatlapura ghat", "BOD", "during", lambda v: v > 3),
        ("Khatlapura ghat", "Dissolved oxygen", "pre", lambda v: v < 5),
    ],
)
def test_counts_equal_manual_count(ghat, parameter, phase, breach) -> None:
    """T11: X, Y, M equal a manual count for 2 ghats; missing tables are excluded from Y."""
    from scoring.engine import score_all

    s = next(x for x in score_all(rules=RULES).ranked if x.ghat == ghat)
    r = next(p for p in s.persistence if p["parameter"] == parameter and p["phase"] == phase)
    assert (r["breaches"], r["valid_tables"], r["missing_tables"]) == \
        _manual(ghat, parameter, phase, breach)


@pytest.mark.skipif(not REAL, reason="organisers' CSV not present")
def test_khatlapura_missing_table_shown_not_clean() -> None:
    from scoring.engine import score_all

    s = next(x for x in score_all(rules=RULES).ranked if x.ghat == "Khatlapura ghat")
    r = next(p for p in s.persistence if p["parameter"] == "BOD" and p["phase"] == "during")
    assert (r["breaches"], r["valid_tables"], r["missing_tables"]) == (4, 5, 1)
    assert headline(s.persistence)["label"] == REPEAT


@pytest.mark.skipif(not REAL, reason="organisers' CSV not present")
def test_persistence_never_changes_ranking(monkeypatch) -> None:
    """Enhancements never change the core ranking."""
    import scoring.engine as engine

    with_badge = [(s.ghat, s.rank, s.tier, s.driver, round(s.risk_score, 9))
                  for s in engine.score_all(rules=RULES).ranked]
    monkeypatch.setattr(engine, "persistence", lambda *a, **k: [])
    without = [(s.ghat, s.rank, s.tier, s.driver, round(s.risk_score, 9))
               for s in engine.score_all(rules=RULES).ranked]
    assert with_badge == without
