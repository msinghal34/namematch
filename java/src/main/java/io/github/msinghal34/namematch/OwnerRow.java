package io.github.msinghal34.namematch;

import java.util.Objects;

/**
 * One owner as the matcher read it, with its best counterpart on the other side.
 *
 * <p>The owner is written the way the matcher understood it: titles removed, initials as capitals
 * with a dot, a relation clause as "(rel ...)", and "[m]" or "[f]" when the record shows the
 * gender. For example "savitha rao (rel anand rao) [f]".
 */
public final class OwnerRow {
    private final String owner;
    private final String bestMatch;
    private final double score;

    OwnerRow(String owner, String bestMatch, double score) {
        this.owner = owner;
        this.bestMatch = bestMatch;
        this.score = score;
    }

    /** This owner, as read. */
    public String owner() {
        return owner;
    }

    /** The owner on the other side that matches this one best, as read; null if that side names nobody. */
    public String bestMatch() {
        return bestMatch;
    }

    /** The score of that best pair, 0 to 1, rounded to 3 decimals. */
    public double score() {
        return score;
    }

    @Override
    public boolean equals(Object o) {
        if (!(o instanceof OwnerRow)) {
            return false;
        }
        OwnerRow r = (OwnerRow) o;
        return owner.equals(r.owner) && Objects.equals(bestMatch, r.bestMatch) && score == r.score;
    }

    @Override
    public int hashCode() {
        return Objects.hash(owner, bestMatch, score);
    }

    @Override
    public String toString() {
        return owner + " ~ " + bestMatch + " " + score;
    }
}
