# Method note

## Reading status (Level 1)

Each reading gets one status:

| Status | When | How it is used |
|---|---|---|
| `value` | a number, with no missing/BDL flag | scored |
| `missing` | flag `not sampled`, `*`, `**`; or blank; or unreadable text | excluded from rates, lowers confidence, never counted as clean |
| `below_detection` | flag `BDL` or `ND` | not a breach, never zero, not missing |

Flags take priority over numbers, so a `0` marked `BDL` is never read as 0.
BDL/ND on a scored parameter (pH, DO, BOD) is unexpected; the loader warns
and records it for the gap register.

## Limits (CPCB class B)

| Parameter | Breach if | Exceedance (0..1) |
|---|---|---|
| pH | outside 6.5-8.5 | distance outside / 1.5 |
| Dissolved oxygen | below 5 mg/l | (5 - v) / 5 |
| BOD | above 3 mg/l | (v - 3) / 3 |

Values live in `rules.yaml` and are checked against the class B rows of
`data/cpcb_water_quality_criteria.csv` on every load; the engine stops if
they differ.

## Data provenance

The organisers' files come from the archive
`bhopal-impact-lab-2026-problem-statements-main.zip`, folder
`track-2-visarjan-ghat-watch/`. They were copied unchanged: `data/*.csv` and
`data/DATA_DICTIONARY.md` into `data/`, report PDFs into `resources/`.

## Verification

Level 1, 11 Oct 2026. The counts below were made twice, once by plain pandas
outside the engine and once through `scoring.loader`. Both agree with the
brief.

| Check | Result |
|---|---|
| Rows / ghats / years | 1,524 / 7 / 2023-2025 |
| Cells per scored parameter | 120 each (pH, DO, BOD) |
| DO valid / below 5 mg/l | 116 / 42 |
| BOD valid / above 3 mg/l | 112 / 100 |
| pH valid / outside 6.5-8.5 | 115 / 6 |
| Missing on scored parameters | BOD 8 not sampled; DO 4; pH 1 not sampled + 2 `*` + 2 `**` |
| BDL | 174, all on metals (Cr 65, Pb 52, Cu 36, Zn 21); none on scored parameters |
| Reported DO = 0 mg/l | 4 |
| Status totals | value 1,289 / missing 61 / below_detection 174 |

## Scoring (Level 2)

Implements core.txt Appendix A. All weights and cut-offs are in `rules.yaml`
under `scoring:`. Run `python -m scoring.engine` to print the ranking and
write `data/derived/ghat_scores.json` with every component visible.

- **Baseline** (pre-immersion only): 0.5 x breach rate + 0.5 x mean
  exceedance over valid pH, DO and BOD readings.
- **Festival effect**: for each festival-year-parameter with valid pre and
  during readings, 0.7 x worsening (pre to during) + 0.3 x worsening (pre to
  after); during only if after is missing. Improvement counts as 0. Each
  parameter's festival value is the mean of its triples; the ghat's festival
  effect is the **worst parameter's** value (max over pH, DO, BOD). The
  per-parameter values stay in the output.
- **Risk** = 100 x (0.5 x baseline + 0.5 x festival). If one part cannot be
  computed, risk uses the other part alone (re-weighted). A missing part is
  never treated as 0.
- **Matched pair**: one festival-year table with a valid pre AND a valid
  during reading for the same parameter. Any average used in a driver label
  or quoted in text is taken over matched pairs only, never across
  different tables.
- **Driver**: "poor before" = baseline >= 0.40. "Worsens" = the physical
  anchor (D1c), not the festival score. No matched pairs at all gives "Not
  enough data to tell". When neither triggers, a Low-tier ghat reads "Lower
  concern on available data" and a Medium or High ghat reads "Elevated on
  several measures; no single large change" (D1f). The JSON field
  `driver_detail` puts the numbers next to the label: baseline, its
  cut-off, the festival score, and whether the anchor was met and why.
- **Unpaired breaches**: a during/after reading that breaches its limit but
  cannot be compared (no valid pre in its table, or an after reading with no
  valid during) is listed with value, parameter, festival-year, phase, page
  and cause. It does not change the score (D1e).
- **Near-boundary**: risk within 1.5 points of a tier line sets
  `near_boundary: true` and gives `nearest_line` (line name, value, signed
  distance) in the JSON (D1d).
- **Confidence** = valid scored readings / expected (festival-years in the
  data x 3 phases x 3 parameters = 54). Every missing table and cell is
  listed. Caps: at most Medium if the most recent Durga table is absent;
  at most Medium if the site name match is "medium" (D1g). Then any unpaired
  breach lowers it one level (floor Low). `cap_reasons` lists the caps used.
