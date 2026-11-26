"""Writes conformance/cases.jsonl: invented name pairs with the Python library's full results.

The Java library must reproduce every field of every case (java/src/test/.../ConformanceTest.java),
and the Python tests check that this file matches the current rules (python/tests/test_conformance.py).
Every name is invented: hand-written shapes plus pairs generated from common name parts with the
spelling slips, titles, initials, relation clauses, owner lists and noise the real records show.

    python conformance/make_cases.py          # rewrite the file after a rule change
"""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python" / "src"))

from namematch import match  # noqa: E402

OUT = Path(__file__).resolve().parent / "cases.jsonl"
MODES = ("any", "all_a", "all")
SEED = 2026
GENERATED = 2500
MIXED = 600

HAND = [
    ("R.SUNDARAM", "Sundaram R"),
    ("Sri. Ramesh Kumar", "RAMESH KUMAR"),
    ("RAMAKRISHNAPPA", "Rama Krishnappa"),
    ("Madhu Kiran Kumar", "Madhu Kirankumar"),
    ("D. BHAGYAGOWRI", "D Bhagya Gowri"),
    ("K.SURESH", "Suresh Krishnappa"),
    ("N H PADMAVATHI", "Nanjunda Hanumantha Padmavathi"),
    ("POORNIMA N S", "N S Purnima"),
    ("SHIVANANTHAIAH G", "G Shivanantayya"),
    ("LAXMI DEVI", "Lakshmi Devi"),
    ("SRINIVASAN M", "M Srinivas"),
    ("GOPALA S/O LATE MUNIYAPPA", "Gopala"),
    ("Shivanna bin Kariyappa", "SHIVANNA"),
    ("1.ANAND RAO 2.SAVITHA RAO", "Savitha Rao W/o Anand Rao | Anand Rao S/o Venkat Rao"),
    ("1.ANAND RAO 2.SAVITHA RAO W/o Anand Rao", "Sri Anand Rao"),
    ("SURESH KUMR SINGH", "Suresh Kumar Singh"),
    ("ಶ್ರೀ. ರಮೇಶ್ ಗೌಡ. ಬಿ.", "RAMESH GOWDA B"),
    ("ಸ್ವರೂಪ್ ಗೌಡ", "Swaroop Gowda"),
    ("ಎಂ. ಲಕ್ಷ್ಮೀ ದೇವಿ", "M Lakshmi Devi"),
    ("ಕೆ. ನಾಗರಾಜ ಕೋಂ ಶಿವಮ್ಮ", "K Nagaraja"),
    ("ಮಹಮ್ಮದ್ ಇಸ್ಮಾಯಿಲ್", "Mohammed Ismail"),
    ("ಜ಼ಾಕಿರ್ ಹುಸೇನ್", "Zakir Hussain"),
    ("ಶ್ರೀಮತಿ ಸುಮಿತ್ರಾ ಬಾಯಿ", "Smt Sumitra Bai"),
    ("ಡಿ. ಕೆ. ಶಿವಪ್ರಸಾದ್", "D K Shivaprasad"),
    ("ಪ್ರವೀಣ್", "Parvin"),
    ("Praveen Kumar", "Parvin Kumar"),
    ("Manish", "Munish"),
    ("Kamala", "Komal"),
    ("Mallappa", "Mallamma"),
    ("Kumar", "Kumari"),
    ("Jayanth", "Jayanthi"),
    ("Ramesh S/o Krishna", "Ramesh S/o Gopal"),
    ("Lakshmi W/o Ramesh", "Lakshmi D/o Ramesh"),
    ("RAMESH B", "RAMESH S/O KRISHNA"),
    ("PRABHAKARA K NARASIMHA", "PRABHAKARA K S/O K NARASIMHA"),
    ("ANAND RAO", "SAVITA RAO W/O ANAND RAO"),
    ("NAVEED AKHTAR RUKSANA BANU", "RUKSANA BANU W/O NAVEED AKHTAR"),
    ("Kavya Thimmappa K", "K B Thimmappa"),
    ("Raghunandan B K", "Raghunandan Venugopal Sharma"),
    ("M/s Sri Lakshmi Builders Pvt Ltd", "Sri Laxmi Bildars"),
    ("M/s Ramesh Kumar", "Ramesh Kumar"),
    ("ABC Developers (India) Pvt Ltd", "ABC Developers"),
    ("Prestige Estates Projects Ltd rep by its Director Suresh", "Prestige Estates Projects"),
    ("Suresh GPA holder for Ramesh Kumar", "Ramesh Kumar"),
    ("Ramesh Kumar rep by GPA holder Suresh", "Suresh"),
    ("Ramesh @ Ramu", "Ramu"),
    ("Mohammed Ismail alias Ismail Khan", "Ismail Khan"),
    ("MS RAMESH", "M S Ramesh"),
    ("AN RAMESH", "A N Ramesh"),
    ("EM ANITA", "M Anita"),
    ("Miss Kumari", "Kumari"),
    ("Khali", "Ramesh"),
    ("NA", "NA"),
    ("", "Ramesh"),
    ("", ""),
    ("R4MESH KUM4R", "Ramesh Kumar"),
    ("Ramesh 2 Suresh", "Suresh"),
    ("RАMESH", "RAMESH"),
    ("José Ramírez", "Jose Ramirez"),
    ("Ramesh Kumar", "Ramesh Kumar"),
    ("Ra​mesh", "Ramesh"),
    ("Smt. Savitha w/o Late Anand", "Savitha"),
    ("Sri Venkatesha s/olate Narayanappa", "Venkatesh"),
    ("Gopal S O Krishnappa", "Gopal"),
    ("Mary Joseph", "Meri Josef"),
    ("Syed Ahmed", "Sayed Ahamed"),
    ("Mohd. Iqbal", "Mohammed Iqbal"),
    ("Sheikh Abdul Rahman", "Shaik Abdul Rahaman"),
    ("Venkatesan", "Venkatesh"),
    ("Narayanan", "Narayana"),
    ("Muniyappan", "Muniyappa"),
    ("Rahman", "Rahma"),
    ("Sura Narayana", "Suranarayana"),
    ("Bhimaiaha", "Bheemayya"),
    ("Deepti", "Deepit"),
    ("Ramesh and Suresh", "Suresh"),
    ("Ramesh, Suresh & Mahesh", "Mahesh and Ramesh"),
    ("Ramesh mattu Suresh", "Suresh"),
    ("1) Ramesh 2) Suresh 3) Mahesh", "Ramesh | Suresh"),
    ("Ramesh Kumar and others", "Ramesh Kumar"),
    ("Ramesh Kumar Legal Heirs", "Ramesh Kumar"),
    ("Sri Rama Temple Trust", "Rama Temple"),
    ("BBMP", "Ramesh"),
    ("Karnataka Housing Board", "Housing Board"),
    ("Dr. Lt. Col. Ramesh", "Ramesh"),
    ("Ramesh S/o Krishna W/o", "Ramesh"),
    ("((Ramesh))", "Ramesh"),
    ("R", "Ramesh"),
    ("K S", "K S"),
    ("Kumar Kumar Kumar", "Kumar"),
    ("Smt Kiran", "Kiran S/o Gopal"),
    ("Mr Kiran", "Kiran W/o Gopal"),
    ("Thiru Selvi", "Selvi D/o Murugan"),
    ("Kiran Kumar S/o Gopal", "Kiran Kumar Gopal"),
    ("M/s Kiran Kumar", "Kiran Kumar Traders"),
    # v0.5.0: Kannada / English
    ("PRAVEEN KUMAR", "ಪ್ರವೀಣ ಕುಮಾರ್"), ("VINAY S", "ವಿನಯ ಎಸ್"), ("Kಲಕ್ಷ್ಮಿ", "Smt K.Lakshmi"), ("ಗೀತಾM.S", "Geetha M S"),
    ("SOWMYA R", "ಸೌಮ್ಯ ಆರ್"), ("SHYLAJA M", "ಶೈಲಜಾ ಎಂ"), ("GNANA PRAKASH", "ಜ್ಞಾನ ಪ್ರಕಾಶ್"), ("JNANESH", "ಜ್ಞಾನೇಶ್"),
    ("GNANESH", "ಜ್ಞಾನೇಶ್"), ("ಜ್ಙಾನೇಶ್", "ಜ್ಞಾನೇಶ್"), ("PRAJNA", "ಪ್ರಜ್ಞಾ"), ("PRAGNA", "ಪ್ರಜ್ಞಾ"), ("JNANA MURTHY", "GNANA MURTHY"),
    ("RAJNI", "RAJINI"), ("RAJNI", "ರಜನಿ"), ("RAJNI", "RAGINI"), ("SAJNI", "SAJANI"), ("PRAJNA", "PRAGNA"),
    ("T N GIRIDHAR RAO", "ಟಿ ಎನ್ ಗಿರಿಧರ ರಾವ್"), ("ROBERT D LOBO", "ರಾಬರ್ಟ್ ಡಿ ಲೋಬೊ"), ("NIRMAL DAS", "ನಿರ್ಮಲ್ ದ್ಯಾಸ್"),
    ("HAMSA VENI", "ಹಂಸ ವೇಣಿ"), ("IMTIAZ AHMED", "ಇಂತಿಯಾಜ್ ಅಹ್ಮದ್"), ("SHYAM SUNDAR", "ಶ್ಯಾಮ್ ಸುಂದರ್"),
    ("KARTIK", "ಕೃತಿಕಾ"), ("PRITAM", "ಪ್ರತಿಮಾ"), ("PRAMILA", "ಪರಿಮಳ"), ("KAMAL", "ಕೋಮಲ್"), ("MALLAPPA", "ಮಲ್ಲಮ್ಮ"),
    ("LAKSHMI", "ಲಕ್ಷ್ಮಯ್ಯ"), ("NARASIMHA", "ನರಸಮ್ಮ"), ("MUNIYAPPA", "ಮುನಿಯಮ್ಮ"), ("ADITI", "ಆದಿತ್ಯ"), ("SALIM", "ಸಲ್ಮ"),
    ("PRABHU", "ಪ್ರಭ"), ("RATAN", "ರತ್ನ"), ("HANUMAN", "ಹನುಮಕ್ಕ"), ("SHIVALINGAMMA", "ಶಿವಲಿಂಗಮ್"), ("ADITYA", "ಆದಿತ್ಯ"),
    ("KAVYA", "ಕಾವ್ಯ"), ("CHAITANYA", "ಚೈತನ್ಯ"), ("SUSHEELA M", "ಎಂ.ಸುಶೀಲ"), ("ARUNA", "ಅರುಣ.ಎಲ್"), ("Praveen", "Praveena"),
    ("NAIDU", "ನಾಯ್ಡು"), ("BEGUM", "ಬೇಗಂ"), ("THOMAS EDISON", "ಥಾಮಸ್ ಎಡಿಸನ್"), ("\x02RAMESH KUMAR", "Ramesh Kumar"),
    ("RA\x02MESH", "Ramesh"), ("SANJAY K", "ಸಂಜಯ್ ಕೆ"), ("GANGAMMA", "ಗಂಗಮ್ಮ"), ("BASAVVA", "ಬಸವ್ವ"),
]

