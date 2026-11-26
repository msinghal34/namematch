package io.github.msinghal34.namematch;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.function.Function;
import java.util.regex.Pattern;

/**
 * Phonetic keys and token similarity tuned for Indian names written in Latin script.
 *
 * <p>The key folds the spelling freedom of romanised Indian names (aspirates, long vowels, w/v,
 * z/j, ksh/x, -iah/-ayya, final -a, doubled letters) so that common variants collide, while the
 * edit-distance fallback absorbs whatever the rules miss.
 */
final class Phonetic {
    private Phonetic() {
    }

    private static final Map<String, String> VARIANT = new HashMap<>();
    static final Set<String> VARIANT_WORDS = new HashSet<>();

    static {
        for (List<String> group : Rules.pairsOf(Rules.table("variants"), "groups")) {
            for (String member : group) {
                VARIANT.put(member, group.get(0));
                VARIANT_WORDS.add(member);
            }
        }
    }

    private static final class Rewrite {
        final Pattern pattern;
        final String replacement;   // null: the first group, doubled letters collapse to one

        Rewrite(String regex, String replacement) {
            this.pattern = Py.re(regex);
            this.replacement = replacement;
        }

        String apply(String t) {
            return replacement == null ? Py.sub(pattern, t, m -> m.group(1)) : Py.sub(pattern, t, replacement);
        }
    }

    /** Ordered rewrites. */
    private static final List<Rewrite> REWRITES = Arrays.asList(
        new Rewrite("ksh", "ks"),
        new Rewrite("x", "ks"),
        new Rewrite("q", "k"),
        new Rewrite("z", "j"),
        new Rewrite("w", "v"),
        new Rewrite("ph", "f"),
        new Rewrite("ck", "k"),
        new Rewrite("chh", "ch"),
        new Rewrite("ch", "C"),          // protect ch while c becomes k
        new Rewrite("c", "k"),
        new Rewrite("C", "c"),
        new Rewrite("sh", "s"),
        new Rewrite("th", "t"),
        new Rewrite("dh", "d"),
        new Rewrite("bh", "b"),
        new Rewrite("gh", "g"),
        new Rewrite("kh", "k"),
        new Rewrite("jh", "j"),
        new Rewrite("ee|ii|ie(?=.)", "i"),
        new Rewrite("oo|uu", "u"),
        new Rewrite("ow|ou|au|ao", "au"),
        new Rewrite("aa", "a"),
        new Rewrite("ei|ey(?=.)", "ai"),
        new Rewrite("(?<=[^aeiou])y$", "i"),
        new Rewrite("aiah$|aiya$|ayya$|iah$|aya$", "aya"),
        new Rewrite("ayi$|ay$", "ai"),
        new Rewrite("(?<=[aeiou])h$", ""),
        new Rewrite("(?<=[^aeiou])h(?=[^aeiou]|$)", ""),
        new Rewrite("(.)\\1+", null));

    /** A bounded, thread-safe memo, standing in for Python's lru_cache. */
    static final class Memo<K, V> {
        private final Map<K, V> map;
        private final Function<K, V> f;

        Memo(int max, Function<K, V> f) {
            this.f = f;
            this.map = Collections.synchronizedMap(new LinkedHashMap<K, V>(1024, 0.75f, true) {
                private static final long serialVersionUID = 1L;

                @Override
                protected boolean removeEldestEntry(Map.Entry<K, V> eldest) {
                    return size() > max;
                }
            });
        }

        V get(K k) {
            V v = map.get(k);
            if (v == null) {
                v = f.apply(k);
                map.put(k, v);
            }
            return v;
        }
    }

    private static final Memo<String, String> KEY = new Memo<>(200_000, t -> orSelf(fold(canonical(t), true), t));
    private static final Memo<String, String> RAW_KEY = new Memo<>(200_000, t -> orSelf(fold(t, true), t));
    private static final Memo<String, String> GENDER_KEY = new Memo<>(200_000, t -> orSelf(fold(t, false), t));
    private static final Memo<List<String>, Double> SIMILARITY =
        new Memo<>(500_000, ab -> computeSimilarity(ab.get(0), ab.get(1)));

