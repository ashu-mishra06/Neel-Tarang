"""Vega-Lite chart specs (plain dicts) built from engine output.

Plain specs are rendered with st.vega_lite_chart, which does not need Altair.
Every number plotted comes from GhatScore fields; nothing is recomputed here
except splitting the risk score into its two published parts.
"""

from __future__ import annotations

from typing import Any

from ui.theme import CHART, COLOR


def risk_parts(s: Any, weights: dict[str, float]) -> tuple[float, float]:
    """Split a ghat's risk score into its baseline and festival parts (they sum to it)."""
    b = weights["baseline"] * (s.baseline or 0)
    f = weights["festival"] * (s.festival or 0)
    total = b + f
    if total == 0:
        return 0.0, 0.0
    return s.risk_score * b / total, s.risk_score * f / total


def risk_breakdown(scores: Any, rules: dict[str, Any], labels: dict[str, str],
                   tier_names: dict[str, str]) -> dict[str, Any]:
    """Stacked horizontal bars: baseline part + festival part = risk score, tier lines dashed."""
    weights = rules["scoring"]["risk_weights"]
    rows, order = [], []
    for s in scores.ranked:
        name = f"{s.rank}. {s.ghat}"
        order.append(name)
        base, fest = risk_parts(s, weights)
        for order_, (part, value) in enumerate(((labels["baseline"], base),
                                                (labels["festival"], fest))):
            rows.append({"ghat": name, "part": part, "o": order_, "value": round(value, 1),
                         "risk": round(s.risk_score, 1), "tier": tier_names[s.tier]})
    lines = [{"x": v, "line": f"{tier_names[k.capitalize()]} ≥ {v:g}"}
             for k, v in rules["scoring"]["tiers"].items()]
    y = {"field": "ghat", "type": "nominal", "sort": order, "title": None,
         "axis": {"labelLimit": 260, "labelFontSize": 13}}
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "height": {"step": 34},
        "layer": [
            {"data": {"values": rows}, "mark": {"type": "bar", "cornerRadiusEnd": 3},
             "encoding": {
                 "y": y,
                 "x": {"field": "value", "type": "quantitative", "stack": "zero",
                       "title": labels["risk"]},
                 "color": {"field": "part", "type": "nominal", "title": None,
                           "scale": {"domain": [labels["baseline"], labels["festival"]],
                                     "range": [CHART["baseline"], CHART["festival"]]},
                           "legend": {"orient": "top", "direction": "vertical",
                                      "labelFontSize": 13, "labelLimit": 320}},
                 "order": {"field": "o", "type": "quantitative", "sort": "ascending"},
                 "tooltip": [{"field": "ghat", "title": " "},
                             {"field": "part", "title": " "},
                             {"field": "value", "title": "part"},
                             {"field": "risk", "title": labels["risk"]},
                             {"field": "tier", "title": " "}]}},
            {"data": {"values": lines}, "mark": {"type": "rule", "strokeDash": [5, 4],
                                                 "color": COLOR["muted"]},
             "encoding": {"x": {"field": "x", "type": "quantitative"},
                          "tooltip": [{"field": "line", "title": " "}]}},
        ],
        "config": {"view": {"stroke": None}, "axis": {"grid": False}},
    }


def pairs_chart(s: Any, parameter: str, limit: Any, unpaired_label: str,
                worse: str = "worse", better: str = "same or better") -> dict[str, Any] | None:
    """Before -> during per report table for one parameter, with the class B limit.

    The arrowhead points the way the value moved; colour AND legend say worse/better.
    """
    pairs = [p for p in s.matched_pairs if p["parameter"] == parameter]
    unpaired = [u for u in s.unpaired_breaches if u["parameter"] == parameter]
    if not pairs and not unpaired:
        return None
    rows = [{"table": f"{p['festival']} {p['year']}", "before": p["pre"], "during": p["during"],
             "change": worse if p["worsening"] > 0 else better,
             "dir": "up" if p["during"] >= p["pre"] else "down"} for p in pairs]
    extra = [{"table": f"{u['festival']} {u['year']} ({u['phase']})", "value": u["value"],
              "note": unpaired_label} for u in unpaired]
    limits = [v for v in (limit.low, limit.high) if v is not None]
    unit = f" ({limit.unit})" if limit.unit else ""
    x = {"type": "quantitative", "title": f"{parameter}{unit}", "scale": {"zero": False}}
    color = {"field": "change", "type": "nominal", "title": None,
             "scale": {"domain": [worse, better],
                       "range": [CHART["worse"], CHART["better"]]}}
    layers: list[dict[str, Any]] = []
    if rows:
        layers += [
            {"data": {"values": rows}, "mark": {"type": "rule", "strokeWidth": 3},
             "encoding": {"y": {"field": "table", "type": "nominal", "title": None,
                                "axis": {"labelLimit": 220}},
                          "x": {**x, "field": "before"}, "x2": {"field": "during"},
                          "color": color}},
            {"data": {"values": rows}, "mark": {"type": "point", "filled": False, "size": 90},
             "encoding": {"y": {"field": "table", "type": "nominal"},
                          "x": {**x, "field": "before"}, "color": {"value": COLOR["muted"]},
                          "tooltip": [{"field": "table"}, {"field": "before"},
                                      {"field": "during"}]}},
            {"data": {"values": rows},
             "mark": {"type": "point", "filled": True, "size": 150},
             "encoding": {"y": {"field": "table", "type": "nominal"},
                          "x": {**x, "field": "during"}, "color": color,
                          "shape": {"field": "dir", "type": "nominal", "legend": None,
                                    "scale": {"domain": ["up", "down"],
                                              "range": ["triangle-right", "triangle-left"]}},
                          "tooltip": [{"field": "table"}, {"field": "before"},
                                      {"field": "during"}, {"field": "change"}]}},
        ]
    if extra:
        layers.append(
            {"data": {"values": extra}, "mark": {"type": "point", "shape": "cross",
                                                 "filled": True, "size": 160},
             "encoding": {"y": {"field": "table", "type": "nominal", "title": None},
                          "x": {**x, "field": "value"}, "color": {"value": CHART["worse"]},
                          "tooltip": [{"field": "table"}, {"field": "value"},
                                      {"field": "note"}]}})
    layers.append(
        {"data": {"values": [{"limit": v} for v in limits]},
         "mark": {"type": "rule", "color": CHART["limit"], "strokeDash": [6, 3],
                  "strokeWidth": 2},
         "encoding": {"x": {"field": "limit", "type": "quantitative"},
                      "tooltip": [{"field": "limit", "title": "CPCB class B limit"}]}})
    return {"$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "height": {"step": 30}, "layer": layers,
            "config": {"view": {"stroke": None}, "legend": {"orient": "top"}}}