GIVEN_M = ["ramesh", "suresh", "mahesh", "ganesh", "praveen", "manish", "anand", "venkatesh", "narayana",
           "krishna", "gopal", "nagaraj", "shivakumar", "manjunath", "basavaraj", "mallappa", "hanumantha",
           "srinivas", "raghavendra", "prakash", "mohammed", "syed", "abdul", "ismail", "iqbal", "joseph",
           "thomas", "kiran", "madhu", "jayanth", "vijay", "shankar", "subramanya", "chandrashekar",
           "lokesh", "dinesh", "naveen", "harish", "girish", "satish", "rajesh", "mukund", "puttaswamy",
           "muniyappa", "kariyappa", "thimmaiah", "lingaraju", "devaraj", "umesh", "yogesh", "vasanth"]
GIVEN_F = ["lakshmi", "savitha", "sumitra", "padmavathi", "poornima", "kamala", "sharada", "anitha",
           "pallavi", "deepa", "rekha", "shobha", "geetha", "yashoda", "sandhya", "fathima", "mary",
           "mallamma", "shivamma", "jayanthi", "kumari", "sunitha", "kavitha", "nagaveni", "bhagya",
           "roopa", "asha", "usha", "vani", "manjula", "kousar", "parvin", "renuka", "gowramma", "sowmya"]