    private static String orSelf(String s, String fallback) {
        return s.isEmpty() ? fallback : s;
    }

    /** rules.toml variants.mined_groups (mined_variants): the first group naming a word wins. */
    private static final Map<String, String> MINED = new HashMap<>();

    static {
        @SuppressWarnings("unchecked")
        List<List<String>> mined = (List<List<String>>) Rules.table("variants").getOrDefault("mined_groups", List.of());
        for (List<String> group : mined) {
            for (String member : group) {
                MINED.putIfAbsent(member, VARIANT.getOrDefault(group.get(0), group.get(0)));
            }
        }
    }

    static String canonical(String token) {
        if (Switches.MINED_VARIANTS && MINED.containsKey(token) && !VARIANT.containsKey(token)) {
            return MINED.get(token);
        }
        return VARIANT.getOrDefault(token, token);
    }

    /** Phonetic key of the token's canonical spelling (variants table applied first). */
    static String key(String token) {
        return KEY.get(token);
    }

    /** Phonetic key of the token as written, for spellings the variants table does not list. */
    static String rawKey(String token) {
        return RAW_KEY.get(token);
    }

    /** Key that keeps name endings, which carry gender (kamal / kamala, madhav / madhavi). */
    static String genderKey(String token) {
        return GENDER_KEY.get(token);
    }

    private static final List<String> FEMALE_END = Rules.strings(Rules.table("gender"), "female_suffixes");
    private static final List<String> MALE_END = Rules.strings(Rules.table("gender"), "male_suffixes");

    /**
     * "m" or "f": first from how the records use this given name, else from an ending that only one
     * gender takes (-amma, -kumari, -begum / -appa, -ayya, -kumar); "" when unknown.
     */
    static String genderOf(String token) {
        String g = Rules.NAME_GENDER.getOrDefault(genderKey(token), "");
        if (!g.isEmpty()) {
            return g;
        }
        for (String e : FEMALE_END) {
            if (token.endsWith(e) && token.length() >= e.length() + 3) {
                return "f";
            }
        }
        for (String e : MALE_END) {
            if (token.endsWith(e) && token.length() >= e.length() + 3) {
                return "m";
            }
        }
        return "";
    }

    private static final Pattern OW = Py.re("ow(?=[^aeiou]|$)");
    private static final Pattern JN = Py.re("^jn");
    private static final Pattern Y_VOWEL = Py.re("(?<=[^aeiou])y(?=[^aeiouy])");

    static String fold(String t, boolean endings) {
        // Before the ordered rewrites, which turn w into v and would hide 'ow' (sowmya, gowri).
        if (Switches.OW_VOWEL) {
            t = Py.sub(OW, t, "au");
        }
        if (Switches.Y_VOWEL) {
            t = Py.sub(Y_VOWEL, t, "ai");
        }
        if (Switches.KANNADA_JNA) {
            // Only at the start of a word (jnana / gnana); inside a word jn is usually j + n (Rajni).
            t = Py.sub(JN, t, "gn");
        }
        for (int pass = 0; pass < 2; pass++) {   // second pass catches endings exposed by the first ('bhimaiaha')
            for (Rewrite r : REWRITES) {
                t = r.apply(t);
            }
            if (!endings) {
                continue;
            }
            if (t.length() > 3 && t.endsWith("a")) {
                t = t.substring(0, t.length() - 1);
            }
            // Tamil -an on a name ending in s / n / p: srinivasan ~ srinivas, narayanan ~ narayana,
            // muniyappan ~ muniyappa. Not rahman / salman / lakshman / sultan / kalyan.
            if (t.length() > 5 && t.endsWith("an") && "snp".indexOf(t.charAt(t.length() - 3)) >= 0) {
                t = t.substring(0, t.length() - 2);
            }
        }
        return t;
    }

