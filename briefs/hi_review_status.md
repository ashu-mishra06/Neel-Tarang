# Hindi review status

**Status: reviewed** - Hindi brief reviewed by Ashutosh Mishra (team), 11 Oct 2026, as reported
to Claude in the build session. Drafted by Claude.

Changed after the review (needs a quick re-check): the brief's new persistence line
("विसर्जन के दौरान ... तालिकाओं में सीमा से ऊपर/नीचे") and the shorter heading.

Not yet reviewed: the Hindi *interface* text added later the same day (`ui/i18n.py`,
labels, help text and gap explanations). It is marked as a draft in the app.

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
