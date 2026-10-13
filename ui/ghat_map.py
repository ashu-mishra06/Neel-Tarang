"""Ghat map for the Overview page: 3D columns (height = risk score), an
auto-tour that flies from ghat to ghat in rank order, and click-to-select.

Positions come from data/context/ghat_locations.csv (sources and precision
recorded per row). The map shows engine output only; no-baseline ghats are
drawn as a grey ring and never get a column, score or tier.
The base map needs internet; pins, labels and selection work offline.
"""

from __future__ import annotations

import re
import time
from typing import Any

import pandas as pd
import pydeck as pdk
import streamlit as st

from scoring.config import repo_path
from ui import components as ui
from ui import i18n
from ui.theme import COLOR, TIER

LOCATIONS = "data/context/ghat_locations.csv"
MAP_KEY = "ghat_map"
TOUR_KEY = "map_tour"
STEP_KEY = "map_t0"  # clock time the tour (re)started; the stop is derived from elapsed time
PICK_KEY = "pick_ghat"  # read by the detail selector on the next run
SEEN_KEY = "map_seen"  # ghat the camera rests on when the tour is off
PAUSE_KEY = "map_pause"  # set inside the fragment, applied before the toggle renders
ROUND_KEY = "map_round"  # bumps the chart key after a click, which clears its selection
TOUR_SECONDS = 5.0
FLY_MS = 3500
OVERVIEW = {"zoom": 10.7, "pitch": 35, "bearing": 0}
FOCUS = {"zoom": 13.2, "pitch": 55}
ELEVATION_PER_POINT = 14  # metres of column per risk point
CROWDED = 0.015  # degrees: closer neighbours push the label to the far side


def short_name(ghat: str) -> str:
    """'Bairagarh (Sant Hirdaram) kund' -> 'Bairagarh'; 'X ghat / Y kund' -> 'X ghat'."""
    return re.split(r" \(| /", ghat)[0].strip()


def rgb(hex_colour: str, alpha: int = 255) -> list[int]:
    return [int(hex_colour[i:i + 2], 16) for i in (1, 3, 5)] + [alpha]


def load_locations(path: str = LOCATIONS) -> pd.DataFrame:
    file = repo_path(path)
    if not file.exists():
        return pd.DataFrame(columns=["data_site", "lat", "lon", "precision"])
    return pd.read_csv(file)


def map_points(scores: Any, locations: pd.DataFrame, lang: str) -> tuple[list[dict], list[str]]:
    """One point per ranked ghat and per blind spot that has a location, in tour order.

    Returns (points, names without a location). Blind spots carry no score or tier.
    """
    where = {r.data_site: r for r in locations.itertuples()}
    points, unplaced = [], []
    entries = [(s.ghat, s) for s in scores.ranked] + [(b.ghat, None) for b in scores.blind_spots]
    for ghat, s in entries:
        loc = where.get(ghat)
        if loc is None:
            unplaced.append(ghat)
            continue
        tier = s.tier if s else "NoData"
        approx = loc.precision != "mapped"
        label = f"{s.rank}. {short_name(ghat)}" if s else short_name(ghat)
        points.append({
            "ghat": ghat, "label": label, "lat": float(loc.lat), "lon": float(loc.lon),
            "kind": "ranked" if s else "nobase", "rank": s.rank if s else None,
            "tier": tier, "tier_text": i18n.tier(tier, lang),
            "risk": round(s.risk_score, 1) if s else None,
            "risk_text": f"{s.risk_score:.1f}" if s else "—",
            "elevation": s.risk_score * ELEVATION_PER_POINT if s else 0,
            "label_z": (s.risk_score * ELEVATION_PER_POINT if s else 0) + 40,
            "color": rgb(TIER[tier]["fg"], 230),
            "approx": i18n.t("approx_pos", lang) if approx else "",
        })
    place_labels(points)
    return points, unplaced


def place_labels(points: list[dict]) -> None:
    """Put each label on the side away from its nearest neighbour, so close ghats stay legible."""
    for p in points:
        others = [o for o in points if o is not p]
        p.update(anchor="middle", baseline="bottom", offset=[0, -14])
        if not others:
            continue
        n = min(others, key=lambda o: (o["lat"] - p["lat"]) ** 2 + (o["lon"] - p["lon"]) ** 2)
        dx, dy = n["lon"] - p["lon"], n["lat"] - p["lat"]
        if max(abs(dx), abs(dy)) > CROWDED:
            continue
        if abs(dx) >= abs(dy):
            p.update(anchor="end" if dx > 0 else "start", baseline="center",
                     offset=[-14 if dx > 0 else 14, 0])
        else:
            p.update(baseline="top" if dy > 0 else "bottom", offset=[0, 14 if dy > 0 else -14])


