"""Behaviour of the matcher on the name shapes seen in Karnataka property records.

Names here are invented; each case mirrors a pattern found in the real sample.
"""

import pytest

from namematch import covers, match, parse

SAME = 0.80          # "same" band floor
REVIEW = 0.35


@pytest.mark.parametrize("a, b", [
    ("R.SUNDARAM", "Sundaram R"),                                   # order, punctuation
    ("Sri. Ramesh Kumar", "RAMESH KUMAR"),                          # honorific
    ("RAMAKRISHNAPPA", "Rama Krishnappa"),                          # joined words
    ("Madhu Kiran Kumar", "Madhu Kirankumar"),
    ("D. BHAGYAGOWRI", "D Bhagya Gowri"),
    ("K.SURESH", "Suresh Krishnappa"),                              # initial spelled out
    ("N H PADMAVATHI", "Nanjunda Hanumantha Padmavathi"),
    ("POORNIMA N S", "N S Purnima"),                                # transliteration variants
    ("SHIVANANTHAIAH G", "G Shivanantayya"),
    ("LAXMI DEVI", "Lakshmi Devi"),
    ("SRINIVASAN M", "M Srinivas"),
    ("GOPALA S/O LATE MUNIYAPPA", "Gopala"),                         # relation clause
    ("Shivanna bin Kariyappa", "SHIVANNA"),
    ("1.ANAND RAO 2.SAVITHA RAO", "Savitha Rao W/o Anand Rao | Anand Rao S/o Venkat Rao"),  # several owners
    ("SURESH KUMR SINGH", "Suresh Kumar Singh"),                    # dropped vowel
    ("ಶ್ರೀ. ರಮೇಶ್ ಗೌಡ. ಬಿ.", "RAMESH GOWDA B"),                      # Kannada script + letter-name initial
    ("ಎಂ. ಗಿರೀಶ್", "M GIREESH"),
    ("Mohd Rafiq", "Mohammed Rafiq"),                               # variant table
    ("M/s Sunrise Developers Pvt Ltd", "SUNRISE DEVELOPERS (INDIA) PRIVATE LIMITED"),
    ("HOLDER (BORAMMA)", "Smt. Boramma"),
    ("Ravi Shankar @ Ravi", "RAVI SHANKAR"),
    ("STEFAN MERI", "Stephan Mery"),                                # variant on one side only
    ("HAREESH MANE", "Harish Manae"),                               # vowel inserted in a short name
])
def test_same_person(a, b):
    r = match(a, b)
    assert r.score >= SAME, r
    assert match(b, a).score == pytest.approx(r.score, abs=0.05)   # roughly symmetric


@pytest.mark.parametrize("a, b", [
    ("MALLAPPA", "Mallamma"),                                       # gender suffix
    ("ANIL KUMAR", "Anil Kumari"),
    ("PRABHA GOEL", "Rakesh Goel"),                                 # shared surname only
    ("RAVI KUMAR", "Suresh Kumar"),                                 # shared common word only
    ("KHALI", "Suresh Kumar"),                                      # placeholder
    ("M/s Sunrise Developers Pvt Ltd", "Suresh Kumar"),             # organisation vs person
    ("Smt. Kavitha GPA holder for Sri Mohan Das", "Kavitha"),       # GPA holder is not the owner
])
def test_different_person(a, b):
    assert match(a, b).score < REVIEW, match(a, b)


@pytest.mark.parametrize("a, b", [
    ("Kalyan", "Kalyan Gopinathan"),                                # thin evidence
    ("J S Lingaraja", "Lingaraja T S"),                               # initials disagree
    ("Srivatsa B K", "Srivatsa Seshadri Sharma"),
])
def test_needs_review(a, b):
    r = match(a, b)
    assert REVIEW <= r.score < SAME, r


@pytest.mark.parametrize("a, b", [
    # Independent review C1: masculine / feminine forms of one name are different people.
    ("Salma Khan", "Salman Khan"),
    ("Lakshman Rao", "Lakshmi Rao"),
    ("Madhav", "Madhavi Rao"),
    ("Jayanth K", "Jayanthi K"),
    ("Shankar Gowda", "Shankaramma Gowda"),
    ("Shyam Sundar", "Shyama Sundari"),
    # Review C2: relatives recorded on both sides must agree.
    ("Ramesh S/o Krishna", "Ramesh S/o Gopal"),
    ("Lakshmi W/o Ramesh", "Lakshmi W/o Suresh"),
    ("Lakshmi W/o Ramesh", "Lakshmi D/o Ramesh"),
    ("RAMESH B", "RAMESH S/O KRISHNA"),
    ("KAMALA", "Komal"),        # a changed vowel in a short name: never auto-accepted (short_floor retired)
    ("Ramesh", "Rajesh"),       # one consonant: short_strict retired, so only kept out of auto-accept
    ("Amarnath K Mehta", "Kavitha Mehta"),
    ("Pallavi Ramappa K", "K B Ramappa"),   # daughter vs father: review at most
])
def test_never_auto_accepted(a, b):
    assert match(a, b).score < SAME, match(a, b)


