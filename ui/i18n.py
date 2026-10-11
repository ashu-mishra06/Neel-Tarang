"""Interface text in Hindi and English.

Hindi interface strings are a Claude draft (11 Oct 2026) and need review by a
fluent reader, like the brief did. Numbers are never translated or re-typed:
they are inserted from engine output with {placeholders}.
"""

from __future__ import annotations

from typing import Any

from scoring.brief import HI as BRIEF_HI

TEXT: dict[str, dict[str, str]] = {
    "app_tagline": {
        "en": "Which immersion ghats need attention before Durga visarjan, and why.",
        "hi": "दुर्गा विसर्जन से पहले किन घाटों पर ध्यान चाहिए, और क्यों।"},
    "banner": {
        "en": "Durga visarjan: 20 Oct 2026 | Standard: CPCB class B | Data: MPPCB 2023-2025",
        "hi": "दुर्गा विसर्जन: 20 अक्टूबर 2026 | मानक: CPCB श्रेणी B | आँकड़े: MPPCB 2023-2025"},
    "language": {"en": "Language / भाषा", "hi": "भाषा / Language"},
    "tab_rank": {"en": "Ranked ghats", "hi": "घाटों की सूची"},
    "tab_brief": {"en": "Brief", "hi": "सारांश"},
    "tab_upload": {"en": "Add new readings", "hi": "नई रीडिंग जोड़ें"},
    "tab_gaps": {"en": "Gaps & method", "hi": "कमियाँ और तरीका"},
    "kpi_ranked": {"en": "Ghats ranked", "hi": "क्रमित घाट"},
    "kpi_high": {"en": "High tier", "hi": "उच्च श्रेणी"},
    "kpi_nobase": {"en": "No baseline", "hi": "कोई पिछला आँकड़ा नहीं"},
    "kpi_unpaired": {"en": "Breaches not comparable", "hi": "तुलना न हो सकने वाले उल्लंघन"},
    "chart_title": {"en": "Why each ghat ranks where it does",
                    "hi": "हर घाट इस स्थान पर क्यों है"},
    "chart_caption": {
        "en": "Bar length = risk score. Blue part: water already poor before immersion "
              "(baseline). Orange part: water got worse during immersion (festival effect). "
              "Dashed lines: tier lines.",
        "hi": "पट्टी की लंबाई = जोखिम अंक। नीला भाग: विसर्जन से पहले ही खराब पानी (आधार)। "
              "नारंगी भाग: विसर्जन के दौरान बिगड़ा पानी (त्योहार प्रभाव)। धराशायी रेखाएँ: "
              "श्रेणी रेखाएँ।"},
    "part_baseline": {"en": "Before immersion (baseline)", "hi": "विसर्जन से पहले (आधार)"},
    "part_festival": {"en": "Worse during immersion", "hi": "विसर्जन के दौरान बिगड़ा"},
    "risk": {"en": "Risk score", "hi": "जोखिम अंक"},
    "driver": {"en": "Why", "hi": "क्यों"},
    "confidence": {"en": "Confidence", "hi": "भरोसा"},
    "of_expected": {"en": "of expected readings", "hi": "अपेक्षित रीडिंग में से"},
    "details": {"en": "Open details, charts and report pages",
                "hi": "विवरण, चार्ट और रिपोर्ट पृष्ठ खोलें"},
    "d_chart": {"en": "Before vs during", "hi": "पहले बनाम दौरान"},
    "d_numbers": {"en": "Numbers", "hi": "आँकड़े"},
    "d_evidence": {"en": "Report pages", "hi": "रिपोर्ट पृष्ठ"},
    "d_gaps": {"en": "Gaps", "hi": "कमियाँ"},
    "pairs_chart_caption": {
        "en": "Each line is one report table: the dot on the left end is before immersion, "
              "the arrow end is during. Red line = CPCB class B limit.",
        "hi": "हर रेखा एक रिपोर्ट तालिका है: एक सिरा विसर्जन से पहले, दूसरा विसर्जन के दौरान। "
              "लाल रेखा = CPCB श्रेणी B सीमा।"},
    "no_pairs": {"en": "No table has both a before and a during reading for this parameter.",
                 "hi": "इस माप के लिए किसी तालिका में पहले और दौरान दोनों रीडिंग नहीं हैं।"},
    "full_reason": {"en": "Full reason", "hi": "पूरा कारण"},
    "near_line": {"en": "Near tier line", "hi": "श्रेणी रेखा के पास"},
    "site_two": {"en": "Site may be two places", "hi": "स्थान दो जगह हो सकता है"},
    "zero_do": {"en": "Reported 0 mg/l DO", "hi": "DO 0 mg/l दर्ज"},
    "not_comparable": {"en": "breach(es) not comparable", "hi": "उल्लंघन तुलना योग्य नहीं"},
    "not_on_list": {"en": "Not on reported 2026 list - confirm with BMC",
                    "hi": "2026 की सूची में नहीं - BMC से पुष्टि करें"},
    "tier_note": {
        "en": "Tier lines: Medium ≥ {medium}, High ≥ {high}. Tiers show relative concern among "
              "these {n} ghats, not a safety certification.",
        "hi": "श्रेणी रेखाएँ: मध्यम ≥ {medium}, उच्च ≥ {high}। श्रेणियाँ इन {n} घाटों की आपसी "
              "तुलना हैं, सुरक्षा प्रमाणपत्र नहीं।"},
    "no_baseline_title": {"en": "No baseline", "hi": "कोई पिछला आँकड़ा नहीं"},
    "no_baseline_text": {
        "en": "No past readings in the MPPCB 2023-2025 reports. No score and no tier. "
              "Any test here is new information.",
        "hi": "MPPCB 2023-2025 रिपोर्ट में कोई पिछली रीडिंग नहीं। कोई अंक या श्रेणी नहीं। "
              "यहाँ कोई भी जाँच नई जानकारी होगी।"},
    "footer": {
        "en": "Readings compared with CPCB class B limits only; no health conclusions. Persona "
              "inferred from the problem statement, not from interviews.",
        "hi": "रीडिंग की तुलना केवल CPCB श्रेणी B सीमाओं से; स्वास्थ्य पर कोई निष्कर्ष नहीं। "
              "उपयोगकर्ता की ज़रूरतें समस्या विवरण से ली गई हैं, साक्षात्कार से नहीं।"},
    "ui_draft": {
        "en": "",
        "hi": "इंटरफ़ेस का हिन्दी पाठ मसौदा है (सारांश की समीक्षा हो चुकी है)। कुछ तकनीकी विवरण, "
              "जैसे रिपोर्ट तालिकाएँ, अंग्रेज़ी में हैं।"},
    "how_title": {"en": "How to read this page", "hi": "इस पृष्ठ को कैसे पढ़ें"},
    "how_body": {
        "en": "- **Tier** comes from the risk score: High ≥ {high}, Medium ≥ {medium}, else Low. "
              "A reported dissolved oxygen of 0 mg/l lifts a ghat to at least High (team's own "
              "flag, not a CPCB limit).\n- **Why** says whether the water was already poor before "
              "immersion, got worse during it, or both.\n- **Confidence** = share of expected "
              "readings that exist. A data hole never counts as clean.\n- A dashed outline marks "
              "low confidence; ≈ marks a score near a tier line.",
        "hi": "- **श्रेणी** जोखिम अंक से: उच्च ≥ {high}, मध्यम ≥ {medium}, बाकी निम्न। DO 0 mg/l "
              "दर्ज होने पर घाट कम से कम उच्च श्रेणी में (टीम का अपना संकेत, CPCB सीमा नहीं)।\n"
              "- **क्यों** बताता है कि पानी विसर्जन से पहले ही खराब था, दौरान बिगड़ा, या दोनों।\n"
              "- **भरोसा** = अपेक्षित रीडिंग में से कितनी मौजूद हैं। आँकड़ों की कमी को कभी साफ़ "
              "नहीं माना जाता।\n- धराशायी किनारा = कम भरोसा; ≈ = अंक श्रेणी रेखा के पास।"},
    "brief_reviewed": {"en": "Hindi brief reviewed by the team.",
                       "hi": "हिन्दी सारांश की टीम ने समीक्षा की है।"},
    "copy_hint": {"en": "Copy: use the copy icon at the top right of the box.",
                  "hi": "कॉपी: बॉक्स के ऊपर दाईं ओर कॉपी आइकन दबाएँ।"},
    "dl_text": {"en": "Download text", "hi": "पाठ डाउनलोड करें"},
    "dl_html": {"en": "Download print-ready HTML", "hi": "प्रिंट योग्य HTML डाउनलोड करें"},
    "brief_lang": {"en": "Brief language", "hi": "सारांश की भाषा"},
    "gaps_intro": {"en": "Everything the data does not cover. Missing data is shown as missing, "
                         "never as clean.",
                   "hi": "जो कुछ आँकड़े नहीं बताते। कमी को कमी ही दिखाया जाता है, साफ़ नहीं।"},
}

