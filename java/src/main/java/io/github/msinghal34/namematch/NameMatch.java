package io.github.msinghal34.namematch;

/**
 * Rule-based person-name matching for Indian (Karnataka) property and identity records.
 *
 * <pre>{@code
 * MatchResult r = NameMatch.match("Sri. K. Ramesh Kumar S/o Krishnappa", "RAMESH KUMAR K");
 * r.score();      // 0.95
 * r.band();       // Band.SAME
 * r.reasons();    // [...]
 * }</pre>
 *
 * <p>It reads names the way a revenue officer does: titles (Sri, Smt) and relation clauses
 * (S/o, W/o, bin) are set aside, initials may stand for words, common spelling variants and
 * Kannada script are understood, and a string may list several owners. Gives the same scores,
 * bands and reasons as the Python library of the same version.
 *
 * <p>All methods are thread-safe. The library has no dependencies and runs on Java 11 or newer.
 */
public final class NameMatch {
    private NameMatch() {
    }

    /** The version of the rules, the same as the Python library's {@code namematch.VERSION}. */
    public static final String VERSION = Rules.VERSION;

    /** How strongly {@code a} and {@code b} name the same person; any owner matching any owner is enough. */
    public static MatchResult match(String a, String b) {
        return match(a, b, OwnerMode.ANY);
    }

    /** How strongly {@code a} and {@code b} name the same person(s), combining several owners as {@code owners} says. */
    public static MatchResult match(String a, String b, OwnerMode owners) {
        if (owners == null) {
            throw new IllegalArgumentException("owners must not be null");
        }
        return Scorer.match(Parser.parse(a), Parser.parse(b), owners);
    }

    /** Every owner named in {@code a} is found in {@code b}: the same as {@code match(a, b, OwnerMode.ALL_A)}. */
    public static MatchResult covers(String a, String b) {
        return match(a, b, OwnerMode.ALL_A);
    }
}