def centre(points: list[dict]) -> tuple[float, float]:
    lats, lons = [p["lat"] for p in points], [p["lon"] for p in points]
    return (min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2


def view_for(points: list[dict], focus: dict | None, step: int) -> pdk.ViewState:
    """Overview of all points, or a tilted close-up of one; bearing turns with each step."""
    if focus is None:
        lat, lon = centre(points)
        return pdk.ViewState(latitude=lat, longitude=lon, transition_duration=FLY_MS, **OVERVIEW)
    return pdk.ViewState(latitude=focus["lat"], longitude=focus["lon"],
                         bearing=(step * 40) % 360 - 20, transition_duration=FLY_MS, **FOCUS)


def build_deck(points: list[dict], focus: dict | None, step: int, tooltip: str) -> pdk.Deck:
    """Columns + click dots for ranked ghats, rings for no-baseline ghats, labels, halo."""
    ranked = [p for p in points if p["kind"] == "ranked"]
    nobase = [p for p in points if p["kind"] == "nobase"]
    link = rgb(COLOR["link"])
    layers = [
        pdk.Layer("ScatterplotLayer", [focus] if focus else [], id="halo",
                  get_position=["lon", "lat"], get_radius=380, filled=False, stroked=True,
                  get_line_color=link, line_width_min_pixels=3),
        pdk.Layer("ColumnLayer", ranked, id="columns", get_position=["lon", "lat"],
                  get_elevation="elevation", get_fill_color="color", radius=150,
                  extruded=True),
        # Click targets: dots that never shrink below a tappable size, even zoomed out.
        pdk.Layer("ScatterplotLayer", ranked, id="ghats", get_position=["lon", "lat"],
                  get_radius=160, radius_min_pixels=11, get_fill_color="color",
                  stroked=True, get_line_color=[255, 255, 255, 255], line_width_min_pixels=2,
                  pickable=True, auto_highlight=True),
        pdk.Layer("ScatterplotLayer", nobase, id="nobase", get_position=["lon", "lat"],
                  get_radius=200, radius_min_pixels=10,
                  get_fill_color=rgb(TIER["NoData"]["bg"], 220), stroked=True,
                  get_line_color=rgb(TIER["NoData"]["fg"]), line_width_min_pixels=3,
                  pickable=True),
        pdk.Layer("TextLayer", points, id="labels", get_position=["lon", "lat", "label_z"],
                  get_text="label", get_size=14, get_color=rgb(COLOR["text"]),
                  get_text_anchor="anchor",
                  get_alignment_baseline="baseline", get_pixel_offset="offset",
                  background=True, get_background_color=[255, 255, 255, 230],
                  background_padding=[6, 3]),
    ]
    return pdk.Deck(layers=layers, initial_view_state=view_for(points, focus, step),
                    map_provider="carto", map_style=pdk.map_styles.CARTO_LIGHT,
                    tooltip={"html": tooltip,
                             "style": {"backgroundColor": COLOR["bg"], "color": COLOR["text"],
                                       "fontSize": "13px", "border": f"1px solid {COLOR['line']}"}})


def tooltip_html(lang: str) -> str:
    return (f"<b>{{label}}</b><br/>{{tier_text}} · {i18n.t('risk', lang)} {{risk_text}}"
            f"<br/><i>{{approx}}</i>")


def selected_ghat(event: Any) -> str | None:
    """Ghat name from a pydeck selection event (single object), if any."""
    objects = getattr(getattr(event, "selection", None), "objects", None) or {}
    for layer in ("ghats", "nobase"):
        if objects.get(layer):
            return objects[layer][0].get("ghat")
    return None


def tour_stops(points: list[dict]) -> list[dict | None]:
    """None = overview, then every point in rank order (no-baseline ghats last)."""
    return [None, *points]


def tour_step(started: float, now: float) -> int:
    """Stop number from elapsed time, so extra reruns (e.g. map events) never skip a stop."""
    return max(0, int((now - started) // TOUR_SECONDS))


def _focus(points: list[dict], tour_on: bool) -> tuple[dict | None, int]:
    """Which point the camera shows this run, and the step used for the bearing."""
    started = st.session_state.setdefault(STEP_KEY, time.time())
    step = tour_step(started, time.time())
    if tour_on:
        stops = tour_stops(points)
        return stops[step % len(stops)], step
    chosen = st.session_state.get(SEEN_KEY)
    return next((p for p in points if p["ghat"] == chosen), None), step


def _spotlight(focus: dict | None, data: dict[str, Any], lang: str, tour_on: bool) -> None:
    scores = data["scores"]
    if focus is None:
        html_ = ui.spot_overview(scores, lang)
        st.markdown(html_, unsafe_allow_html=True)
        return
    s = next((x for x in scores.ranked if x.ghat == focus["ghat"]), None)
    heading = i18n.t("spot_now" if tour_on else "spot_picked", lang)
    st.markdown(ui.spot_card(heading, focus, s, data["limits"], len(scores.ranked), lang),
                unsafe_allow_html=True)
    if s is not None and st.button(i18n.t("open_details", lang), key="spot_open",
                                   icon=":material/arrow_downward:", type="primary"):
        st.session_state[PICK_KEY] = s.ghat
        st.session_state[SEEN_KEY] = s.ghat
        st.session_state[PAUSE_KEY] = True
        st.rerun(scope="app")


def _map_body(data: dict[str, Any], lang: str, points: list[dict]) -> None:
    tour_on = st.session_state.get(TOUR_KEY, True)
    focus, step = _focus(points, tour_on)
    left, right = st.columns([2.2, 1], gap="medium")
    with left:
        event = st.pydeck_chart(build_deck(points, focus, step, tooltip_html(lang)),
                                height=440, on_select="rerun", selection_mode="single-object",
                                key=f"{MAP_KEY}_{st.session_state.get(ROUND_KEY, 0)}")
    picked = selected_ghat(event)
    if picked:
        # Keep tier colours readable: a fresh chart key drops Streamlit's selection greying.
        st.session_state[ROUND_KEY] = st.session_state.get(ROUND_KEY, 0) + 1
        st.session_state[SEEN_KEY] = picked
        st.session_state[PAUSE_KEY] = True
        if any(s.ghat == picked for s in data["scores"].ranked):
            st.session_state[PICK_KEY] = picked
        st.rerun(scope="app")
    with right:
        _spotlight(focus, data, lang, tour_on)


def _restart_tour() -> None:
    """Turning the tour on starts again from the overview."""
    st.session_state[STEP_KEY] = time.time()


def _show_all() -> None:
    """Button callback (runs before widgets render, so it may set the toggle's state)."""
    st.session_state.pop(SEEN_KEY, None)
    st.session_state[TOUR_KEY] = False


def follow_detail(ghat: str) -> None:
    """Point the camera at the ghat chosen in the detail selector (tour off)."""
    st.session_state[SEEN_KEY] = ghat
    st.session_state[TOUR_KEY] = False


def map_section(data: dict[str, Any], lang: str) -> None:
    """Map card with tour toggle, legend caption and the spotlight card."""
    points, unplaced = map_points(data["scores"], load_locations(), lang)
    if not points:
        return
    head, toggle, reset = st.columns([3, 1.4, 1], vertical_alignment="center")
    head.markdown(ui.card_title(i18n.t("map_title", lang)), unsafe_allow_html=True)
    st.session_state.setdefault(TOUR_KEY, True)
    if st.session_state.pop(PAUSE_KEY, False):
        st.session_state[TOUR_KEY] = False
    toggle.toggle(i18n.t("map_tour", lang), key=TOUR_KEY, help=i18n.t("map_tour_help", lang),
                  on_change=_restart_tour)
    reset.button(i18n.t("map_all", lang), key="map_reset", on_click=_show_all)
    run_every = TOUR_SECONDS if st.session_state.get(TOUR_KEY, True) else None
    st.fragment(_map_body, run_every=run_every)(data, lang, points)
    approx = sum(1 for p in points if p["approx"])
    st.caption(i18n.t("map_caption", lang) + " "
               + i18n.t("map_approx", lang, n=approx, total=len(points)))
    if unplaced:
        st.caption(i18n.t("map_unplaced", lang, names=", ".join(unplaced)))