@pytest.mark.parametrize("a, b", [
    ("B A MRUTHYUNJAYASWAMY", "B A Mruthyunjaya Swamy S/o Late Siddalingappa"),   # joined word with a dropped vowel
    ("SENDHIL VELAN N", "Sri. Senthil Velan.N."),                         # nd / nt
    ("K M IBRAHEEM MATTU M K RAJIYA", "K M IBRAHIM AND M K RAZIYA"),    # Kannada 'mattu' = and
    ("PRABHAKARA.K NARASIMHA", "PRABHAKARA.K. S.O. K. NARASIMHA"),        # father's name appended
    ("GIRIJA SIDDAPPA", "Sri SIDDAPPA G is POA of Smt GIRIJA SIDDAPPA"),   # "is POA of"
])
def test_v02_patterns(a, b):
    assert match(a, b).score >= SAME, match(a, b)


@pytest.mark.parametrize("a, b", [
    ("RAMESHA", "Ramesh"),                  # Kannada adds -a to male names: not a gender change
    ("PRADEEPA R", "Pradeep R"),
    ("SRINIVASAN M", "M Srinivas"),
    ("MUNIYAPPAN", "Muniyappa"),
    ("RAMESH K", "RAMESH S/O KRISHNA"),     # initial fits the father
    ("ಶ್ರೀಮತಿ ಲಕ್ಷ್ಮಿ", "Lakshmi"),            # Kannada title
])
def test_review_fixes_keep_true_matches(a, b):
    assert match(a, b).score >= SAME, match(a, b)


def test_reasons_explain_the_decision():
    r = match("K.SURESH", "Suresh Krishnappa")
    assert any("K.=krishnappa" in x for x in r.reasons)
    assert any("gender" in x for x in match("MALLAPPA", "Mallamma").reasons) or match("MALLAPPA", "Mallamma").score == 0


def test_covers_requires_every_owner():
    deed = "Savitha Rao W/o Anand Rao | Anand Rao S/o Venkat Rao"
    assert covers("ANAND RAO & SAVITHA RAO", deed).score >= SAME
    assert covers("ANAND RAO & PRIYA NAIR", deed).score < REVIEW


def test_parse_structure():
    p = parse("1.G.PRAVEEN KUMAR,2.M.SUDHA Rep by GPA Holder Sri. N.S. Ramani S/o Late Ramaiah")
    assert [x.full for x in p.persons] == [["praveen", "kumar"], ["sudha"]]
    assert [x.full for x in p.representatives] == [["ramani"]]
    p = parse("Smt.ವತ್ಸಲಾ.ಆರ್ ಕೋಂ ರಾಮಣ್ಣ")
    assert p.persons[0].full == ["vathsalaa"] and p.persons[0].initials == ["r"]
    assert p.persons[0].gender == "f" and p.persons[0].relative
    assert parse("KHALI").placeholder


DEED = "Savitha Rao W/o Anand Rao | Anand Rao S/o Venkat Rao"


@pytest.mark.parametrize("b, any_, all_a, all_", [
    ("Anand Rao", "same", "different", "different"),            # one of two owners present
    (DEED, "same", "same", "same"),                              # both owners present
    ("Anand Rao | Priya Nair", "same", "different", "different"),  # one right, one wrong
    ("Anand Rao | Savitha Rao | Priya Nair", "same", "same", "different"),  # an extra owner in B
])
def test_owner_modes(b, any_, all_a, all_):
    a = "1.ANAND RAO 2.SAVITHA RAO"
    assert match(a, b).band == any_
    assert match(a, b, owners="all_a").band == all_a
    assert match(a, b, owners="all").band == all_


def test_partial_flag_and_owner_rows():
    r = match("1.ANAND RAO 2.SAVITHA RAO", "Anand Rao")
    assert r.score >= SAME and r.partial
    assert [row["score"] >= SAME for row in r.owners_a] == [True, False]
    assert not match("1.ANAND RAO 2.SAVITHA RAO", DEED).partial
    assert not match("Praveen Kumar", "Parvin Kumar").partial      # one owner each: nothing is partial
    with pytest.raises(ValueError):
        match("a", "b", owners="some")


