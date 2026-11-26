"""Score how strongly two names denote the same person, the way a revenue officer reads them.

The score is evidence-weighted coverage: distinctive words that agree push it up, common
words (Kumar, Reddy) count for less, an initial that explains a spelled-out word counts as
weak agreement, and two different words in the same name, contradicting initials, or
opposite genders pull it down hard.
"""

import math
from dataclasses import dataclass, field

from .parse import Organisation, ParsedName, Person, Token, parse
from .phonetic import cross_gender_conflict, cross_similarity, gender_conflict, gender_key, gender_of, initial_of, key, similarity, vowel_slip
from .rules import NAME_GENDER, TOKEN_FREQ, TOKEN_PERSONS
from .switches import ON

MATCH_FLOOR = 0.70          # token similarity below this is "not the same word"
NEAR_SIM = 0.75             # a vowel-slip word (same consonants, vowels differ) when it is allowed
NEAR_CAP = 0.64             # ... and the most such a pair can score: "needs a check", never accepted
INITIAL_CONFLICT = 0.6      # per pair of initials that disagree: the same given name with another father
CARRIED_CAP = 0.6           # her name in front of his (Rekha Mahesh Kulkarni / Mahesh Kulkarni): a relative
# A part counts as common from 25 sightings per 153,218 persons: the sample the weights were tuned on.
_COMMON_RATE = 25 / 153_218


_COMMON = _COMMON_RATE * TOKEN_PERSONS if TOKEN_PERSONS else 25
_TOP = max(TOKEN_FREQ.values(), default=1)


def _table():
    """(counts, 'common' threshold, largest count) of the frequency table."""
    return TOKEN_FREQ, _COMMON, _TOP


# Bands, calibrated on a labelled development set of name pairs.
BANDS = [(0.80, "same"), (0.65, "likely_same"), (0.35, "review"), (0.0, "different")]


def weight(token: str) -> float:
    """1.0 for a distinctive word, down to 0.35 for the commonest (kumar)."""
    freq, common, top = _table()
    n = freq.get(key(token), 0)
    if n <= common:
        return 1.0
    return 1.0 - 0.65 * math.log(n / common) / math.log(top / common)


def _total(values) -> float:
    """Plain left-to-right sum. Python 3.12's sum() compensates rounding, so it differs in the last
    bits from Python 3.11 and from Java; this keeps scores identical everywhere."""
    t = 0.0
    for v in values:
        t += v
    return t


def band(score: float) -> str:
    return next(name for floor, name in BANDS if score >= floor)


@dataclass
class MatchResult:
    score: float
    band: str
    reasons: list[str] = field(default_factory=list)
    left: str = ""
    right: str = ""
    owners: str = "any"                                   # how several owners were combined (OWNER_MODES)
    partial: bool = False                                 # with several owners, some owner has no counterpart >= 0.80
    owners_a: list[dict] = field(default_factory=list)    # per owner in A: its best counterpart in B and the score
    owners_b: list[dict] = field(default_factory=list)    # per owner in B: its best counterpart in A and the score

    def __repr__(self) -> str:
        return f"MatchResult({self.score:.2f} {self.band}: {self.left} ~ {self.right}; {'; '.join(self.reasons)})"


@dataclass
class _Unit:
    idx: frozenset
    text: str
    w: float
    kn: bool = False        # some word of it came from Kannada script


def _similar(x: str, x_kn: bool, y: str, y_kn: bool, recorded: str = "") -> float:
    """Word similarity; a Kannada-written word against an English-written one uses cross_similarity,
    unless `recorded`, the gender the Kannada side's record states (Smt, W/o, D/o, kom), contradicts
    the English name: then Kannada's readings may not override that evidence (ಶ್ರೀಮತಿ ಪ್ರವೀಣ is not Praveen)."""
    if ON["cross_script"] and x_kn != y_kn:
        k, latin = (x, y) if x_kn else (y, x)
        g = gender_of(latin)
        if recorded and g and g != recorded:
            return similarity(k, latin)
        return cross_similarity(k, latin)
    return similarity(x, y)


def _gender_clash(x: Token, y: Token) -> bool:
    if ON["cross_script"] and x.kn != y.kn:
        return cross_gender_conflict(x.text, y.text) if x.kn else cross_gender_conflict(y.text, x.text)
    return gender_conflict(x.text, y.text)


