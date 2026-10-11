"""Matched pairs, physical driver anchor, near-boundary flag, unpaired breaches, reason text."""

import pandas as pd
import pytest

from scoring.config import load_rules, repo_path
from scoring.engine import confidence_for, near_boundary, score_all
from scoring.limits import evaluate_frame, limits_from_rules
from scoring.loader import MISSING, VALUE
from scoring.pairs import anchor_by_parameter, matched_pairs, unpaired_breaches, worsens

RULES = load_rules()
LIMITS = limits_from_rules(RULES)
NO_DESIGNATED = pd.DataFrame(columns=["ghat_name", "data_site"])


def frame(rows: list[tuple], ghat: str = "G") -> pd.DataFrame:
    """rows: (festival, year, phase, parameter, value or None, page)."""
    records = [{
        "ghat": ghat, "water_body": "Kund", "festival": f, "year": str(y), "phase": ph,
        "parameter": prm, "flag": "" if v is not None else "not sampled",
        "status": VALUE if v is not None else MISSING, "value_num": v,
        "source_page": str(page), "site_match_confidence": "high",
    } for f, y, ph, prm, v, page in rows]
    return evaluate_frame(pd.DataFrame(records), LIMITS)


def do_tables(tables: list[tuple[str, int, float | None, float | None, float | None]]):
    """(festival, year, pre, during, after) for DO; BOD and pH steady and compliant."""
    rows = []
    for festival, year, pre, during, after in tables:
        page = 20 + year % 100
        for phase, value in (("pre", pre), ("during", during), ("after", after)):
            rows += [(festival, year, phase, "Dissolved oxygen", value, page),
                     (festival, year, phase, "BOD", 2.0, page),
                     (festival, year, phase, "pH", 7.5, page)]
    return frame(rows)


# Malikhedi-shaped: two matched DO pairs plus an unpaired 0.6 during reading.
MALIKHEDI_LIKE = [
    ("Durga", 2023, 4.6, 4.3, 4.3),
    ("Ganesh", 2024, 4.8, 3.8, 3.8),
    ("Ganesh", 2025, None, 0.6, None),
]


# ---------- 1. reason quotes matched pairs only ----------


def test_reason_quotes_matched_pair_not_cross_table_averages() -> None:
    (g,) = score_all(do_tables(MALIKHEDI_LIKE), RULES, LIMITS, NO_DESIGNATED).ranked
    assert "Dissolved oxygen 4.8 mg/l before to 3.8 mg/l during (Ganesh 2024" in g.reason
    assert "Report 2024 p.44" in g.reason  # page of that table
    # Cross-table averages: pre (4.6+4.8)/2 = 4.7; during (4.3+3.8+0.6)/3 = 2.9
    assert "4.7" not in g.reason and "2.9" not in g.reason
    assert "averaged" not in g.reason


def test_reason_mentions_unpaired_reading_with_page_and_cause() -> None:
    (g,) = score_all(do_tables(MALIKHEDI_LIKE), RULES, LIMITS, NO_DESIGNATED).ranked
    assert "Dissolved oxygen 0.6 mg/l (Ganesh 2025 during, Report 2025 p.45; " \
           "no valid pre-immersion reading in this table)" in g.reason


def test_reason_numbers_all_trace_to_single_readings() -> None:
    df = do_tables(MALIKHEDI_LIKE)
    (g,) = score_all(df, RULES, LIMITS, NO_DESIGNATED).ranked
    import re

    printed = {float(x) for x in re.findall(r"(?<![\w.])\d+\.\d+(?![\w.])", g.reason)}
    readings = set(df.loc[df["status"] == VALUE, "value_num"].astype(float))
    assert printed <= readings, printed - readings


# ---------- 2. physical driver anchor ----------


@pytest.mark.parametrize(
    "tables, expected",
    [
        ([("Durga", 2023, 7.5, 6.4, 6.4)], True),   # DO drop 1.1 >= 1.0 mg/l
        ([("Durga", 2023, 7.5, 6.6, 6.6)], False),  # DO drop 0.9, still within limit
        ([("Durga", 2023, 5.4, 4.9, 4.9)], True),   # drop 0.5 but crosses 5 mg/l
        ([("Durga", 2023, 4.5, 4.0, 4.0)], False),  # already below limit: no crossing, drop 0.5
        ([("Durga", 2023, 6.0, 4.0, 4.0), ("Ganesh", 2023, 6.0, 7.5, 7.5)], False),  # mean 0.25
    ],
)
def test_do_anchor(tables, expected: bool) -> None:
    anchor = anchor_by_parameter(matched_pairs(do_tables(tables), LIMITS), LIMITS, RULES)
    assert worsens(anchor)[0] is expected


def test_bod_anchor_at_exactly_one_mg_l() -> None:
    rows = [("Durga", 2023, "pre", "BOD", 4.0, 30), ("Durga", 2023, "during", "BOD", 5.0, 30)]
    worse, because = worsens(anchor_by_parameter(matched_pairs(frame(rows), LIMITS), LIMITS, RULES))
    assert worse is True and because[0].startswith("BOD")