- **Ranking**: tier, then risk score, then lower confidence first, then name.
- **Blind spots**: ghats with no valid readings, and 2026 designated ghats
  with no data (Arch Bridge), are listed but never ranked or scored.
- **Reason text**: filled from numbers by a template, with a report page for
  every number. Up to four sentences: (1) the parameter with the largest
  baseline part, as "breached its limit in X of Y pre-immersion readings;
  worst V"; (2) the matched pair that got worse the most, as "V1 before to
  V2 during"; (3) up to two unpaired breaches, with the reason each could
  not be compared; (4) the DO = 0 flag. It never quotes averages.

### Decisions (core.txt Section 8)

- **D1a festival aggregation (decided 11 Oct 2026, reviewer decision).** The
  festival effect is the MAX over parameters of each parameter's mean triple
  score, replacing the mean over all triples. Reason: class B compliance
  fails if any one parameter fails, so a single parameter getting worse
  should not be diluted by others staying steady. Setting:
  `scoring.festival_aggregation: max` (the old rule is `mean_of_triples`).
- **D1b tier cut-offs.** With the placeholder cut-offs (High 60, Medium 35)
  all 7 ghats scored Low (range 13.9-33.6). Final cut-offs, set in Level 2
  and **not re-tuned** after D1a:
  - High >= 27.5 = 100 x (0.5 x 0.40 + 0.5 x 0.15). **Derived** from the
    baseline cut-off and festival 0.15. 0.15 was the festival driver cut-off
    until D1c replaced it; it is kept only as `festival_tier_anchor` so this
    derivation stays visible. The line itself is unchanged.
  - Medium >= 20 = 100 x (0.5 x 0.40 + 0.5 x 0). The arithmetic is derived
    from the same cut-offs, but choosing "at the baseline cut-off with no
    worsening" as the Medium anchor is a **judgement**, not a rule from
    CPCB or the brief.
  - Weights stay at 0.5 / 0.5. The rejected alternative was tertiles of the
    observed scores, which would be fitting to the data.

  Effect of D1a with the cut-offs unchanged (before -> after):

  | Ghat | Festival | Risk | Tier | Driver |
  |---|---|---|---|---|
  | Bairagarh | 0.263 -> 0.525 | 33.6 -> 46.7 | High | Poor before and worse during |
  | Shahpura | 0.230 -> 0.537 | 30.8 -> 46.2 | High | Worsens with immersion |
  | Hathaikheda | 0.300 -> 0.613 | 29.7 -> 45.3 | High | Worsens with immersion |
  | Rani Kamlapati | 0.137 -> 0.318 | 24.4 -> 33.5 | Medium -> **High** | Lower concern -> **Worsens** |
  | Malikhedi | 0.097 -> 0.149 | 24.1 -> 26.7 | Medium | Lower concern |
  | Khatlapura | 0.112 -> 0.191 | 21.1 -> 25.1 | Medium | Lower concern -> **Worsens** |
  | Prempura | 0.123 -> 0.251 | 13.9 -> 20.3 | Low -> **Medium** | Lower concern -> **Worsens** |

  Ranking order is unchanged. Tiers are now High 4, Medium 3, Low 0. BOD is
  the worst parameter at 6 of 7 ghats. Taking the max means the festival
  scores are on a larger scale than the 0.15 driver cut-off was set for, so
  6 of 7 ghats now read "worsens". Prempura (20.3) sits just above the
  Medium line.

  Malikhedi's DO festival value is 0.149 (below 0.15). Its "5.4 to 4.0
  mg/l" figure, used in earlier notes and in core.txt, compared averages
  over different tables and has been withdrawn. Matched DO pairs: Durga 2023
  4.6 to 4.3 (p.61), Durga 2024 4.5 to 4.1 (p.26), Ganesh 2023 7.5 to 7.0
  (p.27), Ganesh 2024 4.8 to 3.8 (p.71). Paired means: 5.35 to 4.8. The
  0.6 mg/l reading during Ganesh 2025 (Report 2025 p.29) has no pre reading
  and is listed as an unpaired breach.
- **D1c driver anchor (decided 11 Oct 2026, reviewer proposal; JUDGEMENT).**
  "Worsens with immersion" now means, on matched pairs averaged per
  parameter: DO falls by at least 1.0 mg/l, or BOD rises by at least 1.0
  mg/l, or the paired mean of pre is within the limit and the paired mean of
  during breaches it. Only pre-to-during pairs are used. 1 mg/l is a round,
  readable change, not a CPCB number. It was written into `rules.yaml`
  before the results were seen and has not been tuned. Disclosure: Malikhedi's
  matched DO pairs had already been seen in the previous review; no other
  ghat's matched-pair numbers had. The festival SCORE is unchanged and still
  drives risk and tier.
