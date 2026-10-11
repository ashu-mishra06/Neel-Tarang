"""UI: Appendix B contrast, labels never colour-only, and an app smoke test."""

import pytest

from scoring.config import load_rules, repo_path
from ui import components as ui
from ui.theme import MISSING, TIER


def _luminance(hex_colour: str) -> float:
    rgb = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(fg: str, bg: str) -> float:
    hi, lo = sorted((_luminance(fg), _luminance(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


@pytest.mark.parametrize("name", list(TIER))
def test_tier_pairs_meet_4_5_contrast(name: str) -> None:
    assert contrast(TIER[name]["fg"], TIER[name]["bg"]) >= 4.5


def test_missing_style_contrast() -> None:
    assert contrast(MISSING["fg"], MISSING["bg"]) >= 4.5


@pytest.mark.parametrize("tier", ["High", "Medium", "Low", "NoData"])
def test_tier_badge_has_icon_and_text(tier: str) -> None:
    badge = ui.tier_badge(tier)
    assert TIER[tier]["icon"] in badge and TIER[tier]["label"] in badge


def test_near_boundary_text() -> None:
    assert ui.near_boundary_text({"line": "High", "value": 27.5, "distance": -0.84}) == \
        "0.8 points below the High line (27.5)"


@pytest.mark.skipif(not repo_path(load_rules()["data"]["readings_csv"]).exists(),
                    reason="organisers' CSV not present")
def test_app_runs_and_shows_core_content() -> None:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(repo_path("app.py")), default_timeout=120).run()
    assert not at.exception
    text = " ".join([m.value for m in at.markdown] + [c.value for c in at.caption])
    for needle in ("Durga visarjan: 20 Oct 2026 | Standard: CPCB class B", "No baseline",
                   "Arch Bridge", "Near tier line", "Site may be two places", "not sampled",
                   "not a safety certification"):
        assert needle in text, needle
    assert len(at.tabs) == 3