def test_relative_does_not_turn_husband_into_wife():
    # Review follow-up: the relative may explain an extra word only when its carrier was matched by name.
    assert match("ANAND RAO", "Smt. Savita Rao W/o Anand Rao").score < REVIEW
    assert match("ASIF KHAN NAZIA BEGUM", "Nazia Begum W/o Asif Khan").score >= SAME


def test_vowel_slip_goes_to_review_never_accepted():
    # vowel_slip (v0.3.0 near_miss, generalised in v0.6.0): names whose vowels differ go to an officer.
    for a, b in [("Praveen", "Parvin"), ("Manish", "Munish"), ("MANISH KUMAR", "Munish Kumar"), ("Ramesh", "Rumesh")]:
        r = match(a, b)
        assert r.band == "review" and r.score <= 0.64, (a, b, r)
        assert "vowels differ: needs a check" in r.reasons
    # Opposite genders stay different, and a real match is untouched.
    assert match("Mallappa", "Mallamma").band == "different"
    assert match("Salman", "Salma").band == "different"
    assert match("Praveen", "Pravin").band == "same"


# v0.5.0: Kannada / English (names invented; each case mirrors a pattern in the eAasthi export).
@pytest.mark.parametrize("a, b", [
    ("PRAVEEN KUMAR", "ಪ್ರವೀಣ ಕುಮಾರ್"),            # Kannada's final short a is not a feminine ending
    ("VINAY S", "ವಿನಯ ಎಸ್"),
    ("Kಲಕ್ಷ್ಮಿ", "Smt K.Lakshmi"),                   # a word that changes script is two words
    ("SOWMYA R", "ಸೌಮ್ಯ ಆರ್"),                      # ow ~ au
    ("SHYLAJA M", "ಶೈಲಜಾ ಎಂ"),                      # y between consonants ~ ai
    ("GNANA PRAKASH", "ಜ್ಞಾನ ಪ್ರಕಾಶ್"),             # ಜ್ಞ ~ gn
    ("Y K HARIHARA RAO", "ವೈ ಕೆ ಹರಿಹರ ರಾವ್"),      # rao ~ raav
    ("NIRMAL DAS", "ನಿರ್ಮಲ್ ದ್ಯಾಸ್"),               # v0.5.0 (second decision): the English a written as ಯಾ
    ("HAMSA VENI", "ಹಂಸ ವೇಣಿ"),                     # v0.5.0 (second decision): the nasal sign written m in English
])
def test_kannada_english_spellings_accepted(a, b):
    assert match(a, b).score >= SAME, match(a, b)


@pytest.mark.parametrize("a, b", [
    ("MALLAPPA", "ಮಲ್ಲಮ್ಮ"),                         # opposite genders stay apart across scripts
    ("Praveen", "Praveena"),                         # in one script the final a still marks a woman
    ("KAMAL", "ಕೋಮಲ್"),                              # a short name's vowels still matter
])
def test_cross_script_keeps_its_guards(a, b):
    assert match(a, b).score < SAME, match(a, b)


@pytest.mark.parametrize("a, b", [
    ("ROBERT D LOBO", "ರಾಬರ್ಟ್ ಡಿ ಲೋಬೊ"),            # vowels differ only: likely the same, but an officer checks
    ("KARTIK", "ಕೃತಿಕಾ"),                             # the same consonants, a different name (Kritika)
    ("PRITAM", "ಪ್ರತಿಮಾ"),                            # Pratima
    ("PRAMILA", "ಪರಿಮಳ"),                             # Parimala
])
def test_vowels_only_across_scripts_goes_to_review_never_accepted(a, b):
    r = match(a, b)
    assert REVIEW <= r.score < 0.65, r


@pytest.mark.parametrize("a, b", [
    ("JNANESH", "ಜ್ಞಾನೇಶ್"),                           # jn ~ gn, both ways
    ("GNANESH", "ಜ್ಞಾನೇಶ್"),
    ("ಜ್ಙಾನೇಶ್", "ಜ್ಞಾನೇಶ್"),                          # ಜ್ಙ: a common misspelling of ಜ್ಞ
    ("PRAJNA", "ಪ್ರಜ್ಞಾ"),                            # ಜ್ಞ inside a word: gn or jn in English
    ("PRAGNA", "ಪ್ರಜ್ಞಾ"),
    ("JNANA MURTHY", "GNANA MURTHY"),
])
def test_jn_and_gn_are_one_sound(a, b):
    assert match(a, b).score >= SAME, match(a, b)


def test_marker_characters_in_input_mean_nothing():
    assert match("\x02RAMESH KUMAR", "Ramesh Kumar").score == match("RAMESH KUMAR", "Ramesh Kumar").score


