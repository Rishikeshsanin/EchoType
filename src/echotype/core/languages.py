from __future__ import annotations

import unicodedata

AUTO = "auto"

# code, display name, writing script, scheduled/primary UI language
LANGUAGES = [
    ("auto", "Auto-detect", None, True),
    ("as", "Assamese", "BENGALI", True),
    ("bn", "Bengali", "BENGALI", True),
    ("brx", "Bodo", "DEVANAGARI", True),
    ("doi", "Dogri", "DEVANAGARI", True),
    ("en", "English", "LATIN", True),
    ("gu", "Gujarati", "GUJARATI", True),
    ("hi", "Hindi", "DEVANAGARI", True),
    ("kn", "Kannada", "KANNADA", True),
    ("kok", "Konkani", "DEVANAGARI", True),
    ("mai", "Maithili", "DEVANAGARI", True),
    ("ml", "Malayalam", "MALAYALAM", True),
    ("mni", "Manipuri", "BENGALI", True),
    ("mr", "Marathi", "DEVANAGARI", True),
    ("ne", "Nepali", "DEVANAGARI", True),
    ("or", "Odia", "ORIYA", True),
    ("pa", "Punjabi", "GURMUKHI", True),
    ("sa", "Sanskrit", "DEVANAGARI", True),
    ("sat", "Santali", "OL", True),
    ("sd", "Sindhi", "DEVANAGARI", True),
    ("ta", "Tamil", "TAMIL", True),
    ("te", "Telugu", "TELUGU", True),
    ("njm", "Angami", "LATIN", False),
    ("njo", "Ao", "LATIN", False),
    ("awa", "Awadhi", "DEVANAGARI", False),
    ("bjj", "Bajjika", "DEVANAGARI", False),
    ("bry", "Bearybashe", "KANNADA", False),
    ("bhb", "Bhili", "DEVANAGARI", False),
    ("bho", "Bhojpuri", "DEVANAGARI", False),
    ("bns", "Bundeli", "DEVANAGARI", False),
    ("nbc", "Chakhesang", "LATIN", False),
    ("ccp", "Chakma", "BENGALI", False),
    ("hne", "Chhattisgarhi", "DEVANAGARI", False),
    ("grt", "Garo", "LATIN", False),
    ("gbm", "Garhwali", "DEVANAGARI", False),
    ("gon", "Gondi", "DEVANAGARI", False),
    ("hlb", "Halbi", "DEVANAGARI", False),
    ("bgc", "Haryanvi", "DEVANAGARI", False),
    ("clk", "Idu Mishmi", "LATIN", False),
    ("mjw", "Karbi", "LATIN", False),
    ("kfx", "Khariboli", "DEVANAGARI", False),
    ("kho", "Khortha", "DEVANAGARI", False),
    ("trp", "Kokborok", "BENGALI", False),
    ("kru", "Kurukh", "DEVANAGARI", False),
    ("mag", "Magadhi", "DEVANAGARI", False),
    ("mvi", "Malvani", "DEVANAGARI", False),
    ("mwr", "Marwari", "DEVANAGARI", False),
    ("lus", "Mizo", "LATIN", False),
    ("nag", "Nagamese", "LATIN", False),
    ("njz", "Nyishi", "LATIN", False),
    ("raj", "Rajasthani", "DEVANAGARI", False),
    ("nnl", "Rengma", "LATIN", False),
    ("nbu", "Rongmei", "LATIN", False),
    ("sck", "Sadri", "DEVANAGARI", False),
    ("spv", "Sambalpuri", "ORIYA", False),
    ("nsm", "Sumi", "LATIN", False),
    ("sgj", "Surgujia", "DEVANAGARI", False),
    ("sjp", "Surjapuri", "DEVANAGARI", False),
    ("tgj", "Tagin", "LATIN", False),
    ("tcy", "Tulu", "KANNADA", False),
    ("wnc", "Wancho", "LATIN", False),
]

BY_CODE = {code: (name, script, scheduled) for code, name, script, scheduled in LANGUAGES}
BY_NAME = {name: code for code, name, _script, _scheduled in LANGUAGES}

SCRIPT_LABELS = {
    "DEVANAGARI": "Devanagari",
    "BENGALI": "Bengali",
    "KANNADA": "Kannada",
    "TELUGU": "Telugu",
    "TAMIL": "Tamil",
    "MALAYALAM": "Malayalam",
    "GUJARATI": "Gujarati",
    "GURMUKHI": "Gurmukhi",
    "ORIYA": "Odia",
    "LATIN": "Latin",
    "OL": "Ol Chiki",
}

SCRIPT_DEFAULT_LANGUAGE = {
    "DEVANAGARI": "hi",
    "BENGALI": "bn",
    "KANNADA": "kn",
    "TELUGU": "te",
    "TAMIL": "ta",
    "MALAYALAM": "ml",
    "GUJARATI": "gu",
    "GURMUKHI": "pa",
    "ORIYA": "or",
    "LATIN": "en",
    "OL": "sat",
}


def display_names(scheduled_first: bool = True) -> list[str]:
    scheduled = [name for code, name, _script, primary in LANGUAGES if primary and code != AUTO]
    other = [name for _code, name, _script, primary in LANGUAGES if not primary]
    if scheduled_first:
        return ["Auto-detect"] + sorted(scheduled) + sorted(other)
    return ["Auto-detect"] + sorted(scheduled + other)


def code_for_name(name: str) -> str:
    return BY_NAME.get(name, AUTO)


def name_for_code(code: str) -> str:
    entry = BY_CODE.get(code)
    return entry[0] if entry else "Auto-detect"


def script_for_code(code: str) -> str | None:
    entry = BY_CODE.get(code)
    return entry[1] if entry else None


def detect_script(text: str) -> str | None:
    counts: dict[str, int] = {}
    for char in text or "":
        if not char.isalpha():
            continue
        try:
            script = unicodedata.name(char).split(" ")[0]
        except ValueError:
            continue
        counts[script] = counts.get(script, 0) + 1
    return max(counts, key=counts.get) if counts else None


def script_label(script: str | None) -> str:
    return SCRIPT_LABELS.get(script, (script or "unknown").title())


def describe(text: str, selected_code: str = AUTO) -> dict[str, object]:
    """Describe script evidence without overstating it as true LID.

    V1 often displayed a default language for a script. V2 keeps that useful
    hint but explicitly labels shared-script cases so UI copy can distinguish
    script detection from actual language identification.
    """
    script = detect_script(text)
    result: dict[str, object] = {
        "script": script,
        "script_label": script_label(script),
        "language": None,
        "mismatch": False,
        "note": "",
        "is_script_hint": True,
    }
    if script is None:
        return result

    if selected_code and selected_code != AUTO:
        expected = script_for_code(selected_code)
        chosen_name = name_for_code(selected_code)
        result["language"] = chosen_name
        if expected and expected != script:
            result["mismatch"] = True
            result["note"] = f"Expected {chosen_name}; received {script_label(script)} script"
        return result

    result["language"] = name_for_code(SCRIPT_DEFAULT_LANGUAGE.get(script, AUTO))
    shared_notes = {
        "DEVANAGARI": "Script hint only — Devanagari is shared by Hindi, Marathi, Nepali and others.",
        "BENGALI": "Script hint only — Bengali script is shared by Bengali, Assamese and Manipuri.",
        "KANNADA": "Script hint only — Kannada script is shared by Kannada and Tulu.",
        "LATIN": "Script hint only — Latin script does not uniquely identify English.",
    }
    result["note"] = shared_notes.get(script, "Script detected; language identification is not yet enabled.")
    return result
