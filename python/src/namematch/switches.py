"""Switches for the live rules, all on in production.

Each switch turns one rule on or off, so its effect on a labelled set of name pairs can be measured
alone. Rules that a sealed evaluation set showed to add false accepts, or to bring no measurable
benefit, were deleted rather than left switched off. near_miss was added in v0.3.0; the Kannada /
English rules came in v0.5.0, from name pairs in Karnataka's property records, each kept only after a
sealed evaluation set confirmed it.
"""

ON = {
    "vowel_drop": True,          # 'kumr' ~ 'kumar'
    "short_floor": True,         # short names need near-identity: kamala != komal
    "word_conflict": True,       # leftover initial vs an unexplained word ('Pallavi Ramappa K' vs 'K B Ramappa')
    "firm_cap": True,            # 'M/s <person>' vs the person capped at 0.6
    "holder_for": True,          # '<agent> GPA holder for <owner>'
    "spelled_initials": True,    # 'EM' = M
    "relative_explains": True,   # extra word that is the other side's S/o name
    "relative_conflict": True,   # different fathers / relation kinds / initials vs father
    "near_miss": True,           # v0.3.0: one-letter slip in a short name -> review (<= 0.64), never accepted
    # v0.5.0: Kannada / English rules from name pairs in Karnataka's property records.
    "kannada_jna": True,        # ಜ್ಞ (and its misspelling ಜ್ಙ) is gn or jn in English; a word-initial jn is gn (jnana ~ gnana)
    "ow_vowel": True,           # 'ow' before a consonant is 'au': sowmya ~ saumya, gowri ~ gauri
    "y_vowel": True,            # 'y' between consonants is 'ai': shylaja ~ shailaja
    "script_split": True,       # 'Kಲಕ್ಷ್ಮಿ' -> 'K ಲಕ್ಷ್ಮಿ': a word that changes script is two words
    "cross_script": True,       # a Kannada word against an English one: final a is gender-neutral; vowels-only differences go to review
    "cross_readings": True,      # a Kannada word also read without the y of ಯಾ (ದ್ಯಾಸ್ ~ Das) and with m for its nasal (ಹಂಸ ~ Hamsa)
    "eaasthi_weights": True,    # how common a name part is, counted over the eAasthi export instead of the sample
    "mined_variants": True,     # rules.toml variants.mined_groups: rao ~ raav, naidu ~ naaydu, begum ~ begam, ...
}