    /** Edit distance counting an adjacent swap ('deepit' / 'deepti') as one edit. */
    static int levenshtein(String a, String b) {
        if (a.equals(b)) {
            return 0;
        }
        int n = a.length();
        int m = b.length();
        int[][] d = new int[n + 1][m + 1];
        for (int i = 0; i <= n; i++) {
            d[i][0] = i;
        }
        for (int j = 0; j <= m; j++) {
            d[0][j] = j;
        }
        for (int i = 1; i <= n; i++) {
            for (int j = 1; j <= m; j++) {
                int cost = a.charAt(i - 1) != b.charAt(j - 1) ? 1 : 0;
                d[i][j] = Math.min(Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1), d[i - 1][j - 1] + cost);
                if (i > 1 && j > 1 && a.charAt(i - 1) == b.charAt(j - 2) && a.charAt(i - 2) == b.charAt(j - 1)) {
                    d[i][j] = Math.min(d[i][j], d[i - 2][j - 2] + 1);
                }
            }
        }
        return d[n][m];
    }

    private static boolean isSubsequence(String shortS, String longS) {
        int p = 0;
        for (int i = 0; i < shortS.length(); i++) {
            char ch = shortS.charAt(i);
            while (p < longS.length() && longS.charAt(p) != ch) {
                p++;
            }
            if (p == longS.length()) {
                return false;
            }
            p++;
        }
        return true;
    }

    private static final Pattern VOWELS_Y = Py.re("[aeiouy]");

    /** Consonants of a key: 'kumr' and 'kumar' share 'kmr'. */
    static String skeleton(String k) {
        return k.charAt(0) + Py.sub(VOWELS_Y, k.substring(1), "");
    }

    private static double ratio(String a, String b) {
        return 1 - (double) levenshtein(a, b) / Math.max(Math.max(a.length(), b.length()), 1);
    }

    private static final List<List<String>> PAIRS = Rules.pairsOf(Rules.table("gender"), "pairs");

    /**
     * Opposite genders on look-alike names: mallappa / mallamma, kumar / kumari, and any pair the
     * records show with opposite genders (kamal / kamala, salman / salma, madhav / madhavi).
     */
    static boolean genderConflict(String a, String b) {
        String ga = genderOf(a);
        String gb = genderOf(b);
        if (!ga.isEmpty() && !gb.isEmpty() && !ga.equals(gb)
                && Py.head(genderKey(a), 3).equals(Py.head(genderKey(b), 3))) {
            return true;
        }
        String[][] orders = {{a, b}, {b, a}};
        for (List<String> pair : PAIRS) {
            String male = pair.get(0);
            String female = pair.get(1);
            for (String[] xy : orders) {
                String x = xy[0];
                String y = xy[1];
                if (x.endsWith(male) && y.endsWith(female)) {
                    String stemX = x.substring(0, x.length() - male.length());
                    String stemY = y.substring(0, y.length() - female.length());
                    if (stemX.equals(stemY)
                            || (Math.min(stemX.length(), stemY.length()) >= 2 && key(stemX).equals(key(stemY)))) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    private static final Set<Character> SOFT_FIRST = new HashSet<>(Arrays.asList('s', 'c', 'j', 'v', 'b', 'e', 'i', 'a', 'u', 'o'));

    /** Similarity of two full name tokens in [0, 1]; 0 means 'not the same word'. */
    static double similarity(String a, String b) {
        return SIMILARITY.get(Arrays.asList(a, b));
    }

    private static double computeSimilarity(String a, String b) {
        if (a.equals(b)) {
            return 1.0;
        }
        if (canonical(a).equals(canonical(b))) {
            return 0.98;
        }
        if (genderConflict(a, b)) {
            return 0.0;
        }
        String ka = key(a);
        String kb = key(b);
        if (ka.equals(kb) || rawKey(a).equals(rawKey(b)) || rawKey(a).equals(kb) || ka.equals(rawKey(b))) {
            return 0.95;
        }
        ka = rawKey(a);
        kb = rawKey(b);
        int shortest = Math.min(ka.length(), kb.length());
        if (shortest < 3) {
            return 0.0;
        }
        // Only dropped vowels ('kumr' / 'kumar'), never changed ones ('kamal' / 'komal').
        String shortK = kb.length() < ka.length() ? kb : ka;
        String longK = kb.length() < ka.length() ? ka : kb;
        if (Switches.VOWEL_DROP && (skeleton(shortK).length() >= 3 || shortK.length() >= 4)
                && skeleton(shortK).equals(skeleton(longK)) && isSubsequence(shortK, longK)) {
            return 0.86;
        }
        double rKey = ratio(ka, kb);
        double rRaw = ratio(a, b);
        double best = Math.max(rKey * 0.95, rRaw * 0.92);
        // Short names need near-identity (kamala / komal); long words tolerate a slip or two.
        boolean shortName = Switches.SHORT_FLOOR ? longK.length() <= 6 : shortest <= 4;
        double floor = shortName ? 0.84 : shortest <= 7 ? 0.74 : 0.70;
        if (Math.max(rKey, rRaw) < floor) {
            return 0.0;
        }
        // The first sound carries more identity than the rest.
        if (ka.charAt(0) != kb.charAt(0) && !(SOFT_FIRST.contains(ka.charAt(0)) && SOFT_FIRST.contains(kb.charAt(0)))) {
            best *= 0.8;
        }
        return Py.round(best, 3);
    }

    /**
     * Two words with the same first letter and the same consonants in the same order, only the vowels
     * different or moved: a slip in English ('pravin' / 'parvin'), or an English name spelled by sound in
     * Kannada (a Kannada word is tried in each of its readings). Different names fit too (kamala / komal),
     * so this only ever sends a pair to an officer (capped below 0.65). Never across genders.
     */
    static boolean vowelSlip(String a, String b, boolean aKn, boolean bKn) {
        return VOWEL_SLIP.get(Arrays.asList(a, b, String.valueOf(aKn), String.valueOf(bKn)));
    }

    private static boolean computeVowelSlip(String a, String b, boolean aKn, boolean bKn) {
        List<String> ra = aKn && !bKn ? readings(a) : Collections.singletonList(a);
        List<String> rb = bKn && !aKn ? readings(b) : Collections.singletonList(b);
        for (String x : ra) {
            for (String y : rb) {
                if (genderConflict(x, y) || (aKn != bKn && (aKn ? crossGenderConflict(x, y) : crossGenderConflict(y, x)))) {
                    continue;
                }
                String kx = rawKey(x);
                String ky = rawKey(y);
                if (Math.min(kx.length(), ky.length()) >= 4 && kx.charAt(0) == ky.charAt(0) && !kx.equals(ky)
                        && skeleton(kx).equals(skeleton(ky)) && skeleton(kx).length() >= 2) {
                    return true;
                }
            }
        }
        return false;
    }

    /** Letters a writer might use as this word's initial. */
    static Set<String> initialOf(String token) {
        char first = token.charAt(0);
        Set<String> alts = new HashSet<>();
        alts.add(String.valueOf(first));
        if (first == 'v' || first == 'w') {
            alts.add("v");
            alts.add("w");
        }
        if (first == 'j' || first == 'z') {
            alts.add("j");
            alts.add("z");
        }
        if (first == 'e' || first == 'i') {
            alts.add("e");
            alts.add("i");
        }
        return alts;
    }

    // ---- v0.5.0: a Kannada-written word against an English-written one --------------------------

    /**
     * Gender endings whose final a is part of the ending, never Kannada's silent final a: the a-final ones
     * in rules.toml (amma, appa, ayya) and the Kannada kinship endings -akka and -avva.
     */
    private static final List<String> GENDER_SUFFIXES = genderSuffixes();
    private static final Pattern CONSONANT_Y = Py.re("[^aeiou]y$");
    private static final Pattern YAA = Py.re("(?<=[^aeiouy])y(?=aa)");
    private static final Pattern NASAL_N = Py.re("n(?=[^aeiouyn])");
    private static final Memo<List<String>, Double> CROSS_SIMILARITY =
        new Memo<>(500_000, kl -> computeCrossSimilarity(kl.get(0), kl.get(1)));
    private static final Memo<List<String>, Boolean> VOWEL_SLIP = new Memo<>(500_000,
        k -> computeVowelSlip(k.get(0), k.get(1), Boolean.parseBoolean(k.get(2)), Boolean.parseBoolean(k.get(3))));

    private static List<String> genderSuffixes() {
        List<String> out = new ArrayList<>();
        for (String e : FEMALE_END) {
            if (e.endsWith("a")) {
                out.add(e);
            }
        }
        for (String e : MALE_END) {
            if (e.endsWith("a")) {
                out.add(e);
            }
        }
        out.add("akka");
        out.add("avva");
        return out;
    }

    /**
     * A Kannada word's final short a (ವಿನಯ to 'vinaya'), which English spelling usually drops and which does
     * not say the name is female; a long final aa, a gender ending, or a stem ending in consonant + y keep it.
     */
    static boolean inherentA(String k) {
        if (k.length() <= 3 || !k.endsWith("a") || k.endsWith("aa")) {
            return false;
        }
        for (String e : GENDER_SUFFIXES) {
            if (k.endsWith(e)) {
                return false;
            }
        }
        return !CONSONANT_Y.matcher(k.substring(0, k.length() - 1)).find();
    }

    /** With a Kannada final short a, both readings (with and without it) must conflict. */
    static boolean crossGenderConflict(String k, String latin) {
        return genderConflict(k, latin) && (!inherentA(k) || genderConflict(k.substring(0, k.length() - 1), latin));
    }

    /** Other ways the Kannada-written word may be the English spelling of the same name, sorted. */
    static List<String> readings(String k) {
        Set<String> out = new TreeSet<>();
        out.add(k);
        if (Switches.CROSS_READINGS) {
            for (Pattern p : List.of(YAA, NASAL_N)) {
                String repl = p == YAA ? "" : "m";
                for (String t : new ArrayList<>(out)) {
                    out.add(Py.sub(p, t, repl));
                }
            }
        }
        if (Switches.KANNADA_JNA) {
            for (String t : new ArrayList<>(out)) {
                out.add(t.replace("gn", "jn"));
            }
        }
        return new ArrayList<>(out);
    }

    /** similarity() for a word written in Kannada (k) against one written in English (cross_script). */
    static double crossSimilarity(String k, String latin) {
        return CROSS_SIMILARITY.get(Arrays.asList(k, latin));
    }

    private static double computeCrossSimilarity(String k, String latin) {
        double s = similarity(k, latin);
        String gk = genderOf(k);
        String gl = genderOf(latin);
        // Names of opposite genders may meet through another reading only where it gives the English name itself.
        boolean opposite = (!gk.isEmpty() && !gl.isEmpty() && !gk.equals(gl)) || genderConflict(k, latin);
        for (String r : readings(k)) {
            if (!r.equals(k)) {
                double other = similarity(r, latin);
                if (!opposite || other >= 0.95) {
                    s = Math.max(s, Math.min(other, 0.95));
                }
            }
            if (inherentA(r)) {
                double stripped = similarity(r.substring(0, r.length() - 1), latin);
                if (!opposite || stripped >= 0.95) {
                    s = Math.max(s, Math.min(stripped, 0.95));
                }
            }
        }
        return s;
    }
}