def _units(tokens: list[Token]) -> list[_Unit]:
    """Each full word, plus runs of 2-3 adjacent full words joined (for 'Sura Narayana' ~ 'Suranarayana')."""
    out = []
    n = len(tokens)
    for i, t in enumerate(tokens):
        if t.initial:
            continue
        out.append(_Unit(frozenset([i]), t.text, weight(t.text), t.kn))
        for j in (i + 2, i + 3):
            run = tokens[i:j]
            if j <= n and all(not x.initial for x in run):
                out.append(_Unit(frozenset(range(i, j)), "".join(x.text for x in run), max(weight(x.text) for x in run),
                                 any(x.kn for x in run)))
    return out


def _score_tokens(a: list[Token], b: list[Token], rel_a: list[Token] = (), rel_b: list[Token] = (),
                  near: bool = False, gender_a: str = "", gender_b: str = "") -> tuple[float, list[str], dict]:
    reasons: list[str] = []
    ua, ub = _units(a), _units(b)
    candidates = []
    near_pairs = set()
    for x in ua:
        for y in ub:
            if len(x.idx) > 1 and len(y.idx) > 1:
                continue
            recorded = gender_a if x.kn else gender_b       # the gender the Kannada side's record states
            s = _similar(x.text, x.kn, y.text, y.kn, recorded)
            if s < MATCH_FLOOR and near and len(x.idx) == 1 and len(y.idx) == 1:
                latin_gender = gender_of(y.text if x.kn else x.text)
                # Across scripts only with cross_script, and never against the gender the Kannada record states.
                cross = x.kn != y.kn
                if (not cross or (ON["cross_script"] and not (recorded and latin_gender and latin_gender != recorded))) \
                        and vowel_slip(x.text, y.text, x.kn and cross, y.kn and cross):
                    s = NEAR_SIM
                    near_pairs.add((x.text, y.text))
            if s >= MATCH_FLOOR:
                candidates.append((s, len(x.idx) + len(y.idx), x, y))
    candidates.sort(key=lambda c: (c[0], c[1]), reverse=True)

    used_a, used_b = set(), set()
    matched_mass = matched_w = 0.0
    for s, _, x, y in candidates:
        if x.idx & used_a or y.idx & used_b:
            continue
        used_a |= x.idx
        used_b |= y.idx
        w = (x.w + y.w) / 2
        matched_mass += s * w
        matched_w += w
        if (x.text, y.text) in near_pairs:
            reasons.append(f"{x.text}?{y.text} vowels differ")
        elif x.text != y.text:
            reasons.append(f"{x.text}~{y.text} {s:.2f}")

    free_a = [i for i, t in enumerate(a) if not t.initial and i not in used_a]
    free_b = [i for i, t in enumerate(b) if not t.initial and i not in used_b]
    init_a = [i for i, t in enumerate(a) if t.initial and i not in used_a]
    init_b = [j for j, t in enumerate(b) if t.initial and j not in used_b]

    # Initials against initials of the same letter.
    agreed = 0
    for i in list(init_a):
        for j in init_b:
            if a[i].text == b[j].text:
                init_a.remove(i)
                init_b.remove(j)
                agreed += 1
                break

    first_a = next((i for i, t in enumerate(a) if not t.initial), None)
    first_b = next((j for j, t in enumerate(b) if not t.initial), None)

    # Initials that explain a spelled-out word on the other side ('K' ~ 'Krishnamurthy').
    explained_w = 0.0
    for inits, side, other_free in ((init_a, a, free_b), (init_b, b, free_a)):
        other = b if side is a else a
        for i in list(inits):
            for j in other_free:
                if side[i].text in initial_of(other[j].text):
                    inits.remove(i)
                    other_free.remove(j)
                    explained_w += weight(other[j].text)
                    reasons.append(f"{side[i].text.upper()}.={other[j].text}")
                    break

    # A word on one side that is the other side's recorded relative ('PRABHAKARA K NARASIMHA'
    # vs 'PRABHAKARA K S/O K NARASIMHA'): the father's name appended, not a different person.
    # Only when the person who carries the relative was matched by their own given name:
    # 'ANAND RAO' vs 'SAVITA RAO W/O ANAND RAO' is her husband (Savita unmatched), while
    # 'NAVEED AKHTAR RUKSANA BANU' vs 'RUKSANA BANU W/O NAVEED AKHTAR' is her, with him run in.
    if ON["relative_explains"]:
        for side, free, rel, carrier_named in ((a, free_a, rel_b, first_b in used_b), (b, free_b, rel_a, first_a in used_a)):
            if not carrier_named:
                continue
            rel_words = [t.text for t in rel if not t.initial]
            for i in list(free):
                if any(similarity(side[i].text, r) >= MATCH_FLOOR for r in rel_words):
                    free.remove(i)
                    explained_w += weight(side[i].text)
                    reasons.append(f"{side[i].text}=relative")

    init_conflicts = min(len(init_a), len(init_b))
    # An initial left over on one side while the other side still has an unexplained word:
    # 'Kavya Thimmappa K' vs 'K B Thimmappa' - B. should have been Kavya and is not.
    word_conflicts = 0
    if ON["word_conflict"] and not init_conflicts:
        word_conflicts = min(len(init_a), len(free_b)) + min(len(init_b), len(free_a))
    missing_inits = max(len(init_a), len(init_b)) - init_conflicts - word_conflicts
    if missing_inits:
        reasons.append("initials on one side only: " + " ".join([a[i].text.upper() for i in init_a]
                                                                  + [b[j].text.upper() for j in init_b]))


    gender_clash = any(_gender_clash(a[i], b[j]) for i in free_a for j in free_b)
    mass_a = _total(weight(a[i].text) for i in free_a)
    mass_b = _total(weight(b[j].text) for j in free_b)
    conflict = min(mass_a, mass_b) if free_a and free_b else 0.0
    extra = max(mass_a, mass_b) - conflict

    info = dict(word_conflicts=word_conflicts, conflict=conflict, extra=extra, gender_clash=gender_clash,
                init_conflicts=init_conflicts, missing_inits=missing_inits, agreed=agreed, explained=explained_w)
    if matched_w == 0:
        if gender_clash:
            reasons.append("gender conflict")
        return 0.0, reasons, info

    # An extra word on one side (surname, father's name) costs less than a word that disagrees.
    denominator = matched_w + conflict + extra * 0.4 + explained_w * 0.08 + missing_inits * 0.08
    score = matched_mass / denominator
    if conflict:
        score *= 0.55
        names = [a[i].text for i in free_a] + ["/"] + [b[j].text for j in free_b]
        reasons.append("differs: " + " ".join(names))
    elif extra:
        reasons.append("extra: " + " ".join([a[i].text for i in free_a] + [b[j].text for j in free_b]))
    if init_conflicts:
        score *= INITIAL_CONFLICT ** init_conflicts
        reasons.append(f"initials differ ({init_conflicts})")
    if word_conflicts:
        # Milder when the given names (leading words) agree: 'Raghunandan B K' vs 'Raghunandan Venugopal Sharma'.
        given_agree = first_a in used_a and first_b in used_b
        score *= (0.85 if given_agree else 0.5) ** word_conflicts
        reasons.append(f"initial does not fit a word ({word_conflicts})")
    if gender_clash:
        score = min(score, 0.2)
        reasons.append("gender conflict")
    if ON["carried_name"] and score > CARRIED_CAP:
        # 'REKHA MAHESH KULKARNI' vs 'Mahesh Kulkarni', 'PRIYA ARVIND' vs 'ARVIND P': a woman's own name,
        # unmatched or only an initial's, in front of a man's name that matches the other side's given
        # name. She carries her husband's or father's name; she is not him. Not when her name and the next
        # word are together a man's name the records list: 'LAKSHMI NARAYANA' vs 'L NARAYANA' is one man
        # (the records only, not an ending: Vandana + Nandkumar ends in -kumar but is no name).
        for side, used, first, o_used, o_first in ((a, used_a, first_a, used_b, first_b), (b, used_b, first_b, used_a, first_a)):
            if first is None or first in used or o_first is None or o_first not in o_used:
                continue
            nxt = next((i for i in range(first + 1, len(side)) if not side[i].initial), None)
            if nxt is not None and NAME_GENDER.get(gender_key(side[first].text + side[nxt].text)) == "m":
                continue
            if gender_of(side[first].text) == "f" and gender_of((b if side is a else a)[o_first].text) != "f" \
                    and any(gender_of(side[i].text) == "m" for i in used if not side[i].initial):
                score = CARRIED_CAP
                reasons.append(f"{side[first].text} carries a man's name: a relative")
                break
    return score, reasons, info