TEXT.update({
    "up_help": {
        "en": "Same columns as the MPPCB CSV. Required: site, year, festival, phase, parameter, "
              "value (or flag). Uploaded rows are 'user-supplied' and never overwrite a report "
              "value. Nothing leaves this computer.",
        "hi": "MPPCB CSV जैसे ही कॉलम। ज़रूरी: site, year, festival, phase, parameter, value "
              "(या flag)। जोड़ी गई पंक्तियाँ 'उपयोगकर्ता द्वारा दी गई' मानी जाती हैं और रिपोर्ट के "
              "मान को कभी नहीं बदलतीं। कुछ भी इस कंप्यूटर से बाहर नहीं जाता।"},
    "up_drop": {"en": "Drop a CSV here", "hi": "यहाँ CSV फ़ाइल डालें"},
    "up_sample": {"en": "Try the sample file (invented values)",
                  "hi": "नमूना फ़ाइल आज़माएँ (काल्पनिक मान)"},
    "up_download": {"en": "Download the sample CSV", "hi": "नमूना CSV डाउनलोड करें"},
    "up_remove": {"en": "Remove uploaded readings", "hi": "जोड़ी गई रीडिंग हटाएँ"},
})

TIER = {"en": {"High": "High", "Medium": "Medium", "Low": "Low", "NoData": "No baseline"},
        "hi": {**BRIEF_HI["tier"], "NoData": "कोई आधार नहीं"}}


