"""Turn a raw owner-name string into structured persons and organisations.

Handles the shapes seen across Draft Khata, Aadhaar, registered deeds and property tax:
several owners in one string, numbering, honorifics, relation clauses (S/o, W/o, bin, ಕೋಂ),
GPA / "rep by" clauses, aliases, companies, placeholders, joined initials and Kannada script.
"""

import re
from dataclasses import dataclass, field

from .phonetic import canonical
from .rules import RULES
from .switches import ON
from .translit import has_kannada, to_latin

_L = RULES["lists"]
_HONORIFICS = set(RULES["honorifics"])
_FEMALE_HON = set(RULES["female_honorifics"])
_MALE_HON = set(RULES["male_honorifics"])
# Title words that are also given names, kept when nothing else is left ("Miss Kumari").
_TITLE_OR_NAME = {"kumari", "baby", "master", "major", "selvi", "chiranjeevi"}
_HONORIFICS_ANYWHERE = {"late", "smt", "mrs", "mr", "dr", "shrimati", "srimati", "smti"}
_ORG_WORDS = set(_L["org_words"]) - {"m/s"}
_PLACEHOLDERS = set(RULES["lists"]["placeholders"]) if "placeholders" in RULES["lists"] else set()
_VARIANT_WORDS = {m for g in RULES["variants"]["groups"] for m in g}
_VOWELS = set("aeiouy")
# Initials spelled out in English letters by the digitisers ("EM ANITA" = M Anita).
_SPELLED_INITIALS = {"em": "m", "en": "n", "es": "s", "el": "l", "aar": "r", "ech": "h", "hech": "h", "jee": "g"}
_FILLER = {"his", "her", "their", "its", "the", "holder", "gpa", "by", "of", "power", "attorney", "agreement", "sale"}

# Marker tokens inserted into the text before tokenising.
SEP, REL, REP, ALIAS = "\x01sep", "\x01rel", "\x01rep", "\x01alias"


@dataclass
class Token:
    text: str
    initial: bool

    def __repr__(self) -> str:
        return self.text.upper() + "." if self.initial else self.text


@dataclass
class Person:
    tokens: list[Token]
    aliases: list[list[Token]] = field(default_factory=list)
    relative: list[Token] = field(default_factory=list)
    gender: str = ""            # "m", "f" or "" from honorific / relation evidence
    relation: str = ""          # kind of the relation clause: "s/o", "w/o", "bin", "kom", ...
    role: str = "owner"         # "owner" or "representative"
    firm: bool = False          # written as "M/s <person name>": a proprietorship

    @property
    def full(self) -> list[str]:
        return [t.text for t in self.tokens if not t.initial]

    @property
    def initials(self) -> list[str]:
        return [t.text for t in self.tokens if t.initial]

    def __repr__(self) -> str:
        s = " ".join(map(repr, self.tokens))
        if self.relative:
            s += " (rel " + " ".join(map(repr, self.relative)) + ")"
        if self.gender:
            s += f" [{self.gender}]"
        if self.role != "owner":
            s += f" <{self.role}>"
        return s


@dataclass
class Organisation:
    tokens: list[str]
    raw: str

    def __repr__(self) -> str:
        return "ORG(" + " ".join(self.tokens) + ")"


@dataclass
class ParsedName:
    raw: str
    persons: list[Person]
    orgs: list[Organisation]
    representatives: list[Person]
    placeholder: bool
    script: str                 # "latin" or "kannada"

    @property
    def empty(self) -> bool:
        return not self.persons and not self.orgs


def _phrase_regex(phrases, marker):
    alts = sorted((re.escape(p).replace(r"\ ", r"[\s.]*") for p in phrases), key=len, reverse=True)
    return re.compile(r"(?<![a-z\x01:])(?:" + "|".join(alts) + r")(?![a-z])"), marker


# "S/o", "s / o", "S\\o", "s/olate", and the slash lost in digitisation ("W O") between words.
_REL_SLASH = re.compile(r"(?<![a-z/])([sdwhc])\s*[/\\]\s*o(?=late(?![a-z])|[^a-z]|$)\.?"
                        r"|(?<=[a-z])([sdw])/o(?=[^a-z]|$)"
                        r"|(?<![a-z.])([sdw])\s+o(?=\s+[a-z])(?![a-z])"
                        r"|(?<![a-z])([sdw])\.\s*o\.")