SURNAMES = ["kumar", "reddy", "gowda", "rao", "shetty", "naidu", "sharma", "murthy", "swamy", "prasad",
            "babu", "iyer", "iyengar", "khan", "hussain", "ahmed", "singh", "jain", "patil", "hegde",
            "naik", "bhat", "kamath", "pai", "achar", "urs", "nayak", "devi", "bai", "begum"]
FIRMS = ["builders", "developers", "estates", "constructions", "enterprises", "traders", "properties"]
FIRM_NAMES = ["sri lakshmi", "prestige", "brigade", "sobha", "mantri", "shree balaji", "sai krishna", "abc"]
HONORIFICS_M = ["sri", "shri", "mr", "sri.", "dr", "late"]
HONORIFICS_F = ["smt", "smt.", "mrs", "kum", "srimati", "miss"]
RELATIONS_M = ["s/o", "S/O", "son of", "S/o.", "bin", "s o", "s\\o"]
RELATIONS_F = ["w/o", "d/o", "W/O", "wife of", "daughter of", "kom", "D/o."]
VOWELS = "aeiou"
CYRILLIC = {"a": "а", "e": "е", "o": "о", "p": "р", "c": "с", "x": "х", "A": "А", "E": "Е", "O": "О", "K": "К", "M": "М"}


