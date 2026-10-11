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
# Chart colours (blue = before immersion, orange = worse during; red dashed = limit).
CHART = {"baseline": "#185FA5", "festival": "#D9822B", "limit": "#A32D2D",
         "worse": "#C0392B", "better": "#3B6D11"}
HERO = {"from": "#0B3D6B", "to": "#1A7FB5", "fg": "#FFFFFF"}
FONT = ('-apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, '
        '"Noto Sans Devanagari", "Nirmala UI", sans-serif')
SHADOW = "0 1px 3px rgba(16, 24, 40, 0.10), 0 1px 2px rgba(16, 24, 40, 0.06)"
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
.stApp {{ font-family:{FONT}; }}
[data-testid="stAppDeployButton"], [data-testid="stMainMenu"], footer {{ display:none !important; }}
.block-container {{ padding-top:{s[4] * 3}px; max-width:1100px; }}
.vgw-brand {{ display:flex; align-items:center; gap:{s[2]}px; }}
.vgw-brand .vgw-logo {{ width:34px; height:34px; border-radius:10px; display:flex;
  align-items:center; justify-content:center; font-size:18px;
  background:linear-gradient(135deg, {HERO['from']}, {HERO['to']}); color:{HERO['fg']}; }}
.vgw-brand .vgw-name {{ font-size:{t[3]}px; font-weight:500; color:{c['text']}; }}
.vgw-brand .vgw-sub {{ font-size:{t[0]}px; color:{c['muted']}; }}
.vgw-lead {{ font-size:28px; font-weight:500; line-height:1.25; margin:{s[2]}px 0 {s[1]}px 0;
  background:linear-gradient(90deg, {HERO['from']}, {HERO['to']}); -webkit-background-clip:text;
  background-clip:text; color:transparent; }}
.vgw-pill {{ display:inline-block; padding:{s[1]}px {s[2]}px; border-radius:999px;
  background:{c['surface']}; color:{c['muted']}; font-size:{t[1]}px;
  border:1px solid {c['border']}; margin:{s[1]}px 0 {s[3]}px 0; }}
.vgw-kpis {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(160px, 1fr));
  gap:{s[2]}px; margin:{s[2]}px 0 {s[4]}px 0; }}
.vgw-kpi {{ border:1px solid {c['border']}; border-radius:12px; padding:{s[3]}px;
  background:{c['bg']}; }}
.vgw-kpi .n {{ font-size:28px; font-weight:500; color:{c['text']}; line-height:1.1; }}
.vgw-kpi .l {{ font-size:{t[1]}px; color:{c['muted']}; margin-top:{s[0]}px; }}
.vgw-section {{ font-size:{t[3]}px; font-weight:500; color:{c['text']};
  margin:{s[4]}px 0 {s[1]}px 0; }}
.vgw-hero {{ background:linear-gradient(120deg, {HERO['from']}, {HERO['to']});
  color:{HERO['fg']}; padding:{s[4]}px; border-radius:{RADIUS_CARD * 2}px;
  margin-bottom:{s[3]}px; box-shadow:{SHADOW}; }}
.vgw-hero h1 {{ color:{HERO['fg']}; font-size:32px; font-weight:500; margin:0; padding:0; }}
.vgw-hero p {{ color:{HERO['fg']}; font-size:{t[2]}px; margin:{s[1]}px 0 0 0; opacity:0.95; }}
.vgw-hero .vgw-chipline {{ display:inline-block; margin-top:{s[2]}px; padding:{s[1]}px {s[2]}px;
  border-radius:999px; background:rgba(255,255,255,0.16); font-size:{t[1]}px; }}
.vgw-banner {{ background:{c['surface']}; color:{c['text']}; padding:{s[2]}px {s[3]}px;
  border-radius:{RADIUS_CARD}px; font-size:{t[2]}px; font-weight:500; margin-bottom:{s[3]}px; }}
.vgw-row {{ border:1px solid {c['border']}; border-radius:{RADIUS_CARD * 1.5}px;
  padding:{s[3]}px; margin:{s[3]}px 0 {s[1]}px 0; background:{c['bg']}; display:flex;
  gap:{s[3]}px; box-shadow:{SHADOW}; }}
.vgw-row.lowconf {{ border:2px dashed {c['muted']}; }}
.vgw-rank {{ font-size:{t[3]}px; font-weight:500; color:{HERO['fg']}; background:{HERO['from']};
  min-width:36px; height:36px; border-radius:50%; display:flex; align-items:center;
  justify-content:center; flex-shrink:0; }}
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