_PARENT = {"s/o", "d/o", "bin", "binti", "bint", "son of", "daughter of"}
_SPOUSE = {"w/o", "h/o", "kom", "kon", "wife of", "husband of"}


def _kind(relation: str) -> str:
    return "parent" if relation in _PARENT else "spouse" if relation in _SPOUSE else ""


def _relatives(p: Person, q: Person, score: float, reasons: list[str]) -> tuple[float, list[str]]:
    """Use the recorded relatives as evidence against, not only for, a match."""
    if not ON["relative_conflict"] or score == 0:
        return score, reasons
    kp, kq = _kind(p.relation), _kind(q.relation)
    if p.relative and q.relative and kp and kq:
        r, _, _ = _score_tokens(p.relative, q.relative)
        if kp == kq and r < 0.35:
            # 'Ramesh S/o Krishna' vs 'Ramesh S/o Gopal': namesakes with different fathers.
            return score * 0.5, reasons + ["relatives differ"]
        if kp != kq and r >= 0.8:
            # 'Lakshmi W/o Ramesh' vs 'Lakshmi D/o Ramesh': his wife and his daughter.
            return score * 0.5, reasons + ["same relative, different relation"]
    # An initial usually stands for the father: 'RAMESH B' vs 'RAMESH S/O KRISHNA'.
    for x, y in ((p, q), (q, p)):
        if _kind(y.relation) != "parent" or not y.relative or x.relative:
            continue
        father = [t.text for t in y.relative if not t.initial]
        own = set(x.initials) - set(y.initials)
        if ON["father_initial_fit"] and father and own and not any(i in initial_of(father[0]) for i in own):
            # 'S Ganapati' vs 'GANAPATI SHENOY S/O RAMAPPA SHENOY': S. is Shenoy, a word y has, not the father.
            # Not by the given name itself: in 'R RAMESH' vs 'RAMESH S/O GOPAL' the R is not Ramesh.
            words = [t.text for t in y.tokens if not t.initial][1:]
            own = {i for i in own if not any(i in initial_of(w) for w in words)}
        if father and own and not any(i in initial_of(father[0]) for i in own):
            return score * 0.75, reasons + [f"initials {' '.join(sorted(own)).upper()} do not fit father {father[0]}"]
    return score, reasons


