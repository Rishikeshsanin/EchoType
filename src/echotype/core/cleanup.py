from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

VERBATIM = "verbatim"
SMART = "smart"
NOTES = "notes"
MODES = {VERBATIM, SMART, NOTES}

FILLERS = ("um", "uh", "umm", "uhh", "erm", "er", "hmm", "hmmm", "mmm", "mhm")
FILLER_PHRASES = (
    "you know what i mean",
    "if that makes sense",
    "or something like that",
    "i mean like",
    "sort of like",
    "kind of like",
    "you know",
)

SPOKEN_PUNCT = (
    (r"\bnew paragraph\b", "\n\n"),
    (r"\bnew line\b", "\n"),
    (r"\bnext line\b", "\n"),
    (r"\bfull stop\b", "."),
    (r"\bperiod\b", "."),
    (r"\bcomma\b", ","),
    (r"\bquestion mark\b", "?"),
    (r"\bexclamation (?:mark|point)\b", "!"),
    (r"\bsemicolon\b", ";"),
    (r"\bcolon\b", ":"),
    (r"\bopen paren(?:thesis)?\b", "("),
    (r"\bclose paren(?:thesis)?\b", ")"),
    (r"\bhyphen\b", "-"),
)

DANDA_SCRIPTS = {"DEVANAGARI", "BENGALI", "GURMUKHI", "ORIYA", "GUJARATI"}
SEC_PER_CHAR = 0.075
BASE_WORD_SEC = 0.10
SENTENCE_PAUSE = 0.55
CLAUSE_PAUSE = 0.28

BUILTIN_ALIASES = {
    "EchoType": ["echo type", "echotype"],
    "SraVaani": ["sravani", "shravani", "sravaani", "shravaani", "sra vani", "srivani"],
    "ARTPARK": ["art park", "artpark", "aart park"],
    "IISc": ["i i s c", "iisc", "i isc", "i is c", "indian institute of science"],
    "PyTorch": ["pie torch", "pytorch", "py torch"],
    "GitHub": ["git hub", "github"],
}

COMPOUNDS = set(
    """
    tomorrow today tonight yesterday everyone everybody everything everywhere
    someone somebody something somewhere anyone anybody anything anywhere
    nobody nothing nowhere myself yourself himself herself itself ourselves
    themselves cannot maybe already although because before behind below
    between beyond within without inside outside however therefore meanwhile
    otherwise nevertheless whatever whenever wherever whoever forever forward
    backward afternoon weekend birthday classroom keyboard notebook laptop
    software hardware database website online offline username password filename
    framework homework breakfast sunlight daylight nowadays understand update
    upload download upgrade output input overall overview background foreground
    feedback newspaper bookmark bedroom bathroom airport railway highway worldwide
    lifetime sometimes another throughout moreover furthermore timeline deadline
    headline guideline baseline pipeline network wallpaper screenshot smartphone
    microphone headphone loudspeaker earphone playback setup login logout signup
    """.split()
)

SPLIT_WORDS = {
    "alot": "a lot",
    "infront": "in front",
    "eachother": "each other",
    "aswell": "as well",
    "atleast": "at least",
    "incase": "in case",
    "thankyou": "thank you",
    "goodmorning": "good morning",
    "goodevening": "good evening",
    "goodnight": "good night",
    "everytime": "every time",
    "inspite": "in spite",
    "ofcourse": "of course",
    "eventhough": "even though",
}

CONTRACTIONS = (
    (r"\bdont\b", "don't"),
    (r"\bcant\b", "can't"),
    (r"\bwont\b", "won't"),
    (r"\bdoesnt\b", "doesn't"),
    (r"\bdidnt\b", "didn't"),
    (r"\bisnt\b", "isn't"),
    (r"\bwasnt\b", "wasn't"),
    (r"\barent\b", "aren't"),
    (r"\bshouldnt\b", "shouldn't"),
    (r"\bcouldnt\b", "couldn't"),
    (r"\bwouldnt\b", "wouldn't"),
    (r"\bhavent\b", "haven't"),
    (r"\bhasnt\b", "hasn't"),
    (r"\bthats\b", "that's"),
    (r"\blets\b", "let's"),
    (r"\bim\b", "I'm"),
    (r"\bive\b", "I've"),
)


