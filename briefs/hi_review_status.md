# Hindi review status

**Status: NOT REVIEWED - draft by Claude (11 Oct 2026). Do not forward as final.**

- `briefs/hi.j2`: every line is a machine draft and needs review by N1 (a
  fluent Hindi reader on the team). The rendered brief carries a "Draft -
  needs human review" line until then.
- `briefs/GLOSSARY.md`: terms are drafts.
- Numbers: identical to the English brief, checked by `tests/test_brief.py`.
  The reviewer should change wording only, never numbers.
- Length: the English brief is under 250 words. The Hindi draft is longer by
  word count (Hindi postpositions count as separate words) with the same
  content.

When reviewed, set Status to "reviewed", add reviewer name and date, and
remove the draft line at the top of `hi.j2`.

| Sentence / section | Reviewer | Date | OK / changed |
|---|---|---|---|
| Title and audience | | | |
| Top ghats lines | | | |
| Where to check first | | | |
| Blind spots | | | |
| Caveats | | | |