# "<agent> GPA holder for <owner>": the owner comes after.
_HOLDER_FOR = re.compile(r"^(.*?)(?<![a-z])(?:(?:is\s+)?(?:the\s+)?(?:(?:gpa|spa|poa|pa|power of attorney)\s*)?holders?"
                         r"|is\s+(?:the\s+)?(?:gpa|spa|poa|pa))\s+(?:for|of)(?![a-z])(.*)$")
_REL_WORDS = [k for k in RULES["relations"] if "/" not in k]
_REL_GENDER = RULES["relations"]
_SUBS = [
    _phrase_regex(_L["trailing"], " "),
    _phrase_regex([p for p in _L["representation"]], f" {REP} "),
    _phrase_regex([a for a in _L["alias"] if a != "@"], f" {ALIAS} "),
    _phrase_regex(_REL_WORDS, None),
]


def _relation_marker(m: re.Match) -> str:
    """'son of' -> ' \\x01rel:son_of '. Outside the f-string: Python 3.11 allows no backslash in one."""
    kind = re.sub(r"[\s.]+", " ", m.group(0)).strip().replace(" ", "_")
    return f" {REL}:{kind} "


def _mark(text: str) -> str:
    text = re.sub(r"[=*_~`^]", "", text)
    if ON["holder_for"]:
        text = "|".join(_HOLDER_FOR.sub(r"\2 rep by \1", part) for part in text.split("|"))
    text = text.replace("@", f" {ALIAS} ")
    text = _REL_SLASH.sub(lambda m: f" {REL}:{next(g for g in m.groups() if g)}/o ", text)
    for regex, marker in _SUBS:
        if marker is None:
            text = regex.sub(_relation_marker, text)
        else:
            text = regex.sub(marker, text)
    # Owner separators. "an" is a common typo for "and" between names.
    text = re.sub(r"[|;&+()\[\]{}\n\t]", f" {SEP} ", text)
    # "mattu" is Kannada for "and", left untranslated by the digitisers.
    text = re.sub(r"(?<![a-z\x01:])(and|an|with|mattu|maththu|haagu)(?![a-z])", f" {SEP} ", text)
    text = re.sub(r",", f" {SEP} ", text)
    # Numbering ("1.", "2)", "(3)") and stray digits separate owners; digits inside words are OCR slips.
    text = re.sub(r"(?<![a-z0-9])\d+(?![a-z0-9])", f" {SEP} ", text)
    text = re.sub(r"[a-z]*\d[a-z0-9]*", _ocr_digits, text)
    return text


_OCR = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "6": "g", "8": "b", "9": "g", "2": "z", "7": "t"})


def _ocr_digits(m: re.Match) -> str:
    word = m.group(0)
    return word.translate(_OCR) if re.search(r"[a-z]", word) else f" {SEP} "


def _join_letters(words: list[str]) -> list[str]:
    out, run = [], ""
    for w in words:
        if len(w) == 1:
            run += w
            continue
        if run:
            out.append(run)
            run = ""
        out.append(w)
    if run:
        out.append(run)
    return [w for w in out if w not in ("p",)]


def _split_word(word: str) -> list[Token]:
    """Short vowel-less clusters are joined initials: 'ns' -> N S, 'kb' -> K B."""
    if ON["spelled_initials"] and word in _SPELLED_INITIALS:
        return [Token(_SPELLED_INITIALS[word], True)]
    if len(word) == 1:
        return [Token(word, True)]
    if len(word) <= 3 and not (set(word) & _VOWELS) and word not in _VARIANT_WORDS:
        return [Token(c, True) for c in word]
    return [Token(word, False)]


def _clean_person(words: list[str]) -> tuple[list[Token], str]:
    gender = ""
    original = words
    # Leading honorifics, possibly several ("mr dr", "surg lt cdr").
    while words and words[0] in _HONORIFICS:
        if words[0] in _FEMALE_HON:
            gender = "f"
        elif words[0] in _MALE_HON:
            gender = "m"
        words = words[1:]
    words = [w for w in words if w not in _HONORIFICS_ANYWHERE]
    if not words and original and original[-1] in _TITLE_OR_NAME:
        words = original[-1:]           # "Miss Kumari": the title word is the name
    tokens = [t for w in words for t in _split_word(w)]
    return tokens, gender


def _is_org(words: list[str], raw_segment: str) -> bool:
    return "m/s" in raw_segment or "m/ s" in raw_segment or any(w in _ORG_WORDS for w in words)


