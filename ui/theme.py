"""Design tokens (core.txt Appendix B, refined 11 Oct 2026 - see docs/DESIGN.md).

The only place colours, sizes and type are defined. Direction: a calm,
document-like civic tool. Five brand tokens, semantic tier colours as light
backgrounds with dark text, no gradients, no glass, no emoji.
"""

# Five brand tokens.
COLOR = {
    "text": "#1B1F24",     # ink
    "muted": "#5B6470",    # slate: secondary text, axis labels
    "bg": "#FFFFFF",       # paper
    "surface": "#F5F6F8",  # mist: grouped areas, table headers
    "link": "#185FA5",     # river blue: the one action / brand colour
    "border": "#D5D9DF",   # derived from slate: rules and outlines
    "line": "#E6EAF0",     # lighter rule inside cards
    "focus": "#185FA5",
}

# Semantic status colours (GOV.UK tag guidance: light background, dark text).
# Every tier also has a SHAPE (drawn in CSS) and a TEXT label.
TIER = {
    "High": {"fg": "#A32D2D", "bg": "#FCEBEB", "shape": "square", "label": "High"},
    "Medium": {"fg": "#854F0B", "bg": "#FAEEDA", "shape": "diamond", "label": "Medium"},
    "Low": {"fg": "#3B6D11", "bg": "#EAF3DE", "shape": "circle", "label": "Low"},
    "NoData": {"fg": "#5F5E5A", "bg": "#F1EFE8", "shape": "ring", "label": "No baseline"},
}
MISSING = {"fg": "#5F5E5A", "bg": "#F1EFE8"}

# Charts: blue = before immersion (baseline), amber = worse during immersion.
CHART = {"baseline": "#185FA5", "festival": "#C77700", "limit": "#A32D2D",
         "worse": "#A32D2D", "better": "#3B6D11"}

FONT = ('-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, '
        '"Noto Sans Devanagari", "Nirmala UI", "Mangal", sans-serif')
TYPE_SCALE = [12, 14, 16, 20, 24, 32]  # px: caption, small, body, h3, h2, page title
WEIGHT = {"regular": 400, "medium": 500}
SPACE = [4, 8, 12, 16, 24, 32, 48]  # px
RADIUS_CARD = 6
RADIUS_TAG = 4
TAP_TARGET = 40  # px minimum
MOTION = "150ms cubic-bezier(0.22, 1, 0.36, 1)"
MAX_WIDTH = 1240
SHADOW = "0 1px 2px rgba(16, 24, 40, 0.04), 0 1px 3px rgba(16, 24, 40, 0.06)"


def _shape_css(shape: str, colour: str) -> str:
    """CSS for the small tier shape drawn before the tag text (non-text contrast >= 3:1)."""
    if shape == "square":
        return f"background:{colour};"
    if shape == "diamond":
        return f"background:{colour}; transform:rotate(45deg) scale(0.85);"
    if shape == "circle":
        return f"background:{colour}; border-radius:50%;"
    return f"border:2px solid {colour}; border-radius:50%; width:6px; height:6px;"