def slip(rng: random.Random, word: str) -> str:
    """One spelling slip of the kinds the records show."""
    if len(word) < 3:
        return word
    kind = rng.randrange(11)
    i = rng.randrange(1, len(word) - 1)
    if kind == 0 and word[i] in VOWELS:                              # dropped vowel
        return word[:i] + word[i + 1:]
    if kind == 1 and word[i] in VOWELS:                              # changed vowel
        return word[:i] + rng.choice(VOWELS.replace(word[i], "")) + word[i + 1:]
    if kind == 2:                                                    # adjacent swap
        return word[:i] + word[i + 1] + word[i] + word[i + 2:]
    if kind == 3:                                                    # doubled letter
        return word[:i] + word[i] + word[i:]
    if kind == 4:                                                    # aspirate
        return word.replace("t", "th", 1) if "th" not in word else word.replace("th", "t", 1)
    if kind == 5:
        return word.replace("ee", "i", 1) if "ee" in word else word.replace("i", "ee", 1)
    if kind == 6:
        return word.replace("oo", "u", 1) if "oo" in word else word.replace("u", "oo", 1)
    if kind == 7:
        return word.replace("v", "w", 1) if "v" in word else word.replace("w", "v", 1)
    if kind == 8 and word.endswith(("aiah", "ayya", "iah")):
        return word[: word.rfind("a" if word.endswith("ayya") else "i")] + rng.choice(["aiah", "ayya", "aiya"])
    if kind == 9:                                                    # final a
        return word[:-1] if word.endswith("a") else word + "a"
    return word[:i] + rng.choice("bcdfghjklmnprstvy") + word[i + 1:]  # any other letter


def person(rng: random.Random, female=None):
    female = rng.random() < 0.4 if female is None else female
    given = rng.choice(GIVEN_F if female else GIVEN_M)
    words = [given]
    if rng.random() < 0.3:
        words.append(rng.choice(GIVEN_M))
    if rng.random() < 0.6:
        words.append(rng.choice(SURNAMES))
    initials = [rng.choice("abcdefghjklmnprsty").upper() for _ in range(rng.choice([0, 0, 1, 1, 2]))]
    father = [rng.choice(GIVEN_M)] + ([rng.choice(SURNAMES)] if rng.random() < 0.3 else [])
    return {"female": female, "words": words, "initials": initials, "father": father}


