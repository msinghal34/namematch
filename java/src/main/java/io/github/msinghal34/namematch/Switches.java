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
}
