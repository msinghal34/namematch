package io.github.msinghal34.namematch;

/** How the owners are combined when a name string lists several people. */
public enum OwnerMode {
    /** The best pair: any owner in A matching any owner in B is enough. */
    ANY("any"),
    /** Every owner in A must match some owner in B; the weakest one decides. */
    ALL_A("all_a"),
    /** Every owner on both sides must pair one-to-one with an owner on the other side. */
    ALL("all");

    private final String id;

    OwnerMode(String id) {
        this.id = id;
    }

    /** The mode's name as the Python library writes it: "any", "all_a" or "all". */
    public String id() {
        return id;
    }

    /** The mode with this id ("any", "all_a" or "all"). */
    public static OwnerMode fromId(String id) {
        for (OwnerMode m : values()) {
            if (m.id.equals(id)) {
                return m;
            }
        }
        throw new IllegalArgumentException("owners must be one of any, all_a, all; got " + id);
    }
}