def render(rng: random.Random, p, perturb: float) -> str:
    words = [slip(rng, w) if rng.random() < perturb else w for w in p["words"]]
    if rng.random() < 0.1 and len(words) > 1:
        words = ["".join(words[:2])] + words[2:]                   # joined words
    inits = list(p["initials"])
    if inits and rng.random() < 0.2:                               # an initial spelled out, or dropped
        inits = inits[1:]
    parts = list(words)
    style = rng.randrange(4)
    if style == 0:
        parts = [f"{i}." for i in inits] + parts
    elif style == 1:
        parts = parts + inits
    elif style == 2:
        parts = ["".join(inits)] + parts if inits else parts
    else:
        parts = [" ".join(inits)] + parts if inits else parts
    text = " ".join(x for x in parts if x)
    if rng.random() < 0.3:
        text = rng.choice(HONORIFICS_F if p["female"] else HONORIFICS_M) + " " + text
    if rng.random() < 0.3:
        rel = rng.choice(RELATIONS_F if p["female"] else RELATIONS_M)
        text += f" {rel} {' '.join(p['father'])}"
    if rng.random() < 0.05:
        text += f" @ {words[0]}"
    case = rng.randrange(3)
    text = text.upper() if case == 0 else text.title() if case == 1 else text
    return text


def noise(rng: random.Random, text: str) -> str:
    kind = rng.randrange(6)
    if kind == 0:
        return "".join(CYRILLIC.get(c, c) if rng.random() < 0.2 else c for c in text)
    if kind == 1:
        return text.replace("o", "0", 1).replace("e", "3", 1)
    if kind == 2:
        return text.replace(" ", " ", 1)
    if kind == 3:
        return text.replace("a", "á", 1)
    if kind == 4:
        return f"{text}."
    return f"  {text} ,"


def owners(rng: random.Random, people, perturb: float) -> str:
    texts = [render(rng, p, perturb) for p in people]
    if len(texts) == 1:
        return texts[0]
    joiner = rng.choice([" and ", " & ", ", ", " | ", "; ", " mattu "])
    if rng.random() < 0.3:
        return " ".join(f"{k + 1}.{t}" for k, t in enumerate(texts))
    return joiner.join(texts)


def generated(rng: random.Random):
    out = []
    for _ in range(GENERATED):
        roll = rng.random()
        if roll < 0.08:
            firm = f"{rng.choice(FIRM_NAMES)} {rng.choice(FIRMS)}"
            a = f"M/s {firm} Pvt Ltd" if rng.random() < 0.5 else firm.title()
            b = slip(rng, firm) if rng.random() < 0.5 else f"{rng.choice(FIRM_NAMES)} {rng.choice(FIRMS)}"
            if rng.random() < 0.3:
                b += f" rep by {render(rng, person(rng), 0)}"
            out.append((a, b))
            continue
        if roll < 0.11:
            out.append((rng.choice(["khali", "NA", "vacant", "owner", "-", "", "1."]), render(rng, person(rng), 0)))
            continue
        people_a = [person(rng) for _ in range(rng.choice([1, 1, 1, 2, 3]))]
        kind = rng.random()
        if kind < 0.55:                                            # the same owners, written another way
            people_b = rng.sample(people_a, rng.randint(1, len(people_a)))
        elif kind < 0.75:                                          # a namesake or relative
            p = dict(people_a[0])
            p["father"] = [rng.choice(GIVEN_M)]
            if rng.random() < 0.5:
                p["words"] = [rng.choice(GIVEN_F if p["female"] else GIVEN_M)] + p["words"][1:]
            people_b = [p]
        else:                                                      # someone else
            people_b = [person(rng) for _ in range(rng.choice([1, 1, 2]))]
        a = owners(rng, people_a, 0.15)
        b = owners(rng, people_b, 0.35)
        if rng.random() < 0.08:
            a = noise(rng, a)
        if rng.random() < 0.08:
            b = noise(rng, b)
        if rng.random() < 0.05:
            a = f"{render(rng, person(rng), 0)} GPA holder for {a}"
        out.append((a, b))
    return out


