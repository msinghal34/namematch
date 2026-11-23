package io.github.msinghal34.namematch;

import java.util.Collections;
import java.util.List;
import java.util.Locale;

/** The result of comparing two name strings. Immutable and safe to share between threads. */
public final class MatchResult {
    private final double score;
    private final Band band;
    private final List<String> reasons;
    private final String left;
    private final String right;
    private final OwnerMode ownerMode;
    private final boolean partial;
    private final List<OwnerRow> ownersA;
    private final List<OwnerRow> ownersB;

    MatchResult(double score, List<String> reasons, String left, String right, OwnerMode ownerMode, boolean partial,
                List<OwnerRow> ownersA, List<OwnerRow> ownersB) {
        this.score = score;
        this.band = Band.of(score);
        this.reasons = Collections.unmodifiableList(reasons);
        this.left = left;
        this.right = right;
        this.ownerMode = ownerMode;
        this.partial = partial;
        this.ownersA = ownersA;
        this.ownersB = ownersB;
    }

    /** How strongly the two strings name the same person, from 0 to 1, rounded to 3 decimals. */
    public double score() {
        return score;
    }

    /** The band the score falls in. */
    public Band band() {
        return band;
    }

    /** True when the score is in the {@link Band#SAME} band (0.80 or more): safe to accept automatically. */
    public boolean isAccepted() {
        return band == Band.SAME;
    }

    /**
     * Why the score is what it is, in short phrases such as "kumr~kumar 0.86", "K.=krishna",
     * "extra: reddy" or "differs: ramesh / suresh". Empty when the names match exactly.
     */
    public List<String> reasons() {
        return reasons;
    }

    /** The owner on side A that decided the score, as the matcher read it. */
    public String left() {
        return left;
    }

    /** The owner on side B that decided the score, as the matcher read it. */
    public String right() {
        return right;
    }

    /** How several owners were combined. */
    public OwnerMode ownerMode() {
        return ownerMode;
    }

    /**
     * True when a side names several owners and at least one of them has no counterpart scoring 0.80
     * or more on the other side (for example, a co-owner missing from the other record).
     */
    public boolean isPartial() {
        return partial;
    }

    /** Every owner on side A with its best counterpart on side B. */
    public List<OwnerRow> ownersA() {
        return ownersA;
    }

    /** Every owner on side B with its best counterpart on side A. */
    public List<OwnerRow> ownersB() {
        return ownersB;
    }

    @Override
    public String toString() {
        return String.format(Locale.ROOT, "MatchResult(%s %s: %s ~ %s; %s)", Py.fixed(score, 2), band.id(), left, right,
            String.join("; ", reasons));
    }
}