@pytest.mark.parametrize("a, b", [
    ("RAJNI", "RAJINI"), ("RAJNI", "RAJANI"), ("SAJNI", "SAJANI"), ("RAJNI", "ರಜನಿ"),   # jn inside a word is j + n
])
def test_jn_inside_a_word_is_j_and_n(a, b):
    assert match(a, b).score >= 0.80, match(a, b)


def test_jn_rule_does_not_join_different_names():
    assert match("RAJNI", "RAGINI").score < 0.80


@pytest.mark.parametrize("a, b", [
    ("ಲಕ್ಷ್ಮಯ್ಯ", "LAKSHMI"), ("ನರಸಮ್ಮ", "NARASIMHA"), ("ಮುನಿಯಮ್ಮ", "MUNIYAPPA"),       # gender endings across scripts
    ("ಆದಿತ್ಯ", "ADITI"), ("ಸಲ್ಮ", "SALIM"), ("ಪ್ರಭ", "PRABHU"), ("ರತ್ನ", "RATAN"), ("ಹನುಮಕ್ಕ", "HANUMAN"),
    ("ಶಿವಲಿಂಗಮ್", "SHIVALINGAMMA"),                                                     # through another reading
])
def test_kannada_gender_endings_keep_their_gender(a, b):
    # Kannada's silent final a never joins names of opposite genders by a loose match.
    assert match(a, b).score < 0.35, match(a, b)


@pytest.mark.parametrize("a, b", [
    ("ADITYA", "ಆದಿತ್ಯ"), ("SOWMYA", "ಸೌಮ್ಯ"), ("KAVYA", "ಕಾವ್ಯ"), ("CHAITANYA", "ಚೈತನ್ಯ"),
])
def test_names_ending_in_ya_still_match_across_scripts(a, b):
    assert match(a, b).score >= SAME, match(a, b)


@pytest.mark.parametrize("a, b", [
    ("ಶ್ರೀಮತಿ ಪ್ರವೀಣ", "PRAVEEN"),                     # the record says she is a woman: not Praveen
    ("ಪ್ರವೀಣ W/o ರಮೇಶ್", "PRAVEEN"),
    ("MUNIYAKKA", "MUNIYAPPA"), ("HANUMAVVA", "HANUMAPPA"), ("ಮುನಿಯಕ್ಕ", "MUNIYAPPA"),   # -akka / -avva are female
])
def test_recorded_and_ending_genders_keep_names_apart(a, b):
    assert match(a, b).score < SAME, match(a, b)


@pytest.mark.parametrize("a, b", [
    ("ಶ್ರೀಮತಿ ಪ್ರವೀಣ", "PRAVEENA"), ("ಪ್ರವೀಣ S/o ರಮೇಶ್", "PRAVEEN"), ("BASAVVA", "ಬಸವ್ವ"), ("HANUMAKKA", "ಹನುಮಕ್ಕ"),
])
def test_matching_genders_still_match(a, b):
    assert match(a, b).score >= SAME, match(a, b)


# v0.6.0 (names invented).
def test_comma_between_initials_is_one_name():
    assert match("MEERA,K,BHAT", "Meera K Bhat").score >= SAME
    assert match("T,R,DINESH", "T R Dinesh").score >= SAME
    # A comma between full names still separates owners.
    assert match("RAMESH, SURESH", "Ramesh").partial


def test_initial_explained_by_own_word_is_not_the_father():
    assert match("GANAPATI SHENOY S/O RAMAPPA SHENOY", "S.Ganapati").score >= SAME


def test_her_name_before_his_is_a_relative():
    for a, b in [("REKHA MAHESH KULKARNI", "Mahesh Kulkarni"), ("PRIYA ARVIND", "ARVIND P"),
                 ("Kavya Joseph Mathew", "JOSEPH MATHEW")]:
        r = match(a, b)
        assert REVIEW <= r.score < SAME, (a, b, r)
    # His own extra name is not affected.
    assert match("KISHORE RAO", "Kishore").score >= REVIEW


def test_differing_initials_sit_mid_review():
    r = match("Girish S", "Girish T")
    assert REVIEW <= r.score <= 0.6, r


def test_review_fixes_for_v060():
    # The given name itself does not explain an initial that the father should: R is not Ramesh.
    assert match("R RAMESH", "RAMESH S/O GOPAL").score < SAME
    # An initial standing where her name would stand is his own first name: one man, not a relative.
    assert match("LAKSHMI NARAYANA", "L NARAYANA").score >= SAME
    assert match("UMA SHANKAR", "U Shankar").score >= SAME
    # A comma never joins initials across a relation clause.
    assert match("LAKSHMI W/O RAMESH,K,SURESH", "Suresh").score >= SAME