- **D1d near-boundary flag.** Risk within 1.5 points of a tier line sets
  `near_boundary` and `nearest_line`, so a tier that depends on a fraction
  of a point is visible. The 1.5 points is a judgement
  (`scoring.near_boundary_points`).
- **D1e unpaired breaches (JUDGEMENT on the confidence effect).** Listed,
  never dropped. One level off confidence (`unpaired_breach_downgrade: 1`)
  because a breach that cannot be compared may hide worsening the score
  does not see.

  Result of D1c-D1e (score, rank and tier unchanged from D1a):

  | Ghat | Risk | Tier | Driver (D1a -> D1c) | Confidence | Flags |
  |---|---|---|---|---|---|
  | Bairagarh | 46.7 | High | Poor before and worse during (same) | Medium -> **Low** | DO 0 x4; 2 unpaired |
  | Shahpura | 46.2 | High | Worsens (same) | High | |
  | Hathaikheda | 45.3 | High | Worsens (same) | High | |
  | Rani Kamlapati | 33.5 | High | Worsens -> **Lower concern** | High | |
  | Malikhedi | 26.7 | Medium | Lower concern -> **Worsens** (DO crossing) | Medium -> **Low** | near High (-0.8); 2 unpaired |
  | Khatlapura | 25.1 | Medium | Worsens -> **Lower concern** | High -> **Medium** | 1 unpaired |
  | Prempura | 20.3 | Medium | Worsens -> **Lower concern** | High | near Medium (+0.3) |

  Labels now: Poor before and worse during 1, Worsens 3, Lower concern 3,
  Already poor 0. Known weaknesses:
  - Rani Kamlapati is High tier but reads "Lower concern on available data".
    Its festival score (BOD 0.32, pushed up by scaled and after-phase
    changes) lifts the risk, while its matched mean BOD rise is 0.88 mg/l,
    under 1.0. The score and the label measure different things.
  - "Already poor before immersion" is used by no ghat. Only Bairagarh
    (0.409) reaches the 0.40 baseline cut-off. Shahpura (0.387) and Malikhedi
    (0.384) are just under it. That cut-off is still the Appendix A
    placeholder.
- **Disclosures on the driver cut-offs.**
  - The 0.40 baseline cut-off ("poor before") is the **Appendix A
    placeholder**. It has not been calibrated or derived. It was kept
    unchanged on purpose (reviewer instruction, 11 Oct 2026).
  - The 1 mg/l / crossing anchor (D1c) was **written after the author had
    seen Malikhedi's matched DO pairs**, which were shown in the review that
    led to it. It was fixed before any other ghat's matched-pair results were
    seen and has not been tuned since. Malikhedi passes via the crossing
    rule (paired mean 5.35 to 4.8 mg/l), not via the 1 mg/l rule (drop 0.55).
- **D1f fallback label by tier (decided 11 Oct 2026).** "Lower concern on
  available data" is said only of Low-tier ghats. Saying it next to a High
  tier read as a contradiction. A Medium/High ghat where neither driver
  triggers reads "Elevated on several measures; no single large change".
  The anchor and the 0.40 cut-off are unchanged.
- **D1g uncertain site match (decided 11 Oct 2026).** If a ghat's site match
  confidence is "medium" (Rani Kamlapati / Kamla Park kund: Ganesh tables say
  "Kamla Park kund", Durga tables say "Lower Lake ghat"), its confidence is
  at most Medium and it carries `site_match_uncertain: true` with a short
  note. Its score is unchanged. Setting: `scoring.site_match_medium_cap`.
- **D2 critical flag.** Any reported DO of exactly 0 mg/l lifts the tier to
  at least High. It is labelled as the team's own flag, not a CPCB limit.
  Bairagarh has 4 such readings (2023 Durga pre and during p.60, 2023 Ganesh
  after p.26, 2025 Ganesh during p.28) and is High on its score anyway.
- **D3 Rani Kamlapati / Kamla Park.** Kept as one ghat with the label "Site
  name match is medium confidence - may cover two places".
- **D4 not on the reported 2026 list.** Shahpura and Rani Kamlapati stay in
  the ranking with the label "Not on reported 2026 list - confirm with BMC".
  The link from designated names to data names is the explicit `data_site`
  column in `data/context/designated_ghats_2026.csv`.

### Things to know when reading the scores

- BOD breaches its limit in most pre-immersion readings at every ghat, so
  BOD drives most baselines. That is why the baseline and festival parts are
  kept apart.
- The reason text quotes single readings and matched pairs only. Paired
  means appear in the JSON (`paired_pre_mean`, `paired_during_mean`) and are
  computed over the same tables.
