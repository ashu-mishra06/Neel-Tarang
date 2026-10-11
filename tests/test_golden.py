"""Gate G1 / test T1: golden numbers from the organisers' CSV."""

import pytest

from scoring.config import load_rules, repo_path
from scoring.limits import evaluate_frame, load_limits
from scoring.loader import VALUE, load_readings

READINGS = repo_path(load_rules()["data"]["readings_csv"])

pytestmark = pytest.mark.skipif(
    not READINGS.exists(), reason=f"organisers' CSV not found at {READINGS} - G1 NOT verified"
)


@pytest.fixture(scope="module")
def scored():
    return evaluate_frame(load_readings(), load_limits())


@pytest.mark.parametrize(
    "parameter, valid, breaches",
    [("Dissolved oxygen", 116, 42), ("BOD", 112, 100)],
)
def test_golden_counts(scored, parameter: str, valid: int, breaches: int) -> None:
    rows = scored[(scored["parameter"] == parameter) & (scored["status"] == VALUE)]
    assert len(rows) == valid
    assert int(rows["breach"].sum()) == breaches


def test_expected_cells_per_parameter(scored) -> None:
    for parameter in ["pH", "Dissolved oxygen", "BOD"]:
        assert (scored["parameter"] == parameter).sum() == 120


def test_no_bdl_on_scored_parameters(scored) -> None:
    assert scored.attrs.get("issues", []) == []
