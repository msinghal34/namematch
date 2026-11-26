package io.github.msinghal34.namematch;

/** The live rules, all on; mirrors switches.py in the Python library. */
final class Switches {
    private Switches() {
    }

    static final boolean VOWEL_DROP = true;          // 'kumr' ~ 'kumar'
    static final boolean SHORT_FLOOR = true;         // short names need near-identity: kamala != komal
    static final boolean WORD_CONFLICT = true;       // leftover initial vs an unexplained word ('Pallavi Ramappa K' vs 'K B Ramappa')
    static final boolean FIRM_CAP = true;            // 'M/s <person>' vs the person capped at 0.6
    static final boolean HOLDER_FOR = true;          // '<agent> GPA holder for <owner>'
    static final boolean SPELLED_INITIALS = true;    // 'EM' = M
    static final boolean RELATIVE_EXPLAINS = true;   // extra word that is the other side's S/o name
    static final boolean RELATIVE_CONFLICT = true;   // different fathers / relation kinds / initials vs father
    static final boolean NEAR_MISS = true;           // v0.3.0: one-letter slip in a short name -> review (<= 0.64), never accepted
    // v0.5.0: Kannada / English rules from name pairs in Karnataka's property records.
    static final boolean KANNADA_JNA = true;         // ಜ್ಞ (and ಜ್ಙ) is gn or jn in English; a word-initial jn is gn (jnana ~ gnana)
    static final boolean OW_VOWEL = true;            // 'ow' before a consonant is 'au': sowmya ~ saumya, gowri ~ gauri
    static final boolean Y_VOWEL = true;             // 'y' between consonants is 'ai': shylaja ~ shailaja
    static final boolean SCRIPT_SPLIT = true;        // 'Kಲಕ್ಷ್ಮಿ' -> 'K ಲಕ್ಷ್ಮಿ': a word that changes script is two words
    static final boolean CROSS_SCRIPT = true;        // a Kannada word against an English one: final a is gender-neutral; vowels-only differences go to review
    static final boolean CROSS_READINGS = true;      // a Kannada word also read without the y of ಯಾ (ದ್ಯಾಸ್ ~ Das) and with m for its nasal (ಹಂಸ ~ Hamsa)
    static final boolean EAASTHI_WEIGHTS = true;     // how common a name part is, counted over 5 million persons
    static final boolean MINED_VARIANTS = true;      // rules.toml variants.mined_groups: rao ~ raav, naidu ~ naaydu, begum ~ begam, ...
}