# Common name words in Kannada with their usual English spelling, for mixed-script pairs.
KANNADA = [("ರಮೇಶ್", "ramesh"), ("ಸುರೇಶ್", "suresh"), ("ಮಹೇಶ್", "mahesh"), ("ಗಣೇಶ್", "ganesh"), ("ಪ್ರವೀಣ್", "praveen"),
           ("ಆನಂದ್", "anand"), ("ವೆಂಕಟೇಶ್", "venkatesh"), ("ನಾರಾಯಣ", "narayana"), ("ಕೃಷ್ಣ", "krishna"), ("ಗೋಪಾಲ್", "gopal"),
           ("ನಾಗರಾಜ್", "nagaraj"), ("ಮಂಜುನಾಥ್", "manjunath"), ("ಬಸವರಾಜ್", "basavaraj"), ("ಮಲ್ಲಪ್ಪ", "mallappa"),
           ("ಶ್ರೀನಿವಾಸ್", "srinivas"), ("ಪ್ರಕಾಶ್", "prakash"), ("ವಿನಯ", "vinay"), ("ಅರುಣ", "arun"), ("ಕಿರಣ್", "kiran"),
           ("ಲಕ್ಷ್ಮಿ", "lakshmi"), ("ಸವಿತಾ", "savitha"), ("ಪದ್ಮಾವತಿ", "padmavathi"), ("ಪೂರ್ಣಿಮಾ", "poornima"), ("ಕಮಲ", "kamala"),
           ("ಶಾರದಾ", "sharada"), ("ಅನಿತಾ", "anitha"), ("ಗೀತಾ", "geetha"), ("ರೇಖಾ", "rekha"), ("ಸೌಮ್ಯ", "sowmya"),
           ("ಮಲ್ಲಮ್ಮ", "mallamma"), ("ಶಿವಮ್ಮ", "shivamma"), ("ಕುಮಾರ್", "kumar"), ("ರೆಡ್ಡಿ", "reddy"), ("ಗೌಡ", "gowda"),
           ("ರಾವ್", "rao"), ("ಶೆಟ್ಟಿ", "shetty"), ("ನಾಯ್ಡು", "naidu"), ("ಶರ್ಮ", "sharma"), ("ಬೇಗಂ", "begum"), ("ಖಾನ್", "khan"),
           ("ದ್ಯಾಸ್", "das"), ("ಹಂಸ", "hamsa"), ("ಜ್ಞಾನೇಶ್", "jnanesh"), ("ಪ್ರಜ್ಞಾ", "prajna"), ("ಶೈಲಜಾ", "shylaja")]
KN_INITIALS = {"ಎಂ": "M", "ಎಸ್": "S", "ಕೆ": "K", "ಬಿ": "B", "ಆರ್": "R", "ಎನ್": "N", "ಟಿ": "T", "ಜಿ": "G"}


def mixed(rng: random.Random):
    """Mixed-script pairs: a name of 1 to 3 Kannada words against an English rendering of it (with
    slips, other words or initials), or against a different name."""
    out = []
    for _ in range(MIXED):
        words = rng.sample(KANNADA, rng.choice([1, 2, 2, 3]))
        inits = rng.sample(sorted(KN_INITIALS), rng.choice([0, 0, 1, 2]))
        kan = " ".join(inits + [k for k, _ in words])
        if rng.random() < 0.7:
            latin = [slip(rng, e) if rng.random() < 0.3 else e for _, e in words]
        else:
            latin = [e for _, e in rng.sample(KANNADA, len(words))]
        eng = " ".join([KN_INITIALS[i] for i in inits if rng.random() < 0.8] + latin)
        eng = eng.upper() if rng.random() < 0.5 else eng.title()
        out.append((kan, eng) if rng.random() < 0.5 else (eng, kan))
    return out


def result(a: str, b: str, mode: str) -> dict:
    r = match(a, b, mode)
    return {"score": r.score, "band": r.band, "reasons": r.reasons, "left": r.left, "right": r.right,
            "owners": r.owners, "partial": r.partial, "owners_a": r.owners_a, "owners_b": r.owners_b}


def cases() -> list[str]:
    rng = random.Random(SEED)
    lines = []
    for a, b in HAND + generated(rng) + mixed(rng):
        for mode in MODES:
            lines.append(json.dumps({"a": a, "b": b, "owners": mode, "expected": result(a, b, mode)}, ensure_ascii=False))
    return lines


if __name__ == "__main__":
    lines = cases()
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(lines)} cases written to {OUT}")
