"""Design tokens (core.txt Appendix B). The only place colours and sizes are defined."""

COLOR = {
    "bg": "#FFFFFF",
    "surface": "#F5F6F8",
    "text": "#1B1F24",
    "muted": "#5B6470",
    "link": "#185FA5",
    "border": "#D5D9DF",
}

# Each state has text colour, background, an icon and a text label:
# colour is never the only signal.
TIER = {
    "High": {"fg": "#A32D2D", "bg": "#FCEBEB", "icon": "▲", "label": "High"},
    "Medium": {"fg": "#854F0B", "bg": "#FAEEDA", "icon": "◆", "label": "Medium"},
    "Low": {"fg": "#3B6D11", "bg": "#EAF3DE", "icon": "▼", "label": "Low"},
    "NoData": {"fg": "#5F5E5A", "bg": "#F1EFE8", "icon": "○", "label": "No baseline"},
}
MISSING = {"fg": "#5F5E5A", "bg": "#F1EFE8", "icon": "⊘"}
CONFIDENCE_ICON = {"High": "●●●", "Medium": "●●○", "Low": "●○○"}

TYPE_SCALE = [12, 14, 16, 20, 24]  # px; weights 400 and 500 only
SPACE = [4, 8, 12, 16, 24]  # px
RADIUS_CARD = 8
RADIUS_BADGE = 4
TAP_TARGET = 40  # px minimum


def css() -> str:
    """Page CSS built from the tokens."""
    c, s, t = COLOR, SPACE, TYPE_SCALE
    missing = MISSING
    return f"""
<style>
.vgw-banner {{ background:{c['surface']}; color:{c['text']}; padding:{s[2]}px {s[3]}px;
  border-radius:{RADIUS_CARD}px; font-size:{t[2]}px; font-weight:500; margin-bottom:{s[3]}px; }}
.vgw-row {{ border:1px solid {c['border']}; border-radius:{RADIUS_CARD}px;
  padding:{s[2]}px {s[3]}px; margin:{s[1]}px 0; background:{c['bg']}; display:flex;
  gap:{s[3]}px; }}
.vgw-row.lowconf {{ border:2px dashed {c['muted']}; }}
.vgw-rank {{ font-size:{t[4]}px; font-weight:500; color:{c['muted']}; min-width:28px; }}
.vgw-title {{ font-size:{t[3]}px; font-weight:500; color:{c['text']}; }}
.vgw-wb {{ font-size:{t[1]}px; color:{c['muted']}; font-weight:400; margin-left:{s[1]}px; }}
.vgw-chips {{ display:flex; flex-wrap:wrap; gap:{s[1]}px; margin:{s[1]}px 0; }}
.vgw-badge {{ display:inline-block; border-radius:{RADIUS_BADGE}px; padding:2px {s[1]}px;
  font-size:{t[1]}px; font-weight:500; border:1px solid transparent; }}
.vgw-chip {{ display:inline-block; border-radius:{RADIUS_BADGE}px; padding:2px {s[1]}px;
  font-size:{t[1]}px; background:{c['surface']}; color:{c['text']};
  border:1px solid {c['border']}; }}
.vgw-chip.warn {{ border-color:{c['muted']}; border-style:dashed; }}
.vgw-reason {{ font-size:{t[1]}px; color:{c['text']}; }}
.vgw-muted {{ color:{c['muted']}; font-size:{t[1]}px; }}
.vgw-missing {{ color:{missing['fg']}; background:{missing['bg']};
  border:1px dashed {missing['fg']}; border-radius:{RADIUS_BADGE}px; padding:0 {s[1]}px; }}
.vgw-card {{ border:1px solid {c['border']}; border-radius:{RADIUS_CARD}px;
  padding:{s[2]}px {s[3]}px; margin:{s[1]}px 0; background:{c['surface']}; }}
.vgw-card h4 {{ margin:0 0 {s[1]}px 0; font-size:{t[2]}px; font-weight:500; }}
table.vgw-ev {{ border-collapse:collapse; width:100%; font-size:{t[1]}px; }}
table.vgw-ev th, table.vgw-ev td {{ border-bottom:1px solid {c['border']};
  padding:{s[1]}px; text-align:left; vertical-align:top; }}
table.vgw-ev th {{ font-weight:500; color:{c['muted']}; }}
a.vgw-link {{ color:{c['link']}; }}
.vgw-page img {{ width:100%; border:1px solid {c['border']}; border-radius:{RADIUS_CARD}px; }}
.stButton button {{ min-height:{TAP_TARGET}px; }}
</style>
"""
