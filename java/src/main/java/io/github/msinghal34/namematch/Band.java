package io.github.msinghal34.namematch;

/** How strongly a score says "the same person", from the strongest band to the weakest. */
public enum Band {
    /** 0.80 and above: the same person; safe to accept automatically. */
    SAME("same", 0.80),
    /** 0.65 to 0.80: probably the same person; worth a quick look. */
    LIKELY_SAME("likely_same", 0.65),
    /** 0.35 to 0.65: could be the same person; an officer should decide. */
    REVIEW("review", 0.35),
    /** Below 0.35: different people. */
    DIFFERENT("different", 0.0);

    private final String id;
    private final double floor;

    Band(String id, double floor) {
        this.id = id;
        this.floor = floor;
    }

    /** The band's name as the Python library writes it: "same", "likely_same", "review" or "different". */
    public String id() {
        return id;
    }

    /** The lowest score in this band. */
    public double floor() {
        return floor;
    }

    /** The band a score falls in. */
    public static Band of(double score) {
        for (Band b : values()) {
            if (score >= b.floor) {
                return b;
            }
        }
        return DIFFERENT;
    }
}