def css() -> str:
    """Page CSS built from the tokens."""
    c, s, t, w, m = COLOR, SPACE, TYPE_SCALE, WEIGHT, MISSING
    shapes = "".join(f".nt-tag.{k.lower()}::before {{ {_shape_css(v['shape'], v['fg'])} }}\n"
                     for k, v in TIER.items())
    status_shapes = "".join(
        f".nt-status.{k.lower()}::before {{ {_shape_css(v['shape'], v['fg'])} }}"
        f" .nt-status.{k.lower()} {{ color:{v['fg']}; }} " for k, v in TIER.items())
    return f"""
<style>
/* base: light canvas, white cards (dashboard layout) */
.stApp {{ font-family:{FONT}; color:{c['text']}; background:{c['surface']}; }}
[data-testid="stHeader"] {{ background:transparent; }}
.block-container {{ max-width:{MAX_WIDTH}px; padding-top:{s[6]}px; padding-bottom:{s[6]}px; }}
[data-testid="stAppDeployButton"], [data-testid="stMainMenu"], footer {{ display:none !important; }}
a, .nt-link {{ color:{c['link']}; text-underline-offset:2px; }}
:focus-visible {{ outline:3px solid {c['focus']}; outline-offset:2px; }}
.stButton button, .stDownloadButton button {{ min-height:{TAP_TARGET}px;
  border-radius:{RADIUS_CARD}px; transition:transform {MOTION}; }}
.stButton button:hover, .stDownloadButton button:hover {{ transform:translateY(-1px); }}
@media (prefers-reduced-motion: reduce) {{
  * {{ transition:none !important; animation:none !important; }}
  .stButton button:hover, .stDownloadButton button:hover {{ transform:none; }} }}

/* sidebar */
[data-testid="stSidebar"] {{ background:{c['bg']}; border-right:1px solid {c['line']}; }}
[data-testid="stSidebarNavLink"] {{ border-radius:8px; min-height:{TAP_TARGET}px;
  padding:{s[1]}px {s[2]}px; margin:2px 0; }}
[data-testid="stSidebarNavLink"] span {{ font-size:15px; color:{c['text']}; }}
[data-testid="stSidebarNavLink"][aria-current="page"] {{ background:#E8F0F8; }}
[data-testid="stSidebarNavLink"][aria-current="page"] span {{ color:{c['link']};
  font-weight:{w['medium']}; }}

/* cards: keyed containers st.container(border=True, key="card-...") */
[class*="st-key-card"] {{ background:{c['bg']}; border:1px solid {c['line']} !important;
  border-radius:10px; box-shadow:{SHADOW}; padding:{s[4]}px !important; }}
.nt-card-title {{ font-size:17px; font-weight:{w['medium']}; margin:0 0 {s[2]}px 0; }}

/* top bar and primary action */
.nt-crumb {{ font-size:{t[1]}px; color:{c['muted']}; padding-top:{s[1]}px; }}
.nt-crumb b {{ color:{c['text']}; font-weight:{w['regular']}; }}
.st-key-topbar {{ border-bottom:1px solid {c['line']}; padding-bottom:{s[1]}px;
  margin-bottom:{s[3]}px; }}
.st-key-actions [data-testid="stPageLink"] a {{ background:{c['link']}; border-radius:8px;
  min-height:{TAP_TARGET}px; padding:{s[1]}px {s[3]}px; justify-content:center;
  transition:transform {MOTION}; }}
.st-key-actions [data-testid="stPageLink"] a span,
.st-key-actions [data-testid="stPageLink"] a p {{ color:{c['bg']} !important;
  font-weight:{w['medium']}; }}
.st-key-actions [data-testid="stPageLink"] a:hover {{ transform:translateY(-1px); }}

/* stat cards */
.nt-kpis {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr));
  gap:{s[3]}px; margin:0 0 {s[3]}px 0; }}
.nt-kpi {{ background:{c['bg']}; border:1px solid {c['line']}; border-radius:10px;
  box-shadow:{SHADOW}; padding:{s[4]}px; }}
.nt-kpi .l {{ font-size:{t[1]}px; color:{c['muted']}; }}
.nt-kpi .n {{ font-size:28px; font-weight:{w['medium']}; font-variant-numeric:tabular-nums;
  margin:{s[1]}px 0 {s[0]}px 0; line-height:1.15; }}
.nt-kpi .s {{ font-size:13px; color:{c['muted']}; }}

/* summary list (right-hand card) */
.nt-sum {{ padding:{s[2]}px 0; border-top:1px solid {c['line']}; display:flex;
  justify-content:space-between; gap:{s[2]}px; align-items:baseline; }}
.nt-sum.first {{ border-top:none; }}
.nt-sum .name {{ font-size:{t[1]}px; }}
.nt-sum .val {{ font-size:{t[3]}px; font-weight:{w['medium']}; font-variant-numeric:tabular-nums; }}

/* ranked table */
table.nt-table {{ width:100%; border-collapse:collapse; font-size:{t[1]}px; }}
table.nt-table th {{ text-align:left; font-weight:{w['medium']}; color:{c['muted']};
  background:{c['surface']}; padding:{s[2]}px; border-bottom:1px solid {c['line']}; }}
table.nt-table td {{ padding:{s[2]}px; border-bottom:1px solid {c['line']}; vertical-align:top; }}
table.nt-table td.num {{ text-align:right; font-variant-numeric:tabular-nums;
  font-weight:{w['medium']}; }}
table.nt-table .sub {{ display:block; color:{c['muted']}; font-size:{t[0]}px; margin-top:2px;
  line-height:1.5; }}
.nt-status {{ display:inline-flex; align-items:center; gap:6px; white-space:nowrap; }}
.nt-status::before {{ content:""; display:inline-block; width:8px; height:8px; flex:none; }}
{status_shapes}
table.nt-table, table.nt-table th, table.nt-table td, table.nt-ev, table.nt-ev th,
table.nt-ev td {{ border-left:none !important; border-right:none !important;
  border-top:none !important; }}
@media (max-width: 760px) {{ table.nt-table .hide-sm {{ display:none; }} }}

/* header */
.nt-brand {{ font-size:{t[2]}px; font-weight:{w['medium']}; letter-spacing:-0.01em; }}
.nt-brand span {{ color:{c['muted']}; font-weight:{w['regular']}; }}
.nt-eyebrow {{ font-size:{t[0]}px; letter-spacing:0.08em; text-transform:uppercase;
  color:{c['muted']}; margin:0 0 {s[1]}px 0; }}
.nt-title {{ font-size:clamp(24px, 4vw, {t[5]}px); font-weight:{w['medium']}; line-height:1.2;
  letter-spacing:-0.02em; margin:0 0 {s[1]}px 0; }}
.nt-lede {{ font-size:{t[2]}px; line-height:1.5; color:{c['muted']}; max-width:68ch;
  margin:0 0 {s[4]}px 0; }}
.nt-h2 {{ font-size:{t[3]}px; font-weight:{w['medium']}; margin:{s[5]}px 0 {s[2]}px 0; }}
.nt-note {{ font-size:{t[1]}px; color:{c['muted']}; line-height:1.5; }}

/* stat strip: numbers separated by rules, no boxes */
.nt-stats {{ display:flex; flex-wrap:wrap; border-top:1px solid {c['border']};
  border-bottom:1px solid {c['border']}; margin:{s[2]}px 0 {s[4]}px 0; }}
.nt-stats {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(150px, 1fr)); }}
.nt-stat {{ padding:{s[3]}px {s[3]}px {s[3]}px 0; box-shadow:inset -1px 0 0 {c['border']}; }}
.nt-stat:last-child {{ box-shadow:none; }}
.nt-stat + .nt-stat {{ padding-left:{s[3]}px; }}
.nt-stat .n {{ font-size:{t[4]}px; font-weight:{w['medium']}; font-variant-numeric:tabular-nums;
  line-height:1.1; }}
.nt-stat .l {{ font-size:{t[1]}px; color:{c['muted']}; margin-top:{s[0]}px; }}

/* tier tag: text + shape + colour */
.nt-tag {{ display:inline-flex; align-items:center; gap:6px; padding:2px {s[1]}px;
  border-radius:{RADIUS_TAG}px; font-size:{t[1]}px; line-height:1.5; white-space:nowrap; }}
.nt-tag::before {{ content:""; display:inline-block; width:8px; height:8px; flex:none; }}
{shapes}
/* ghat row */
.nt-row {{ display:grid; grid-template-columns:40px 1fr auto; gap:{s[1]}px {s[3]}px;
  padding:{s[4]}px 0 {s[2]}px 0; border-top:1px solid {c['border']}; }}
.nt-rank {{ font-size:{t[3]}px; font-weight:{w['medium']}; color:{c['muted']};
  font-variant-numeric:tabular-nums; padding-top:2px; }}
.nt-name {{ font-size:{t[3]}px; font-weight:{w['medium']}; line-height:1.3; }}
.nt-wb {{ font-size:{t[1]}px; color:{c['muted']}; font-weight:{w['regular']}; }}
.nt-meta {{ font-size:{t[1]}px; margin-top:{s[1]}px; line-height:1.8; }}
.nt-meta .sep {{ color:{c['border']}; margin:0 {s[1]}px; }}
.nt-meta .k {{ color:{c['muted']}; }}
.nt-reason {{ font-size:{t[2]}px; line-height:1.5; margin-top:{s[1]}px; max-width:72ch; }}
.nt-flags {{ font-size:{t[1]}px; color:{c['muted']}; margin-top:{s[1]}px; line-height:1.6; }}
.nt-score {{ text-align:right; min-width:72px; }}
.nt-score .n {{ font-size:{t[4]}px; font-weight:{w['medium']}; font-variant-numeric:tabular-nums;
  line-height:1.1; }}
.nt-score .l {{ font-size:{t[0]}px; color:{c['muted']}; }}
.nt-lowconf {{ display:inline-block; font-size:{t[0]}px; color:{c['muted']};
  border:1px dashed {c['muted']}; border-radius:{RADIUS_TAG}px; padding:0 {s[1]}px;
  margin-left:{s[1]}px; vertical-align:middle; }}
@media (max-width: 640px) {{
  .nt-row {{ grid-template-columns:28px 1fr; }}
  .nt-score {{ grid-column:2; text-align:left; }} }}

/* lists, tables */
.nt-item {{ border-left:3px solid {c['border']}; padding:{s[1]}px 0 {s[1]}px {s[3]}px;
  margin:{s[3]}px 0; }}
.nt-item h4 {{ margin:0 0 {s[0]}px 0; font-size:{t[2]}px; font-weight:{w['medium']}; }}
.nt-item ul {{ margin:{s[1]}px 0 0 0; padding-left:{s[4]}px; }}
.nt-item li, .nt-item p {{ font-size:{t[1]}px; line-height:1.5; margin:0; }}
.nt-plan {{ display:grid; grid-template-columns:32px 1fr; gap:{s[3]}px; padding:{s[3]}px 0;
  border-top:1px solid {c['border']}; }}
.nt-missing {{ color:{m['fg']}; background:{m['bg']}; border:1px dashed {m['fg']};
  border-radius:{RADIUS_TAG}px; padding:0 {s[1]}px; }}
table.nt-ev {{ border-collapse:collapse; width:100%; font-size:{t[1]}px;
  font-variant-numeric:tabular-nums; }}
table.nt-ev th, table.nt-ev td {{ border-bottom:1px solid {c['border']}; padding:{s[1]}px;
  text-align:left; vertical-align:top; }}
table.nt-ev th {{ font-weight:{w['medium']}; color:{c['muted']}; background:{c['surface']}; }}
/* map: the auto-tour reruns every few seconds; do not fade the card each time */
.st-key-card-map [data-stale="true"] {{ opacity:1 !important; transition:none !important; }}
/* map spotlight (beside the map) */
.nt-spot {{ border-left:3px solid {c['link']}; padding:{s[1]}px 0 {s[1]}px {s[3]}px;
  min-height:200px; }}
.nt-spot-eyebrow {{ font-size:{t[0]}px; letter-spacing:0.08em; text-transform:uppercase;
  color:{c['muted']}; margin-bottom:{s[1]}px; }}
.nt-spot-name {{ font-size:{t[3]}px; font-weight:{w['medium']}; line-height:1.3; }}
.nt-spot-approx {{ font-size:{t[0]}px; color:{c['muted']}; font-weight:{w['regular']}; }}
.nt-spot-meta {{ font-size:{t[1]}px; margin-top:{s[1]}px; line-height:1.8; }}
.nt-spot-meta .sep, .nt-v-head .sep {{ color:{c['border']}; margin:0 {s[1]}px; }}
.nt-spot-score {{ margin-top:{s[2]}px; }}
.nt-spot-score .n {{ font-size:28px; font-weight:{w['medium']};
  font-variant-numeric:tabular-nums; }}
.nt-spot-score .l {{ font-size:{t[0]}px; color:{c['muted']}; }}
.nt-spot-text {{ font-size:{t[1]}px; line-height:1.55; margin:{s[2]}px 0; }}
ul.nt-legend {{ list-style:none; padding:0; margin:{s[2]}px 0 0 0; display:grid;
  grid-template-columns:1fr 1fr; gap:{s[1]}px; font-size:{t[1]}px; }}

/* plain-language verdict in the ghat detail */
.nt-v-head {{ display:flex; justify-content:space-between; gap:{s[3]}px; align-items:flex-start; }}
.nt-v-name {{ font-size:{t[4]}px; font-weight:{w['medium']}; line-height:1.25; }}
.nt-qs {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr));
  gap:{s[3]}px; margin:{s[4]}px 0 {s[3]}px 0; }}
.nt-q {{ background:{c['surface']}; border-radius:8px; padding:{s[3]}px {s[4]}px; }}
.nt-q-title {{ font-size:{t[1]}px; color:{c['muted']}; margin-bottom:{s[1]}px; }}
.nt-q-fact {{ font-size:{t[1]}px; line-height:1.5; margin:{s[2]}px 0 0 0; }}
.nt-q-note {{ font-size:{t[0]}px; line-height:1.5; color:{c['muted']}; margin:{s[1]}px 0 0 0; }}
.nt-answer {{ display:inline-block; font-size:{t[3]}px; font-weight:{w['medium']};
  line-height:1.3; }}
.nt-answer.bad {{ color:{TIER['High']['fg']}; }}
.nt-answer.some {{ color:{TIER['Medium']['fg']}; }}
.nt-answer.good {{ color:{TIER['Low']['fg']}; }}
.nt-answer.unknown {{ color:{m['fg']}; border-bottom:1px dashed {m['fg']}; }}
.nt-suggest {{ border-left:3px solid {c['link']}; padding:{s[1]}px 0 {s[1]}px {s[3]}px; }}
.nt-suggest p {{ font-size:{t[2]}px; line-height:1.5; margin:0; max-width:80ch; }}
.nt-callout {{ font-size:{t[1]}px; color:{TIER['High']['fg']}; background:{TIER['High']['bg']};
  border-radius:{RADIUS_TAG}px; padding:{s[2]}px {s[3]}px; margin:{s[3]}px 0 0 0; }}
.nt-page img {{ width:100%; border:1px solid {c['border']}; border-radius:{RADIUS_CARD}px; }}
</style>
"""
