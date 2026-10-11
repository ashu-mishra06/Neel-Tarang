"""Loader status rules (T2, T3) and limit formulas on tiny hand-made data."""

import pandas as pd
import pytest

from scoring.config import load_rules
from scoring.limits import evaluate, evaluate_frame, limits_from_rules, load_limits
from scoring.loader import (
    BELOW_DETECTION,
    MISSING,
    VALUE,
    SchemaError,
    classify,
    load_readings,
)

RULES = load_rules()
HEADER = "ghat,parameter,value,flag,year,festival,phase,source_page\n"


def write_csv(tmp_path, body: str, header: str = HEADER):
    path = tmp_path / "r.csv"
    path.write_text(header + body, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "value, flag, expected",
    [
        ("4.2", "", VALUE),
        ("0", "", VALUE),
        ("", "not sampled", MISSING),
        ("", " Not Sampled ", MISSING),
        ("", "*", MISSING),
        ("", "**", MISSING),
        ("", "", MISSING),
        ("not sampled", "", MISSING),
        ("", "BDL", BELOW_DETECTION),
        ("", "nd", BELOW_DETECTION),
        ("0", "BDL", BELOW_DETECTION),
        ("abc", "", MISSING),
    ],
)
def test_classify(value: str, flag: str, expected: str) -> None:
    assert classify(value, flag, RULES) == expected


def test_load_readings_status_and_numbers(tmp_path) -> None:
    path = write_csv(tmp_path, (
        "A,Dissolved oxygen,3.8,,2023,Durga,pre,40\n"
        "A,BOD,,not sampled,2023,Durga,pre,40\n"
        "A,Lead,,BDL,2023,Durga,pre,40\n"
        "A,pH,,*,2023,Durga,During,40\n"
    ))
    df = load_readings(path, RULES)
    assert list(df["status"]) == [VALUE, MISSING, BELOW_DETECTION, MISSING]
    assert df["value_num"].iloc[0] == 3.8
    assert df["value_num"].iloc[1:].isna().all()  # BDL is never 0
    assert df["phase"].iloc[3] == "during"
    assert df.attrs["issues"] == []


def test_bdl_on_scored_parameter_warns_and_is_recorded(tmp_path) -> None:
    path = write_csv(tmp_path, "A,BOD,,BDL,2024,Ganesh,pre,30\n")
    with pytest.warns(UserWarning):
        df = load_readings(path, RULES)
    assert df.attrs["issues"][0]["type"] == "bdl_on_scored_parameter"


def test_missing_column_gives_clear_error(tmp_path) -> None:
    path = write_csv(tmp_path, "A,BOD,3\n", header="ghat,parameter,value\n")
    with pytest.raises(SchemaError, match="year"):
        load_readings(path, RULES)


def test_alternative_column_names(tmp_path) -> None:
    header = "ghat_name,parameter,value,flag,year,festival,phase,page\n"
    df = load_readings(write_csv(tmp_path, "A,BOD,5,,2023,Durga,pre,40\n", header), RULES)
    assert df["ghat"].iloc[0] == "A" and df["source_page"].iloc[0] == "40"


LIMITS = limits_from_rules(RULES)


@pytest.mark.parametrize(
    "parameter, value, breach, exceedance",
    [
        ("Dissolved oxygen", 5.0, False, 0.0),
        ("Dissolved oxygen", 2.5, True, 0.5),
        ("Dissolved oxygen", 0.0, True, 1.0),
        ("Dissolved oxygen", 9.0, False, 0.0),
        ("BOD", 3.0, False, 0.0),
        ("BOD", 4.5, True, 0.5),
        ("BOD", 12.0, True, 1.0),
        ("pH", 7.0, False, 0.0),
        ("pH", 6.5, False, 0.0),
        ("pH", 9.25, True, 0.5),
        ("pH", 5.0, True, 1.0),
    ],
)
def test_evaluate(parameter: str, value: float, breach: bool, exceedance: float) -> None:
    result = evaluate(parameter, value, LIMITS)
    assert result["breach"] is breach
    assert result["exceedance"] == pytest.approx(exceedance)


def test_evaluate_refuses_missing() -> None:
    with pytest.raises(ValueError):
        evaluate("BOD", float("nan"), LIMITS)


def test_not_sampled_never_clean(tmp_path) -> None:
    """T2: missing readings get breach=NA, never False."""
    path = write_csv(tmp_path, (
        "A,BOD,,not sampled,2023,Durga,pre,40\n"
        "A,Dissolved oxygen,,**,2023,Durga,pre,40\n"
        "A,BOD,2,,2023,Durga,during,41\n"
    ))
    scored = evaluate_frame(load_readings(path, RULES), LIMITS)
    assert scored["breach"].iloc[:2].isna().all()
    assert not (scored["breach"].iloc[:2] == False).any()  # noqa: E712
    assert bool(scored["breach"].iloc[2]) is False


def test_load_limits_without_csv_uses_rules(tmp_path) -> None:
    limits = load_limits(tmp_path / "absent.csv", RULES)
    assert limits["Dissolved oxygen"].low == 5.0 and limits["BOD"].high == 3.0


CRITERIA_HEADER = "class,designated_best_use,parameter,limit_type,limit,unit\n"
CLASS_B = (
    "B,Outdoor bathing,pH,range,6.5-8.5,\n"
    "B,Outdoor bathing,Dissolved oxygen,min,5,mg/l\n"
    "B,Outdoor bathing,BOD (5 days 20C),max,3,mg/l\n"
)


def test_load_limits_checks_csv(tmp_path) -> None:
    good = tmp_path / "c.csv"
    good.write_text(CRITERIA_HEADER + CLASS_B + "A,Drinking,BOD (5 days 20C),max,2,mg/l\n")
    assert set(load_limits(good, RULES)) == {"pH", "Dissolved oxygen", "BOD"}


@pytest.mark.parametrize(
    "body",
    [
        CLASS_B.replace("min,5,", "min,4,"),  # limit differs
        CLASS_B.replace("B,Outdoor bathing,BOD", "A,Drinking,BOD"),  # BOD absent from class B
    ],
)
def test_load_limits_rejects_mismatch(tmp_path, body: str) -> None:
    bad = tmp_path / "b.csv"
    bad.write_text(CRITERIA_HEADER + body)
    with pytest.raises(ValueError, match="CPCB criteria CSV"):
        load_limits(bad, RULES)


def test_real_criteria_csv_matches_rules() -> None:
    """The organisers' CPCB file agrees with rules.yaml (if present)."""
    from scoring.config import repo_path

    path = repo_path(RULES["data"]["limits_csv"])
    if not path.exists():
        pytest.skip("criteria CSV not present")
    assert load_limits(path, RULES)["BOD"].high == 3.0


def test_frame_ignores_unscored_parameters() -> None:
    df = pd.DataFrame({"parameter": ["COD"], "status": [VALUE], "value_num": [50.0]})
    assert evaluate_frame(df, LIMITS)["breach"].isna().all()
