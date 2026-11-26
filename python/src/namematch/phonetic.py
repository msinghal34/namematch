"""Phonetic keys and token similarity tuned for Indian names written in Latin script.

The key folds the spelling freedom of romanised Indian names (aspirates, long vowels,
w/v, z/j, ksh/x, -iah/-ayya, final -a, doubled letters) so that common variants
collide, while the edit-distance fallback absorbs whatever the rules miss.
"""

import re
from functools import lru_cache

from .rules import NAME_GENDER, RULES
from .switches import ON

_VARIANT = {}
for group in RULES["variants"]["groups"]:
    for member in group:
        _VARIANT[member] = group[0]

# Ordered rewrites; each is (regex, replacement).
_REWRITES = [
    (r"ksh", "ks"),
    (r"x", "ks"),
    (r"q", "k"),
    (r"z", "j"),
    (r"w", "v"),
    (r"ph", "f"),
    (r"ck", "k"),
    (r"chh", "ch"),
    (r"ch", "C"),          # protect ch while c becomes k
    (r"c", "k"),
    (r"C", "c"),
    (r"sh", "s"),
    (r"th", "t"),
    (r"dh", "d"),
    (r"bh", "b"),
    (r"gh", "g"),
    (r"kh", "k"),
    (r"jh", "j"),
    (r"ee|ii|ie(?=.)", "i"),
    (r"oo|uu", "u"),
    (r"ow|ou|au|ao", "au"),
    (r"aa", "a"),
    (r"ei|ey(?=.)", "ai"),
    (r"(?<=[^aeiou])y$", "i"),
    (r"aiah$|aiya$|ayya$|iah$|aya$", "aya"),
    (r"ayi$|ay$", "ai"),
    (r"(?<=[aeiou])h$", ""),
    (r"(?<=[^aeiou])h(?=[^aeiou]|$)", ""),
    (r"(.)\1+", r"\1"),
]
_REWRITES = [(re.compile(p), r) for p, r in _REWRITES]


_MINED = {}
for group in RULES["variants"].get("mined_groups", []):
    for member in group:
        _MINED.setdefault(member, _VARIANT.get(group[0], group[0]))


def canonical(token: str) -> str:
    if ON["mined_variants"] and token in _MINED and token not in _VARIANT:
        return _MINED[token]
    return _VARIANT.get(token, token)


@lru_cache(maxsize=200_000)
def key(token: str) -> str:
    """Phonetic key of the token's canonical spelling (variants table applied first)."""
    return _fold(canonical(token)) or token


@lru_cache(maxsize=200_000)
def raw_key(token: str) -> str:
    """Phonetic key of the token as written, for spellings the variants table does not list."""
    return _fold(token) or token


@lru_cache(maxsize=200_000)
def gender_key(token: str) -> str:
    """Key that keeps name endings, which carry gender (kamal / kamala, madhav / madhavi)."""
    return _fold(token, endings=False) or token


_FEMALE_END = tuple(RULES["gender"]["female_suffixes"])
_MALE_END = tuple(RULES["gender"]["male_suffixes"])


def gender_of(token: str) -> str:
    """'m' or 'f': first from how the records use this given name, else from an ending that only
    one gender takes (-amma, -kumari, -begum / -appa, -ayya, -kumar); '' when unknown."""
    g = NAME_GENDER.get(gender_key(token), "")
    if g:
        return g
    for ends, gender in ((_FEMALE_END, "f"), (_MALE_END, "m")):
        if any(token.endswith(e) and len(token) >= len(e) + 3 for e in ends):
            return gender
    return ""


_OW = re.compile(r"ow(?=[^aeiou]|$)")
_JN = re.compile(r"^jn")
_Y_VOWEL = re.compile(r"(?<=[^aeiou])y(?=[^aeiouy])")


def _fold(t: str, endings: bool = True) -> str:
    # Before the ordered rewrites, which turn w into v and would hide 'ow' (sowmya, gowri).
    if ON["ow_vowel"]:
        t = _OW.sub("au", t)
    if ON["y_vowel"]:
        t = _Y_VOWEL.sub("ai", t)
    if ON["kannada_jna"]:
        # Only at the start of a word: jnana / gnana, jnanesh / gnanesh. Inside a word jn is usually
        # j + n (Rajni, Sajni, Anjna), so it is left alone there; ಜ್ಞ inside a Kannada word is handled
        # by _readings.
        t = _JN.sub("gn", t)
    for _ in range(2):          # second pass catches endings exposed by the first ('bhimaiaha')
        for pattern, repl in _REWRITES:
            t = pattern.sub(repl, t)
        if not endings:
            continue
        if len(t) > 3 and t.endswith("a"):
            t = t[:-1]
        # Tamil -an on a name ending in s / n / p: srinivasan ~ srinivas, narayanan ~ narayana,
        # muniyappan ~ muniyappa. Not rahman / salman / lakshman / sultan / kalyan.
        if len(t) > 5 and t.endswith("an") and t[-3] in "snp":
            t = t[:-2]
    return t


