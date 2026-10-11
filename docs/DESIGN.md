# Neel Tarang design system (11 Oct 2026)

## Product and users

Neel Tarang is a civic data tool for a Bhopal Municipal Corporation officer planning
Durga visarjan. The officer is time-pressed, works on a phone or an office PC, reads
Hindi first, and must be able to defend every number. So the interface should read
like a trustworthy public-sector instrument, not a marketing site or a generic AI
dashboard.

## Research (sources opened on 11 Oct 2026)

| Source | What it informed |
|---|---|
| GOV.UK Design System, Tag component (design-system.service.gov.uk/components/tag/) | Status tags in sentence case with a light background and dark text; as few statuses as possible; colour never the only signal. Applied to the tier tags. |
| Nielsen Norman Group, "Dashboards: Making Charts and Graphs Easier to Understand" (nngroup.com/articles/dashboards-preattentive/) | Length and position are the most accurate encodings, so keep the bar charts; strip decoration; group with shape and proximity and use colour only as reinforcement. |
| W3C, Understanding WCAG 2.2 SC 1.4.3 Contrast (Minimum) | 4.5:1 for status-label text; set both foreground and background; tier shapes are non-text (3:1). Tier pairs are tested in `tests/test_ui.py`. |
| U.S. Web Design System, Design principles (designsystem.digital.gov/design-principles/) | Earn trust (show sources and pages), build accessibility into every decision, keep pages consistent: every section uses the same header pattern. |

The ThreeUI "Kibori" template the user supplied was also inspected. Its content (a
woodshop), code, fonts and images were not used, because no licence is stated, the
repo is public MIT, and event rule 8 forbids pasted-in code. Only its general
principles carried over: one accent colour, small uppercase labels, tight display
type, thin rules instead of boxes, and short motion.

## Decisions

- **Colour: five brand tokens.** Ink `#1B1F24` (text), slate `#5B6470` (secondary),
  paper `#FFFFFF`, mist `#F5F6F8` (table headers, grouped areas), river blue `#185FA5`
  (the one action and link colour). Semantic tier colours stay light-background /
  dark-text pairs (High, Medium, Low, No baseline). No gradients, glass, glow or
  decorative backgrounds.
- **Type.** The system sans stack, with Noto Sans Devanagari / Nirmala UI for Hindi.
  Scale 12 / 14 / 16 / 20 / 24 / 32 px, weights 400 and 500 only, tabular numerals for
  data. Every section uses the same header: an uppercase context eyebrow, the page
  title and a one-line description.
- **Spacing.** 4 / 8 / 12 / 16 / 24 / 32 / 48 px; content max width 1080 px; radius 6 px
  for controls, 4 px for tags.
- **Structure.** Rows and thin rules instead of a card around everything. The stat
  strip is numbers separated by rules. Gaps are a left-ruled list. The planner is a
  numbered list.
- **Icons.** Material Symbols, bundled with Streamlit and so available offline, in the
  top navigation only. No emoji anywhere (enforced by
  `tests/test_ui.py::test_no_emoji_or_pictographs_in_ui`). Tier status is text + a
  CSS-drawn shape (square, diamond, circle, ring) + colour.
- **Motion.** 150 ms, cubic-bezier(0.22, 1, 0.36, 1), a 1 px lift on buttons only,
  disabled under `prefers-reduced-motion`.
- **States.** Loading is the engine spinner. An empty upload page shows instructions
  plus a sample. Upload errors are listed per row. Success shows a confirmation and a
  "what changed" table. Page images that are unavailable show a message. Low
  confidence gets a dashed "Low confidence" marker.