def test_ph_crossing_counts() -> None:
    rows = [("Durga", 2023, "pre", "pH", 8.3, 30), ("Durga", 2023, "during", "pH", 8.7, 30)]
    worse, because = worsens(anchor_by_parameter(matched_pairs(frame(rows), LIMITS), LIMITS, RULES))
    assert worse is True and "crosses" in because[0]


def test_no_matched_pairs_means_unknown_not_false() -> None:
    rows = [("Durga", 2023, "during", "BOD", 9.0, 30), ("Ganesh", 2023, "pre", "BOD", 2.0, 30)]
    assert worsens(anchor_by_parameter(matched_pairs(frame(rows), LIMITS), LIMITS, RULES)) \
        == (None, [])


def test_driver_uses_anchor_not_festival_score() -> None:
    """A large scaled festival score from a small mg/l change does not trigger 'worsens'."""
    rows = []
    for phase, bod in (("pre", 4.0), ("during", 4.9), ("after", 4.9)):
        rows += [("Durga", 2023, phase, "BOD", bod, 30)]
    (g,) = score_all(frame(rows), RULES, LIMITS, NO_DESIGNATED).ranked
    assert g.festival == pytest.approx(0.3)  # 0.9 / 3: above the retired 0.15 cut-off
    assert g.worsens is False and g.driver == "Already poor before immersion"


# ---------- 3. near-boundary ----------


@pytest.mark.parametrize(
    "risk, near, line",
    [(26.5, True, "High"), (29.0, True, "High"), (29.01, False, "High"),
     (24.0, False, "High"), (20.3, True, "Medium"), (18.5, True, "Medium")],
)
def test_near_boundary(risk: float, near: bool, line: str) -> None:
    is_near, nearest = near_boundary(risk, RULES)
    assert is_near is near and nearest["line"] == line
    assert nearest["distance"] == pytest.approx(risk - nearest["value"])


# ---------- 4. unpaired breaches ----------


def test_unpaired_breaches_listed_with_details() -> None:
    (u,) = [x for x in unpaired_breaches(do_tables(MALIKHEDI_LIKE), LIMITS)]
    assert (u["parameter"], u["value"], u["festival"], u["year"], u["phase"], u["source_page"]) \
        == ("Dissolved oxygen", 0.6, "Ganesh", "2025", "during", "45")
    assert "pre" in u["why"]


def test_after_breach_without_during_is_unpaired() -> None:
    rows = [("Durga", 2023, "pre", "BOD", 2.0, 59), ("Durga", 2023, "during", "BOD", None, 59),
            ("Durga", 2023, "after", "BOD", 7.8, 59)]
    (u,) = unpaired_breaches(frame(rows), LIMITS)
    assert u["phase"] == "after" and "during" in u["why"]


def test_paired_or_compliant_readings_are_not_unpaired() -> None:
    rows = [("Durga", 2023, "pre", "BOD", 5.0, 30), ("Durga", 2023, "during", "BOD", 9.0, 30),
            ("Durga", 2023, "after", "BOD", 9.0, 30),            # paired breaches
            ("Ganesh", 2023, "during", "BOD", 2.0, 31)]          # unpaired but compliant
    assert unpaired_breaches(frame(rows), LIMITS) == []


def test_unpaired_breaches_do_not_change_score_but_lower_confidence() -> None:
    with_extra = score_all(do_tables(MALIKHEDI_LIKE), RULES, LIMITS, NO_DESIGNATED).ranked[0]
    without = score_all(do_tables(MALIKHEDI_LIKE[:2] + [("Ganesh", 2025, None, 6.0, None)]),
                        RULES, LIMITS, NO_DESIGNATED).ranked[0]
    assert with_extra.risk_score == pytest.approx(without.risk_score)
    assert with_extra.confidence.downgraded_for_unpaired
    assert not without.confidence.downgraded_for_unpaired
    assert any("unpaired breach" in m for m in with_extra.confidence.missing_items)


def test_confidence_downgrade_floors_at_low() -> None:
    df = do_tables(MALIKHEDI_LIKE)
    unpaired = unpaired_breaches(df, LIMITS)
    tables = [(f, str(y)) for y in (2023, 2024, 2025) for f in ("Ganesh", "Durga")]
    c = confidence_for(df, tables, ("Durga", "2025"), 3, RULES, unpaired)
    assert c.level == "Low"


# ---------- real data ----------

REAL = repo_path(RULES["data"]["readings_csv"]).exists()


@pytest.mark.skipif(not REAL, reason="organisers' CSV not present")
def test_real_malikhedi_unpaired_06_is_reported() -> None:
    by = {s.ghat: s for s in score_all(rules=RULES).ranked}
    m = by["Malikhedi kund"]
    hit = [u for u in m.unpaired_breaches if u["parameter"] == "Dissolved oxygen"]
    assert [(u["value"], u["festival"], u["year"], u["source_page"]) for u in hit] \
        == [(0.6, "Ganesh", "2025", "29")]
    assert "0.6 mg/l" in m.reason and "averaged" not in m.reason
