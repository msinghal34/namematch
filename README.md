# namematch

Rule-based matching of person names in Indian, and especially Karnataka, property and identity records.
It answers one question: do these two name strings name the same person?

It reads names the way a revenue officer does.
Titles (Sri, Smt) and relation clauses (S/o, W/o, bin) are set aside, an initial may stand for a word, common spelling variants are understood, Kannada script is read, and one string may list several owners.
Every result comes with a score, a band and the reasons behind it.

Kannada and English spellings of the same name are matched the way they are written in Karnataka's records: ಪ್ರವೀಣ ಕುಮಾರ್ against PRAVEEN KUMAR, ವೈ ಕೆ ಹರಿಹರ ರಾವ್ against Y K HARIHARA RAO, a word that switches script midway, and the usual Kannada renderings of English, Muslim and South Indian names.
Where the two scripts cannot tell names apart (the same consonants with different vowels, as in Kritika and Kartik), the pair is sent for a check instead of being accepted, and Kannada's silent final vowel never joins names of opposite genders (Muniyamma and Muniyappa stay apart).

The same rules ship as a **Java library** (Java 11 or newer, no dependencies) and a **Python library** (Python 3.11 or newer, no dependencies), and the two give identical results.

## Java

Maven:

```xml
<dependency>
  <groupId>io.github.msinghal34</groupId>
  <artifactId>namematch</artifactId>
  <version>0.5.0</version>
</dependency>
```

Gradle:

```groovy
implementation 'io.github.msinghal34:namematch:0.5.0'
```

Use:

```java
import io.github.msinghal34.namematch.MatchResult;
import io.github.msinghal34.namematch.NameMatch;

MatchResult r = NameMatch.match("Suresh Kumr Gowda", "SURESH KUMAR");
r.score();       // 0.764
r.band();        // Band.LIKELY_SAME
r.isAccepted();  // false: only Band.SAME (0.80 and above) is safe to accept automatically
r.reasons();     // [kumr~kumar 0.86, extra: gowda]
```

All methods are thread-safe, and results are immutable.

## Python

```sh
pip install "git+https://github.com/msinghal34/namematch#subdirectory=python"
```

```python
from namematch import match

r = match("Suresh Kumr Gowda", "SURESH KUMAR")
r.score    # 0.764
r.band     # "likely_same"
r.reasons  # ["kumr~kumar 0.86", "extra: gowda"]
```

## What a result holds

| Java | Python | Meaning |
| --- | --- | --- |
| `score()` | `score` | 0 to 1, rounded to 3 decimals |
| `band()` | `band` | `SAME` (0.80 and above), `LIKELY_SAME` (0.65), `REVIEW` (0.35) or `DIFFERENT` |
| `reasons()` | `reasons` | short phrases explaining the score; empty when the names match exactly |
| `left()`, `right()` | `left`, `right` | the pair of owners that decided the score, as the matcher read them |
| `isPartial()` | `partial` | a side names several owners and one of them has no counterpart on the other side |
| `ownersA()`, `ownersB()` | `owners_a`, `owners_b` | every owner on each side with its best counterpart and score |

Reasons read like this:

| Reason | Meaning |
| --- | --- |
| `kumr~kumar 0.86` | two words taken as the same, with their similarity |
| `K.=krishnappa` | an initial standing for a word on the other side |
| `extra: gowda` | a word only one side has (a surname or father's name), which costs a little |
| `differs: ramesh / suresh` | words that disagree, which cost a lot |
| `praveen?parvin one letter apart` | a one-letter slip in a short name; such a pair is capped at 0.64 and never accepted |
| `relatives differ` | the same name with different fathers (or husbands) |
| `gender conflict` | look-alike names of opposite genders (Mallappa / Mallamma) |

An owner as read is written like `savitha rao (rel anand rao) [f]`: titles removed, initials as capitals with a dot, the relation clause in brackets, and the gender when the record shows it.

## Several owners

`1.ANAND RAO 2.SAVITHA RAO W/o Anand Rao` names two people.
The owner mode decides how they combine:

| Mode | Java | Python | Rule |
| --- | --- | --- | --- |
| any (default) | `OwnerMode.ANY` | `"any"` | any owner on one side matching any owner on the other is enough |
| all_a | `OwnerMode.ALL_A`, or `NameMatch.covers(a, b)` | `"all_a"`, or `covers(a, b)` | every owner in A must be found in B |
| all | `OwnerMode.ALL` | `"all"` | every owner on both sides must pair one-to-one |

```java
MatchResult r = NameMatch.match("1.ANAND RAO 2.SAVITHA RAO W/o Anand Rao", "Sri Anand Rao");
r.score();                       // 1.0: Anand Rao is on both sides
r.isPartial();                   // true: Savitha Rao has no counterpart
r.ownersA().get(1).owner();      // "savitha rao (rel anand rao) [f]"
r.ownersA().get(1).score();      // 0.244
```

## Command line

```sh
java -jar namematch-0.5.0.jar "Ramesh S/o Krishna" "Ramesh S/o Gopal"
python -m namematch "Ramesh S/o Krishna" "Ramesh S/o Gopal"
```

```
score  0.500  (review)
pair   ramesh (rel krishna) [m]  ~  ramesh (rel gopal) [m]
  - relatives differ
```

## How the two libraries stay identical

The rules live once, in `python/src/namematch/rules.toml` and its three data tables (how common each name part is, in two versions, and which names are male or female), and the Java build packages those same files.
The scoring code exists in both languages, and the Python code is the reference.

- `conformance/cases.jsonl` holds about 3,250 invented name pairs, each in all three owner modes (9,741 results), with every field of the Python result; about 650 of them mix Kannada and English.
  The Java tests must reproduce all of them exactly, and the Python tests fail if the file is out of date with the rules.
- `tools/compare_private.py pairs.tsv` runs both libraries over your own name pairs, on your machine, and compares every field.
  The two matched on all 448,797 results from about 150,000 real record pairs, a third of them Kannada property records.

To change a rule: change the Python code or `rules.toml`, bump the version, run `python conformance/make_cases.py`, make the same change in Java until `mvn verify` passes, and run `tools/compare_private.py` on real pairs.

## Licence

MIT, copyright (c) 2026 Mayank Singhal and Chief Minister's Office, Government of Karnataka.