def _variants(p: Person) -> list[list[Token]]:
    return [p.tokens] + p.aliases


def person_score(p: Person, q: Person) -> tuple[float, list[str]]:
    score, reasons = _person_score(p, q, near=False)
    # A pair the rules call different gets a second look allowing words whose vowels differ
    # (Praveen / Parvin, Sunil / Sunel, ಕೃತಿಕಾ / Kartik). Such a pair goes to an officer, never to
    # acceptance, and a pair the rules already score 0.35 or more is left exactly as it was.
    if ON["vowel_slip"] and score < 0.35:
        s2, r2 = _person_score(p, q, near=True)
        s2 = min(s2, NEAR_CAP)
        if s2 > score and any(r.endswith("vowels differ") for r in r2):
            return s2, r2 + ["vowels differ: needs a check"]
    return score, reasons


def _person_score(p: Person, q: Person, near: bool) -> tuple[float, list[str]]:
    best = None
    for ta in _variants(p):
        for tb in _variants(q):
            s, reasons, _ = _score_tokens(ta, tb, p.relative, q.relative, near, p.gender, q.gender)
            if best is None or s > best[0]:
                best = (s, reasons)
    score, reasons = best
    score, reasons = _relatives(p, q, score, reasons)
    if ON["firm_cap"] and p.firm != q.firm and score > 0.6:
        score, reasons = 0.6, reasons + ["M/s firm named after a person"]
    if p.gender and q.gender and p.gender != q.gender and score > 0.35:
        score = 0.35
        reasons = reasons + ["opposite honorific/relation gender"]
    return score, reasons


def org_score(o: Organisation, r: Organisation) -> tuple[float, list[str]]:
    a = [Token(t, False) for t in o.tokens]
    b = [Token(t, False) for t in r.tokens]
    s, reasons, _ = _score_tokens(a, b)
    return s, reasons


def _entities(p: ParsedName):
    return [("person", x) for x in p.persons] + [("org", x) for x in p.orgs]


OWNER_MODES = {
    "any": "best pair: any owner in A matching any owner in B is enough",
    "all_a": "every owner in A must match some owner in B (the weakest one decides)",
    "all": "every owner on both sides must pair one-to-one with an owner on the other side",
}
ACCEPT = BANDS[0][0]


def _pair_score(ka, ea, kb, eb) -> tuple[float, list[str]]:
    if ka != kb:
        return 0.0, ["person vs organisation"]
    if ka == "person":
        return person_score(ea, eb)
    return org_score(ea, eb)


