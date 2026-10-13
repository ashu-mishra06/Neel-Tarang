"""Ghat map points and the plain-language explanation (13 Oct 2026 UI change)."""

import pandas as pd
import pytest

from scoring.config import load_rules, repo_path
from scoring.engine import score_all
from scoring.explain import _confidence_parts, _states, explain
from scoring.limits import load_limits
from scoring.loader import load_readings
from ui import ghat_map

RULES = load_rules()
REAL = repo_path(RULES["data"]["readings_csv"]).exists()


@pytest.fixture(scope="module")
def real() -> tuple:
    limits = load_limits(rules=RULES)
    return score_all(load_readings(rules=RULES), RULES, limits), limits


def test_states_never_contradict_counts() -> None:
    """Breaches below the cut-off read 'some breaches', never a bare 'no'."""
    assert _states(True, 4, True, {"x": 1}) == ("poor", "yes")
    assert _states(False, 6, False, {"x": 1}) == ("mild", "some")
    assert _states(False, 0, False, None) == ("ok", "no")
    assert _states(False, 0, None, None) == ("ok", "unknown")


def test_confidence_parts_split() -> None:
    items = ["no Durga 2025 table", "BOD, Ganesh 2025 pre: not sampled",
             "pH, Ganesh 2025 pre: *", "unpaired breach: BOD 8 mg/l, Ganesh 2025 during"]
    assert _confidence_parts(items) == (["Durga 2025"], 2, 1)


def test_short_name() -> None:
    assert ghat_map.short_name("Bairagarh (Sant Hirdaram) kund") == "Bairagarh"
    assert ghat_map.short_name("Rani Kamlapati ghat / Kamla Park kund") == "Rani Kamlapati ghat"


@pytest.mark.skipif(not REAL, reason="organisers' CSV not present")
def test_explanation_quotes_matched_pair_with_page(real: tuple) -> None:
    scores, limits = real
    e = explain(next(s for s in scores.ranked if s.ghat == "Malikhedi kund"), limits)
    assert e.pair == {"parameter": "Dissolved oxygen", "pre": "4.8", "during": "3.8",
                      "unit": "mg/l", "limit": "at least 5 mg/l", "festival": "Ganesh",
                      "year": "2024", "source": "Report 2024 p.71"}
    assert e.missing_tables == ["Durga 2025"] and e.confidence == "Low"


@pytest.mark.skipif(not REAL, reason="organisers' CSV not present")
def test_map_points_cover_every_ghat_and_blind_spots_have_no_score(real: tuple) -> None:
    scores, _ = real
    points, unplaced = ghat_map.map_points(scores, ghat_map.load_locations(), "en")
    assert unplaced == []
    assert [p["ghat"] for p in points if p["kind"] == "ranked"] == [s.ghat for s in scores.ranked]
    nobase = [p for p in points if p["kind"] == "nobase"]
    assert [p["ghat"] for p in nobase] == ["Arch Bridge"]
    assert all(p["risk"] is None and p["elevation"] == 0 and p["tier"] == "NoData"
               for p in nobase)
    # every label carries text (rank + name), so colour is never the only signal
    assert points[0]["label"].startswith("1. ")


@pytest.mark.skipif(not REAL, reason="organisers' CSV not present")
def test_unplaced_ghat_is_reported_not_dropped(real: tuple) -> None:
    scores, _ = real
    points, unplaced = ghat_map.map_points(scores, pd.DataFrame(
        columns=["data_site", "lat", "lon", "precision"]), "en")
    assert points == [] and len(unplaced) == len(scores.ranked) + len(scores.blind_spots)


@pytest.mark.skipif(not REAL, reason="organisers' CSV not present")
def test_deck_has_selectable_layers(real: tuple) -> None:
    scores, _ = real
    points, _ = ghat_map.map_points(scores, ghat_map.load_locations(), "en")
    deck = ghat_map.build_deck(points, points[0], 1, ghat_map.tooltip_html("en"))
    pickable = {layer.id for layer in deck.layers if getattr(layer, "pickable", False)}
    assert pickable == {"ghats", "nobase"}
    assert ghat_map.tour_stops(points)[0] is None  # tour starts on the overview


def test_tour_step_is_time_based() -> None:
    """Extra reruns within one interval never advance the tour."""
    s = ghat_map.TOUR_SECONDS
    assert ghat_map.tour_step(100.0, 100.0) == 0
    assert ghat_map.tour_step(100.0, 100.0 + s * 0.9) == 0
    assert ghat_map.tour_step(100.0, 100.0 + s * 2.1) == 2
    assert ghat_map.tour_step(100.0, 50.0) == 0