def t(key: str, lang: str, **values: Any) -> str:
    """Interface string in `lang` ("en"/"hi"), with numbers filled in from the engine."""
    text = TEXT[key].get(lang) or TEXT[key]["en"]
    return text.format(**values) if values else text


def driver(label: str, lang: str) -> str:
    return BRIEF_HI["driver"].get(label, label) if lang == "hi" else label


def confidence(level: str, lang: str) -> str:
    return BRIEF_HI["confidence"].get(level, level) if lang == "hi" else level


def tier(level: str, lang: str) -> str:
    return TIER[lang].get(level, level)


def parameter(name: str, lang: str) -> str:
    return BRIEF_HI["parameter"].get(name, name) if lang == "hi" else name


GAP_HI: dict[str, tuple[str, str]] = {
    "missing_tables": ("गायब त्योहार-वर्ष तालिकाएँ",
                       "इन घाट-त्योहार-वर्षों की रिपोर्ट में कोई तालिका नहीं। इनके लिए कुछ भी "
                       "माना नहीं गया; भरोसा कम किया गया है।"),
    "not_sampled": ("जिन खानों में नमूना नहीं लिया गया",
                    "हर जगह 'नमूना नहीं' दिखाया गया है, कभी साफ़ या 0 नहीं।"),
    "single_column_tables": ("एक ही कॉलम वाली तालिकाएँ",
                             "इन तालिकाओं में केवल एक चरण के कॉलम में संख्याएँ हैं; बाकी खाली "
                             "(pH में * और **)। इनके उल्लंघनों की तुलना पहले की रीडिंग से नहीं "
                             "हो सकती।"),
    "unpaired_breaches": ("उल्लंघन जिनकी तुलना नहीं हो सकती",
                          "ये रीडिंग सीमा से बाहर हैं, पर उसी तालिका में पहले की रीडिंग नहीं। "
                          "अंक नहीं बदलते; भरोसा एक स्तर कम होता है।"),
    "ghats_no_valid_data": ("बिना मान्य रीडिंग वाले घाट",
                            "आँकड़ों में हैं पर अंक देने लायक कुछ नहीं; सूची में नहीं।"),
    "designated_not_in_data": ("2026 के घाट जिनकी कोई पिछली रीडिंग नहीं",
                               "2026 के विसर्जन घाट के रूप में बताए गए, पर MPPCB 2023-2025 "
                               "रिपोर्ट में नहीं। कोई अंक या श्रेणी नहीं; यहाँ कोई भी जाँच नई "
                               "जानकारी होगी।"),
    "not_on_2026_list": ("2026 की सूची में न होने वाले घाट",
                         "पिछली रीडिंग हैं पर 2026 गणेश सूची में नहीं थे। सूची में रखे गए हैं; "
                         "दुर्गा के लिए BMC से पुष्टि करें।"),
    "site_match_uncertain": ("स्थान दो जगह हो सकता है",
                             "गणेश तालिकाओं में 'Kamla Park kund', दुर्गा तालिकाओं में 'Lower "
                             "Lake ghat'। एक ही घाट माना गया; भरोसा अधिकतम मध्यम।"),
    "only_four_metals": ("केवल चार धातुओं की जाँच; किसी की श्रेणी B सीमा नहीं",
                         "क्रोमियम, सीसा, जस्ता, ताँबा केवल संदर्भ के लिए दिखाए गए हैं, अंक में "
                         "नहीं। BDL का अर्थ बहुत कम है, शून्य नहीं।"),
    "units_assumed": ("इकाइयाँ मानी गई हैं",
                      "रिपोर्ट में इकाइयाँ नहीं छपीं। आयोजकों ने हर जाँच की मानक इकाई मानी है।"),
    "standard_choice": ("उपयोग किया गया मानक: CPCB श्रेणी B (बाहरी स्नान)",
                        "रीडिंग की तुलना केवल इसकी सीमाओं से; स्वास्थ्य पर कोई निष्कर्ष नहीं।"),
    "lake_vs_kund": ("पिछली रीडिंग झील किनारे के घाटों की हैं",
                     "2026 में विसर्जन कुंडों में होना है; पुरानी रीडिंग नई व्यवस्था का हाल "
                     "नहीं बता सकतीं।"),
    "designated_list_source": ("2026 की सूची एक समाचार रिपोर्ट से",
                               "गणेश 2026 की सूची Free Press Journal (22 सितंबर 2026) से। दुर्गा "
                               "की सूची अलग हो सकती है - BMC से पुष्टि करें।"),
    "bdl_on_scored": ("अंक वाले माप पर BDL", "अप्रत्याशित: pH, DO या BOD पर BDL।"),
}