def levenshtein(a: str, b: str) -> int:
    """Edit distance counting an adjacent swap ('deepit' / 'deepti') as one edit."""
    if a == b:
        return 0
    d = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        d[i][0] = i
    for j in range(len(b) + 1):
        d[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cost = a[i - 1] != b[j - 1]
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[-1][-1]


def _is_subsequence(short: str, long: str) -> bool:
    it = iter(long)
    return all(ch in it for ch in short)


def skeleton(k: str) -> str:
    """Consonants of a key: 'kumr' and 'kumar' share 'kmr'."""
    return k[0] + re.sub(r"[aeiouy]", "", k[1:])


def _ratio(a: str, b: str) -> float:
    return 1 - levenshtein(a, b) / max(len(a), len(b), 1)


_PAIRS = [(m, f) for m, f in RULES["gender"]["pairs"]]


def gender_conflict(a: str, b: str) -> bool:
    """Opposite genders on look-alike names: mallappa / mallamma, kumar / kumari, and any pair
    the records show with opposite genders (kamal / kamala, salman / salma, madhav / madhavi)."""
    ga, gb = gender_of(a), gender_of(b)
    if ga and gb and ga != gb and gender_key(a)[:3] == gender_key(b)[:3]:
        return True
    for male, female in _PAIRS:
        for x, y in ((a, b), (b, a)):
            if x.endswith(male) and y.endswith(female):
                stem_x, stem_y = x[: -len(male)], y[: -len(female)]
                if stem_x == stem_y or (min(len(stem_x), len(stem_y)) >= 2 and key(stem_x) == key(stem_y)):
                    return True
    return False


@lru_cache(maxsize=500_000)
def similarity(a: str, b: str) -> float:
    """Similarity of two full name tokens in [0, 1]; 0 means 'not the same word'."""
    if a == b:
        return 1.0
    if canonical(a) == canonical(b):
        return 0.98
    if gender_conflict(a, b):
        return 0.0
    ka, kb = key(a), key(b)
    if ka == kb or raw_key(a) == raw_key(b) or raw_key(a) == kb or ka == raw_key(b):
        return 0.95
    ka, kb = raw_key(a), raw_key(b)
    shortest = min(len(ka), len(kb))
    if shortest < 3:
        return 0.0
    # Only dropped vowels ('kumr' / 'kumar'), never changed ones ('kamal' / 'komal').
    short_k, long_k = sorted((ka, kb), key=len)
    if ON["vowel_drop"] and (len(skeleton(short_k)) >= 3 or len(short_k) >= 4) \
            and skeleton(short_k) == skeleton(long_k) and _is_subsequence(short_k, long_k):
        return 0.86
    r_key = _ratio(ka, kb)
    r_raw = _ratio(a, b)
    best = max(r_key * 0.95, r_raw * 0.92)
    # Short names need near-identity (kamala / komal); long words tolerate a slip or two.
    floor = 0.84 if (len(long_k) <= 6 if ON["short_floor"] else shortest <= 4) else 0.74 if shortest <= 7 else 0.70
    if max(r_key, r_raw) < floor:
        return 0.0
    # The first sound carries more identity than the rest.
    if ka[0] != kb[0] and not {ka[0], kb[0]} <= {"s", "c", "j", "v", "b", "e", "i", "a", "u", "o"}:
        best *= 0.8
    return round(best, 3)




@lru_cache(maxsize=500_000)
def vowel_slip(a: str, b: str, a_kn: bool = False, b_kn: bool = False) -> bool:
    """Two words with the same first letter and the same consonants in the same order, only the vowels
    different or moved: a slip in English ('pravin' / 'parvin', 'sunil' / 'sunel'), or a name spelled
    by sound across scripts (a Kannada word is tried in each of its readings). Different names fit too
    (kamala / komal, ಕೃತಿಕಾ Kritika ~ Kartik), so this only ever sends a pair to an officer
    (score.person_score caps it below 0.65). Never across genders."""
    ra = _readings(a) if a_kn and not b_kn else [a]
    rb = _readings(b) if b_kn and not a_kn else [b]
    for x in ra:
        for y in rb:
            if gender_conflict(x, y) or (a_kn != b_kn and (cross_gender_conflict(x, y) if a_kn else cross_gender_conflict(y, x))):
                continue
            kx, ky = raw_key(x), raw_key(y)
            if min(len(kx), len(ky)) >= 4 and kx[0] == ky[0] and kx != ky and skeleton(kx) == skeleton(ky) \
                    and len(skeleton(kx)) >= 2:
                return True
    return False


def initial_of(token: str) -> set[str]:
    """Letters a writer might use as this word's initial."""
    first = token[0]
    alts = {first}
    if token.startswith(("sh", "ch")):
        alts.add(token[0])
    if first in "vw":
        alts |= {"v", "w"}
    if first in "jz":
        alts |= {"j", "z"}
    if first in "ei":
        alts |= {"e", "i"}
    return alts


# Gender endings whose final a is part of the ending, never Kannada's silent final a: the a-final ones in
# rules.toml (amma, appa, ayya) and the Kannada kinship endings -akka and -avva (Hanumakka, Basavva).
_GENDER_SUFFIXES = tuple(e for e in _FEMALE_END + _MALE_END if e.endswith("a")) + ("akka", "avva")
_CONSONANT_Y = re.compile(r"[^aeiou]y$")


def _inherent_a(k: str) -> bool:
    """A Kannada word's final short a (ವಿನಯ -> 'vinaya'), which English spelling usually drops and
    which does not say the name is female; a long final aa (ಸವಿತಾ -> 'savitaa') is left alone, and so
    is the a of a gender ending (-amma, -appa, -ayya: ಮುನಿಯಮ್ಮ is not 'muniyamm')."""
    if len(k) <= 3 or not k.endswith("a") or k.endswith("aa") or k.endswith(_GENDER_SUFFIXES):
        return False
    # Not when what is left ends in consonant + y: 'adity' would read as 'aditi' (Aditya, a man, vs Aditi).
    return not _CONSONANT_Y.search(k[:-1])


def cross_gender_conflict(k: str, latin: str) -> bool:
    """Gender conflict between a word written in Kannada (k) and one written in English: with a final
    short a in Kannada, both readings (with and without it) must conflict."""
    return gender_conflict(k, latin) and (not _inherent_a(k) or gender_conflict(k[:-1], latin))


_YAA = re.compile(r"(?<=[^aeiouy])y(?=aa)")
_NASAL_N = re.compile(r"n(?=[^aeiouyn])")


def _readings(k: str) -> list[str]:
    """Other ways the Kannada-written word k may be the English spelling of the same name: Kannada writes
    the English 'a' of Das or Jan as ಯಾ ('dyaas', 'jyaan'), and its nasal sign before a consonant comes
    out as n where English writes m (ಹಂಸ 'hansa' ~ Hamsa, ಇಂತಿಯಾಜ್ ~ Imtiaz). Each pattern was seen in 15 or
    more different names in the eAasthi export."""
    out = {k}
    if ON["cross_readings"]:
        for f in (lambda t: _YAA.sub("", t), lambda t: _NASAL_N.sub("m", t)):
            out |= {f(t) for t in out}
    if ON["kannada_jna"]:
        # ಜ್ಞ is written gn (Pragna) or jn (Prajna) in English; translit gives gn.
        out |= {t.replace("gn", "jn") for t in out}
    return sorted(out)


@lru_cache(maxsize=500_000)
def cross_similarity(k: str, latin: str) -> float:
    """similarity() for a word written in Kannada (k) against one written in English (cross_script).
    Kannada's final short a may be the English name without it (ಪ್ರವೀಣ ~ Praveen), and _readings gives
    the other ways the Kannada spelling may stand for the English one; any of them counts as a spelling
    variant (at most 0.95). Vowels-only differences are vowel_slip, which only sends a pair to an
    officer."""
    s = similarity(k, latin)
    gk, gl = gender_of(k), gender_of(latin)
    # Names of opposite genders (Salma / Salim, ಶಿವಲಿಂಗಮ್ / Shivalingamma) may meet through another reading
    # only where that reading gives the English name itself, not a loose match: a reading can turn the
    # word into one of unknown gender, which would otherwise slip past the gender check.
    opposite = bool(gk and gl and gk != gl) or gender_conflict(k, latin)

    def counts(score):
        return not opposite or score >= 0.95

    for r in _readings(k):
        if r != k:                                  # another reading: a spelling variant at best
            other = similarity(r, latin)
            if counts(other):
                s = max(s, min(other, 0.95))
        if _inherent_a(r):
            stripped = similarity(r[:-1], latin)
            if counts(stripped):
                s = max(s, min(stripped, 0.95))
    return s
