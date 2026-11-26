"""Script normalisation: Kannada to everyday Indian-English spelling, homoglyphs, diacritics.

The output aims at how a Karnataka clerk would spell the name in English
(ಸ್ವರೂಪ್ ಗೌಡ -> "swaroop gowda"), not at scholarly transliteration, because the
other side of every comparison is written that way.
"""

import re
import unicodedata

from .switches import ON

_VIRAMA = "್"
_NUKTA = "಼"
_ANUSVARA = "ಂ"
_VISARGA = "ಃ"

_VOWELS = {
    "ಅ": "a", "ಆ": "aa", "ಇ": "i", "ಈ": "ee", "ಉ": "u", "ಊ": "oo", "ಋ": "ri", "ೠ": "ri",
    "ಎ": "e", "ಏ": "e", "ಐ": "ai", "ಒ": "o", "ಓ": "o", "ಔ": "au",
}
_SIGNS = {
    "ಾ": "aa", "ಿ": "i", "ೀ": "ee", "ು": "u", "ೂ": "oo", "ೃ": "ri", "ೄ": "ri",
    "ೆ": "e", "ೇ": "e", "ೈ": "ai", "ೊ": "o", "ೋ": "o", "ೌ": "au",
}
_CONSONANTS = {
    "ಕ": "k", "ಖ": "kh", "ಗ": "g", "ಘ": "gh", "ಙ": "n",
    "ಚ": "ch", "ಛ": "chh", "ಜ": "j", "ಝ": "jh", "ಞ": "n",
    "ಟ": "t", "ಠ": "th", "ಡ": "d", "ಢ": "dh", "ಣ": "n",
    "ತ": "th", "ಥ": "th", "ದ": "d", "ಧ": "dh", "ನ": "n",
    "ಪ": "p", "ಫ": "ph", "ಬ": "b", "ಭ": "bh", "ಮ": "m",
    "ಯ": "y", "ರ": "r", "ಱ": "r", "ಲ": "l", "ವ": "v",
    "ಶ": "sh", "ಷ": "sh", "ಸ": "s", "ಹ": "h", "ಳ": "l", "ೞ": "l",
}
_NUKTA_FORMS = {"ಜ": "z", "ಫ": "f"}
_JNA = "\ue000"            # stands in for ಜ್ಞ while a run is read (kannada_jna)
_DIGITS = {chr(0x0CE6 + i): str(i) for i in range(10)}

# Cyrillic and Greek capitals that OCR or copy-paste leaves inside Latin names.
_HOMOGLYPHS = str.maketrans({
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P", "С": "C", "Т": "T",
    "Х": "X", "У": "Y", "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x",
    "Α": "A", "Β": "B", "Ε": "E", "Η": "H", "Ι": "I", "Κ": "K", "Μ": "M", "Ν": "N", "Ο": "O",
    "Ρ": "P", "Τ": "T", "Χ": "X", "Υ": "Y", "Ζ": "Z",
    " ": " ", "‌": "", "‍": "", "﻿": "", "•": " ",
})


def has_kannada(text: str) -> bool:
    return any("ಀ" <= ch <= "೿" for ch in text)


# Initials are written in Kannada as the English letter's name (ಬಿ = "bi" = B).
_LETTER_NAMES = {
    "e": "a", "a": "a", "bi": "b", "si": "c", "see": "c", "di": "d", "dee": "d", "i": "e", "ee": "e",
    "eph": "f", "ef": "f", "ji": "g", "jee": "g", "ech": "h", "hech": "h", "ej": "h", "aai": "i", "ai": "i",
    "je": "j", "jai": "j", "ke": "k", "el": "l", "em": "m", "en": "n", "o": "o", "pi": "p", "pee": "p",
    "kyu": "q", "aar": "r", "ar": "r", "es": "s", "ti": "t", "tee": "t", "yu": "u", "vi": "v", "vee": "v",
    "dablyu": "w", "eks": "x", "vai": "y", "jhed": "z", "zed": "z",
}


# Put around each word that came from Kannada when the caller asks (parse, for cross_script).
KN_OPEN, KN_CLOSE = "\x02", "\x03"


def kannada_to_latin(text: str, mark: bool = False) -> str:
    """Transliterate each Kannada run; a run that spells a letter's name becomes that letter."""
    out = []
    for run in re.split(r"([\u0c80-\u0cff\u200c\u200d]+)", text):
        if run and has_kannada(run):
            latin = _kannada_run(run)
            latin = _LETTER_NAMES.get(latin, latin)
            out.append(KN_OPEN + latin + KN_CLOSE if mark else latin)
        else:
            out.append(run)
    return "".join(out)


def _kannada_run(text: str) -> str:
    out = []
    if ON["kannada_jna"]:
        text = text.replace("ಜ್ಞ", _JNA).replace("ಜ್ಙ", _JNA)     # ಜ್ಙ: a common misspelling of ಜ್ಞ
    chars = list(text)
    i = 0
    while i < len(chars):
        ch = chars[i]
        nxt = chars[i + 1] if i + 1 < len(chars) else ""
        if ch in _CONSONANTS or ch == _JNA:
            base = "gn" if ch == _JNA else _CONSONANTS[ch]
            if nxt == _NUKTA:
                base = _NUKTA_FORMS.get(ch, base)
                i += 1
                nxt = chars[i + 1] if i + 1 < len(chars) else ""
            if nxt == _VIRAMA:
                out.append(base)
                i += 2
                continue
            if nxt in _SIGNS:
                out.append(base + _SIGNS[nxt])
                i += 2
                continue
            out.append(base + "a")
            i += 1
            continue
        if ch in _VOWELS:
            out.append(_VOWELS[ch])
        elif ch == _ANUSVARA:
            follower = _CONSONANTS.get(nxt, "")
            # Before a labial or at the end of a word it sounds 'm' (ಎಂ = em = M, ಕೋಂ = kom).
            out.append("m" if not nxt or follower[:1] in ("p", "b", "m") else "n")
        elif ch == _VISARGA:
            out.append("h")
        elif ch in _DIGITS:
            out.append(_DIGITS[ch])
        elif ch in (_VIRAMA, _NUKTA, "‌", "‍"):
            pass
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def to_latin(text: str, mark: bool = False) -> str:
    """Any supported script to plain ASCII-ish Latin, case preserved for Latin input.
    mark=True wraps each word that came from Kannada in KN_OPEN ... KN_CLOSE."""
    text = unicodedata.normalize("NFC", text).translate(_HOMOGLYPHS)
    if has_kannada(text):
        text = kannada_to_latin(text, mark)
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))