def gap_text(gap: Any, lang: str) -> tuple[str, str]:
    """Gap title and explanation in the chosen language (items stay as the engine wrote them)."""
    if lang == "hi" and gap.id in GAP_HI:
        return GAP_HI[gap.id]
    return gap.title, gap.detail


PERSIST_HI = {"Repeat": "बार-बार", "One-off": "एक बार", "Intermittent": "कभी-कभी",
              "Never breached": "कभी नहीं", "Too few tables": "बहुत कम तालिकाएँ"}


def persistence_badge(r: dict[str, Any], rule: str, lang: str) -> str:
    """Persistence badge text (7A) in the chosen language; numbers from the engine."""
    if lang != "hi":
        word = {"min": "below", "max": "above"}.get(rule, "outside")
        return (f"{r['label']}: {r['parameter']} {word} limit {r['phase']} immersion in "
                f"{r['breaches']} of {r['valid_tables']} tables "
                f"({r['missing_tables']} not sampled)")
    word = {"min": "नीचे", "max": "ऊपर"}.get(rule, "बाहर")
    phase = "दौरान" if r["phase"] == "during" else "से पहले"
    return (f"{PERSIST_HI.get(r['label'], r['label'])}: विसर्जन {phase} "
            f"{parameter(r['parameter'], 'hi')} {r['valid_tables']} में से {r['breaches']} "
            f"तालिकाओं में सीमा से {word} ({r['missing_tables']} में नमूना नहीं)")