def parse(raw: str) -> ParsedName:
    raw = raw or ""
    script = "kannada" if has_kannada(raw) else "latin"
    latin = to_latin(raw)
    # In capitals, a two-letter word without a dot before a name is joined initials, not a
    # title or "and": "MS RAMESH" = M S Ramesh, "AN RAMESH" = A N Ramesh.
    latin = re.sub(r"(?<![A-Za-z.])(MS|MR|SH|AN|NA)(?=\s+[A-Z]{2,})", lambda m: " ".join(m.group(1)), latin)
    text = _mark(latin.lower())
    # Tokenise into markers and words; any other punctuation is whitespace.
    pieces = re.findall(r"\x01\w+(?::[\w/]+)?|m/s|[a-z]+", text.replace("'", " ").replace("-", " "))

    segments: list[dict] = []
    current = None

    def new_segment():
        seg = {"name": [], "alias": [], "rel": [], "rel_kind": "", "rep": [], "mode": "name"}
        segments.append(seg)
        return seg

    current = new_segment()
    for piece in pieces:
        if piece == SEP:
            current = new_segment()
        elif piece.startswith(REL):
            kind = piece.split(":", 1)[1] if ":" in piece else ""
            if not current["name"] and len(segments) > 1 and segments[-2]["name"] and not segments[-2]["rel"]:
                # "G. Prakash, S/o Ranga Rao": the clause belongs to the previous owner.
                segments.pop()
                current = segments[-1]
            if current["mode"] in ("rep", "rep_rel"):
                current["mode"] = "rep_rel"     # a relative of the representative: not evidence
                continue
            current["mode"] = "rel"
            current["rel_kind"] = kind.replace("_", " ")
        elif piece == REP:
            current["mode"] = "rep"
        elif piece == ALIAS:
            current["mode"] = "alias"
            current["alias"].append([])
        else:
            mode = current["mode"]
            if mode == "rep_rel":
                continue
            if mode == "name":
                current["name"].append(piece)
            elif mode == "alias":
                current["alias"][-1].append(piece)
            else:
                current[mode].append(piece)

    # "(India) Pvt Ltd" after a company name is part of it, not another owner.
    org_tail = set(RULES["lists"]["org_noise"]) | _ORG_WORDS
    merged = []
    for seg in segments:
        if merged and seg["name"] and all(w in org_tail for w in seg["name"]) and not seg["rel"] and not seg["rep"]:
            merged[-1]["name"].extend(seg["name"])
        else:
            merged.append(seg)
    segments = merged

    persons, orgs, reps = [], [], []
    placeholder = False
    for seg in segments:
        words = seg["name"]
        if not words and not seg["rep"]:
            continue
        if words:
            segment_text = " ".join(words)
            if words[0] == "m/s" and not any(w in _ORG_WORDS for w in words):
                tokens, gender = _clean_person([w for w in words[1:] if w not in _PLACEHOLDERS])
                if any(not t.initial for t in tokens):
                    persons.append(Person(tokens, gender=gender, firm=True))
            elif _is_org(words, segment_text):
                org_words = _join_letters([w for w in words if w not in RULES["lists"]["org_noise"] or len(w) == 1])
                if org_words:
                    orgs.append(Organisation([canonical(w) for w in org_words], segment_text))
            else:
                meaningful = [w for w in words if w not in _PLACEHOLDERS]
                if not meaningful:
                    placeholder = True
                else:
                    tokens, gender = _clean_person(meaningful)
                    rel_tokens, _ = _clean_person(seg["rel"]) if seg["rel"] else ([], "")
                    rel_gender = _REL_GENDER.get(seg["rel_kind"], "")
                    aliases = [a for a in (_clean_person(x)[0] for x in seg["alias"]) if a]
                    p = Person(tokens, aliases, rel_tokens, gender or rel_gender, relation=seg["rel_kind"])
                    if any(not t.initial for t in tokens) or p.aliases:
                        persons.append(p)
                    elif tokens and not persons and not seg["rep"]:
                        persons.append(p)
        if seg["rep"]:
            tokens, gender = _clean_person([w for w in seg["rep"] if w not in _PLACEHOLDERS and w not in _FILLER])
            if any(not t.initial for t in tokens):
                reps.append(Person(tokens, gender=gender, role="representative"))
    return ParsedName(raw, persons, orgs, reps, placeholder and not persons and not orgs, script)