@dataclass(slots=True)
class CleanupResult:
    text: str
    mode: str
    changed: bool


def script_of(text: str) -> str:
    counts: dict[str, int] = {}
    for char in text:
        if not char.isalpha():
            continue
        try:
            script = unicodedata.name(char).split(" ")[0]
        except ValueError:
            continue
        counts[script] = counts.get(script, 0) + 1
    return max(counts, key=counts.get) if counts else "UNKNOWN"


def is_latin(text: str) -> bool:
    return script_of(text) == "LATIN"


def normalize_whitespace(text: str) -> str:
    out = re.sub(r"[ \t]+", " ", text)
    out = re.sub(r" *\n *", "\n", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def _strip_fillers(text: str) -> str:
    out = text
    for phrase in FILLER_PHRASES:
        out = re.sub(
            r"(?<!\w)" + re.escape(phrase) + r"(?!\w)[,]?\s*",
            " ",
            out,
            flags=re.IGNORECASE,
        )
    filler_pattern = r"(?<!\w)(?:" + "|".join(map(re.escape, FILLERS)) + r")(?!\w)[,]?\s*"
    return re.sub(filler_pattern, " ", out, flags=re.IGNORECASE)


def _collapse_stutters(text: str) -> str:
    return re.sub(
        r"(?<!\S)([^\s.,;:!?]{1,12})(\s+\1){2,}(?!\S)",
        r"\1",
        text,
        flags=re.IGNORECASE,
    )


def _apply_spoken_punctuation(text: str) -> str:
    out = text
    for pattern, replacement in SPOKEN_PUNCT:
        out = re.sub(pattern, replacement, out, flags=re.IGNORECASE)
    out = re.sub(r"\s+([,.;:!?])", r"\1", out)
    out = re.sub(r"([,.;:!?])(?=[^\s\d])", r"\1 ", out)
    out = re.sub(r"\(\s+", "(", out)
    out = re.sub(r"\s+\)", ")", out)
    return out


def _capitalise(text: str) -> str:
    def uppercase(match: re.Match[str]) -> str:
        return match.group(0).upper()

    out = re.sub(r"(?:^|(?<=[.!?])\s+|(?<=\n))([a-z])", uppercase, text)
    return re.sub(r"(?<!\w)i(?!\w)", "I", out)


def apply_vocabulary(text: str, vocabulary) -> str:
    wanted = {str(item).strip().lower(): str(item).strip() for item in (vocabulary or []) if str(item).strip()}
    out = text

    for canonical, variants in BUILTIN_ALIASES.items():
        if wanted and canonical.lower() not in wanted:
            continue
        for variant in sorted(variants, key=len, reverse=True):
            pattern = r"(?<!\w)" + re.escape(variant).replace(r"\ ", r"[\s-]+") + r"(?!\w)"
            out = re.sub(pattern, canonical, out, flags=re.IGNORECASE)

    for canonical in wanted.values():
        compact = [re.escape(char) for char in canonical if not char.isspace()]
        if len(compact) < 2:
            continue
        pattern = r"(?<!\w)" + r"\s*[-\s]?\s*".join(compact) + r"(?!\w)"
        try:
            out = re.sub(pattern, canonical, out, flags=re.IGNORECASE)
        except re.error:
            continue
    return out


def merge_split_compounds(text: str, extra=None) -> str:
    if not text or not is_latin(text):
        return text
    vocabulary = set(COMPOUNDS)
    for word in extra or []:
        normalized = str(word).strip().lower()
        if normalized and " " not in normalized:
            vocabulary.add(normalized)

    pattern = re.compile(r"\b([A-Za-z']+)\s+([A-Za-z']+)\b")

    def merge(match: re.Match[str]) -> str:
        first, second = match.group(1), match.group(2)
        joined = (first + second).lower()
        if joined not in vocabulary:
            return match.group(0)
        result = joined.capitalize() if first[:1].isupper() else joined
        return result

    # Two passes catch cases such as "some where else" without an unbounded loop.
    return pattern.sub(merge, pattern.sub(merge, text))


def split_merged_words(text: str) -> str:
    if not text or not is_latin(text):
        return text
    pattern = r"(?<!\w)(?:" + "|".join(sorted(SPLIT_WORDS, key=len, reverse=True)) + r")(?!\w)"

    def replace(match: re.Match[str]) -> str:
        source = match.group(0)
        fixed = SPLIT_WORDS[source.lower()]
        return fixed.capitalize() if source[:1].isupper() else fixed

    return re.sub(pattern, replace, text, flags=re.IGNORECASE)


def fix_contractions(text: str) -> str:
    out = text
    for pattern, replacement in CONTRACTIONS:
        out = re.sub(pattern, replacement, out, flags=re.IGNORECASE)
    return out


def sentence_mark_for(script: str) -> str:
    return "।" if script in DANDA_SCRIPTS else "."


def _excess_silence(word: str, start: float, end: float) -> float:
    expected = BASE_WORD_SEC + SEC_PER_CHAR * max(len(word.strip()), 1)
    return max((end - start) - expected, 0.0)


def segment_by_pauses(
    word_timestamps,
    *,
    sentence_pause: float = SENTENCE_PAUSE,
    clause_pause: float = CLAUSE_PAUSE,
    sentence_mark: str = ".",
) -> str:
    if not word_timestamps:
        return ""
    words = [item for item in word_timestamps if str(item.get("word", "")).strip()]
    pieces: list[str] = []
    for index, item in enumerate(words):
        token = str(item["word"]).strip()
        pieces.append(token)
        if index == len(words) - 1:
            break
        excess = _excess_silence(token, float(item["start"]), float(item["end"]))
        if len(token) <= 2 and excess < sentence_pause:
            pieces.append(" ")
        elif excess >= sentence_pause:
            pieces.append(sentence_mark + "\n")
        elif excess >= clause_pause:
            pieces.append(", ")
        else:
            pieces.append(" ")
    return normalize_whitespace("".join(pieces))


def clean(
    text: str,
    *,
    mode: str = SMART,
    spoken_punctuation: bool = True,
    vocabulary=None,
) -> CleanupResult:
    if mode not in MODES:
        mode = SMART
    original = (text or "").strip()
    if not original:
        return CleanupResult("", mode, False)

    # Verbatim intentionally avoids semantic/grammar edits. We still normalize
    # whitespace because the decoder may emit inconsistent spacing.
    if mode == VERBATIM:
        output = normalize_whitespace(original)
        return CleanupResult(output, mode, output != original)

    output = _collapse_stutters(original)
    latin = is_latin(output)
    if latin:
        output = _strip_fillers(output)
        if spoken_punctuation:
            output = _apply_spoken_punctuation(output)

    output = normalize_whitespace(output)
    if vocabulary:
        output = apply_vocabulary(output, vocabulary)

    if latin:
        output = split_merged_words(output)
        output = merge_split_compounds(output, vocabulary)
        output = fix_contractions(output)
        output = _capitalise(output)

    output = normalize_whitespace(output)
    return CleanupResult(output, mode, output != original)


def clean_hypothesis(
    hypothesis,
    *,
    mode: str = SMART,
    spoken_punctuation: bool = True,
    vocabulary=None,
    auto_punctuate: bool = True,
) -> CleanupResult:
    raw_text = getattr(hypothesis, "text", None) or str(hypothesis)

    if mode != VERBATIM and auto_punctuate:
        timestamps = getattr(hypothesis, "timestamp", None) or {}
        words = timestamps.get("word") if isinstance(timestamps, dict) else None
        if words:
            try:
                raw_text = segment_by_pauses(
                    words,
                    sentence_mark=sentence_mark_for(script_of(raw_text)),
                )
            except Exception:
                pass

    return clean(
        raw_text,
        mode=mode,
        spoken_punctuation=spoken_punctuation,
        vocabulary=vocabulary,
    )


def word_count(text: str) -> int:
    return len([word for word in re.split(r"\s+", text.strip()) if word])