def _owner_rows(ents_x, ents_y, scores, transpose=False) -> list[dict]:
    rows = []
    for i, (_, ex) in enumerate(ents_x):
        best_j, best = None, 0.0
        for j in range(len(ents_y)):
            s = scores[j][i] if transpose else scores[i][j]
            if best_j is None or s > best:
                best_j, best = j, s
        rows.append({"owner": repr(ex), "best_match": repr(ents_y[best_j][1]) if best_j is not None else None,
                     "score": round(min(best, 1.0), 3)})
    return rows


def match_parsed(pa: ParsedName, pb: ParsedName, owners: str = "any") -> MatchResult:
    if owners not in OWNER_MODES:
        raise ValueError(f"owners must be one of {sorted(OWNER_MODES)}")
    if pa.placeholder or pb.placeholder:
        return MatchResult(0.0, "different", ["placeholder name"], pa.raw, pb.raw, owners)
    if pa.empty or pb.empty:
        return MatchResult(0.0, "different", ["no name to compare"], pa.raw, pb.raw, owners)
    ents_a, ents_b = _entities(pa), _entities(pb)
    detail = [[_pair_score(ka, ea, kb, eb) for kb, eb in ents_b] for ka, ea in ents_a]
    scores = [[min(d[0], 1.0) for d in row] for row in detail]
    rows_a = _owner_rows(ents_a, ents_b, scores)
    rows_b = _owner_rows(ents_b, ents_a, scores, transpose=True)
    # Only meaningful with several owners on a side: one owner against one is just the score itself.
    partial = len(rows_a) + len(rows_b) > 2 and any(r["score"] < ACCEPT for r in rows_a + rows_b)

    def result(i, j, score, extra=()):
        reasons = (list(detail[i][j][1]) or (["no part agrees"] if score == 0 else [])) if i is not None else []
        reasons += list(extra)
        left = repr(ents_a[i][1]) if i is not None else pa.raw
        right = repr(ents_b[j][1]) if j is not None else pb.raw
        score = round(score, 3)
        return MatchResult(score, band(score), reasons, left, right, owners, partial, rows_a, rows_b)

    if owners == "any":
        i, j = max(((i, j) for i in range(len(ents_a)) for j in range(len(ents_b))), key=lambda ij: scores[ij[0]][ij[1]])
        return result(i, j, scores[i][j])     # a zero keeps the pair's own reason (gender, company)

    if owners == "all_a":
        # The weakest owner of A, each taking its best counterpart in B.
        i = min(range(len(ents_a)), key=lambda i: max(scores[i]))
        j = max(range(len(ents_b)), key=lambda j: scores[i][j])
        return result(i, j, scores[i][j], [f"weakest of {len(ents_a)} owner(s) in A"] if len(ents_a) > 1 else [])

    # "all": pair owners one-to-one, strongest pairs first; an owner left over on either side scores 0.
    pairs = sorted(((scores[i][j], i, j) for i in range(len(ents_a)) for j in range(len(ents_b))), reverse=True)
    used_a, used_b, chosen = set(), set(), []
    for s, i, j in pairs:
        if i not in used_a and j not in used_b:
            used_a.add(i)
            used_b.add(j)
            chosen.append((s, i, j))
    left_a = [repr(e) for k, (_, e) in enumerate(ents_a) if k not in used_a]
    left_b = [repr(e) for k, (_, e) in enumerate(ents_b) if k not in used_b]
    if left_a or left_b:
        missing = [f"no counterpart in B for {x}" for x in left_a] + [f"no counterpart in A for {x}" for x in left_b]
        return result(None, None, 0.0, missing)
    s, i, j = min(chosen)
    return result(i, j, s, [f"weakest of {len(chosen)} owner pair(s)"] if len(chosen) > 1 else [])


def match(a: str, b: str, owners: str = "any") -> MatchResult:
    """How strongly `a` and `b` name the same person(s), in [0, 1].

    owners="any" (default): the best pair - any owner in a matching any owner in b is enough.
    owners="all_a": every owner in a must be found in b.
    owners="all": every owner on both sides must pair one-to-one with an owner on the other side.
    Whatever the mode, `partial` and the per-owner rows show which owners found no counterpart.
    """
    return match_parsed(parse(a), parse(b), owners)


def covers(a: str, b: str) -> MatchResult:
    """Every owner named in `a` is found in `b` (same as match(a, b, owners="all_a"))."""
    return match(a, b, owners="all_a")
