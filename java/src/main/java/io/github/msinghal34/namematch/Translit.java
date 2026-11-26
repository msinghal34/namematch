package io.github.msinghal34.namematch;

import java.text.Normalizer;
import java.util.HashMap;
import java.util.Map;

/**
 * Script normalisation: Kannada to everyday Indian-English spelling, homoglyphs, diacritics.
 *
 * <p>The output aims at how a Karnataka clerk would spell the name in English (ಸ್ವರೂಪ್ ಗೌಡ to
 * "swaroop gowda"), not at scholarly transliteration, because the other side of every comparison
 * is written that way.
 */
final class Translit {
    private Translit() {
    }

    private static final int VIRAMA = 0x0CCD;
    private static final int NUKTA = 0x0CBC;
    private static final int ANUSVARA = 0x0C82;
    private static final int VISARGA = 0x0C83;
    private static final int ZWNJ = 0x200C;
    private static final int ZWJ = 0x200D;

    private static final Map<Integer, String> VOWELS = map(
        0x0C85, "a", 0x0C86, "aa", 0x0C87, "i", 0x0C88, "ee", 0x0C89, "u", 0x0C8A, "oo", 0x0C8B, "ri", 0x0CE0, "ri",
        0x0C8E, "e", 0x0C8F, "e", 0x0C90, "ai", 0x0C92, "o", 0x0C93, "o", 0x0C94, "au");
    private static final Map<Integer, String> SIGNS = map(
        0x0CBE, "aa", 0x0CBF, "i", 0x0CC0, "ee", 0x0CC1, "u", 0x0CC2, "oo", 0x0CC3, "ri", 0x0CC4, "ri",
        0x0CC6, "e", 0x0CC7, "e", 0x0CC8, "ai", 0x0CCA, "o", 0x0CCB, "o", 0x0CCC, "au");
    private static final Map<Integer, String> CONSONANTS = map(
        0x0C95, "k", 0x0C96, "kh", 0x0C97, "g", 0x0C98, "gh", 0x0C99, "n",
        0x0C9A, "ch", 0x0C9B, "chh", 0x0C9C, "j", 0x0C9D, "jh", 0x0C9E, "n",
        0x0C9F, "t", 0x0CA0, "th", 0x0CA1, "d", 0x0CA2, "dh", 0x0CA3, "n",
        0x0CA4, "th", 0x0CA5, "th", 0x0CA6, "d", 0x0CA7, "dh", 0x0CA8, "n",
        0x0CAA, "p", 0x0CAB, "ph", 0x0CAC, "b", 0x0CAD, "bh", 0x0CAE, "m",
        0x0CAF, "y", 0x0CB0, "r", 0x0CB1, "r", 0x0CB2, "l", 0x0CB5, "v",
        0x0CB6, "sh", 0x0CB7, "sh", 0x0CB8, "s", 0x0CB9, "h", 0x0CB3, "l", 0x0CDE, "l");
    private static final Map<Integer, String> NUKTA_FORMS = map(0x0C9C, "z", 0x0CAB, "f");
    /** Stands in for ಜ್ಞ (and its misspelling ಜ್ಙ) while a run is read (kannada_jna). */
    private static final int JNA = 0xE000;

    /** Put around each word that came from Kannada when the caller asks (Parser, for cross_script). */
    static final String KN_OPEN = "\u0002";
    static final String KN_CLOSE = "\u0003";

    /** Cyrillic and Greek capitals that OCR or copy-paste leaves inside Latin names. */
    private static final Map<Integer, String> HOMOGLYPHS = map(
        0x410, "A", 0x412, "B", 0x415, "E", 0x41A, "K", 0x41C, "M", 0x41D, "H", 0x41E, "O", 0x420, "P",
        0x421, "C", 0x422, "T", 0x425, "X", 0x423, "Y", 0x430, "a", 0x435, "e", 0x43E, "o", 0x440, "p",
        0x441, "c", 0x445, "x", 0x391, "A", 0x392, "B", 0x395, "E", 0x397, "H", 0x399, "I", 0x39A, "K",
        0x39C, "M", 0x39D, "N", 0x39F, "O", 0x3A1, "P", 0x3A4, "T", 0x3A7, "X", 0x3A5, "Y", 0x396, "Z",
        0xA0, " ", 0x200C, "", 0x200D, "", 0xFEFF, "", 0x2022, " ");

    /** Initials are written in Kannada as the English letter's name (ಬಿ = "bi" = B). */
    private static final Map<String, String> LETTER_NAMES = new HashMap<>();

    static {
        String[] pairs = {
            "e", "a", "a", "a", "bi", "b", "si", "c", "see", "c", "di", "d", "dee", "d", "i", "e", "ee", "e",
            "eph", "f", "ef", "f", "ji", "g", "jee", "g", "ech", "h", "hech", "h", "ej", "h", "aai", "i", "ai", "i",
            "je", "j", "jai", "j", "ke", "k", "el", "l", "em", "m", "en", "n", "o", "o", "pi", "p", "pee", "p",
            "kyu", "q", "aar", "r", "ar", "r", "es", "s", "ti", "t", "tee", "t", "yu", "u", "vi", "v", "vee", "v",
            "dablyu", "w", "eks", "x", "vai", "y", "jhed", "z", "zed", "z",
        };
        for (int k = 0; k < pairs.length; k += 2) {
            LETTER_NAMES.put(pairs[k], pairs[k + 1]);
        }
    }

    private static Map<Integer, String> map(Object... kv) {
        Map<Integer, String> m = new HashMap<>();
        for (int k = 0; k < kv.length; k += 2) {
            m.put((Integer) kv[k], (String) kv[k + 1]);
        }
        return m;
    }

    private static boolean isKannada(int cp) {
        return cp >= 0x0C80 && cp <= 0x0CFF;
    }

    static boolean hasKannada(String text) {
        return text.codePoints().anyMatch(Translit::isKannada);
    }

    /** Transliterate each Kannada run; a run that spells a letter's name becomes that letter. */
    static String kannadaToLatin(String text) {
        return kannadaToLatin(text, false);
    }

    static String kannadaToLatin(String text, boolean mark) {
        StringBuilder out = new StringBuilder();
        int[] cps = text.codePoints().toArray();
        int k = 0;
        while (k < cps.length) {
            boolean run = isKannadaRun(cps[k]);
            int start = k;
            while (k < cps.length && isKannadaRun(cps[k]) == run) {
                k++;
            }
            String part = new String(cps, start, k - start);
            if (run && hasKannada(part)) {
                String latin = kannadaRun(cps, start, k);
                latin = LETTER_NAMES.getOrDefault(latin, latin);
                out.append(mark ? KN_OPEN + latin + KN_CLOSE : latin);
            } else {
                out.append(part);
            }
        }
        return out.toString();
    }

    private static boolean isKannadaRun(int cp) {
        return isKannada(cp) || cp == ZWNJ || cp == ZWJ;
    }

    private static String kannadaRun(int[] all, int from0, int to0) {
        int[] cps = java.util.Arrays.copyOfRange(all, from0, to0);
        if (Switches.KANNADA_JNA) {
            cps = replaceJna(cps);
        }
        int from = 0;
        int to = cps.length;
        StringBuilder out = new StringBuilder();
        int i = from;
        while (i < to) {
            int ch = cps[i];
            int nxt = i + 1 < to ? cps[i + 1] : -1;
            String base = ch == JNA ? "gn" : CONSONANTS.get(ch);
            if (base != null) {
                if (nxt == NUKTA) {
                    base = NUKTA_FORMS.getOrDefault(ch, base);
                    i++;
                    nxt = i + 1 < to ? cps[i + 1] : -1;
                }
                if (nxt == VIRAMA) {
                    out.append(base);
                    i += 2;
                    continue;
                }
                String sign = SIGNS.get(nxt);
                if (sign != null) {
                    out.append(base).append(sign);
                    i += 2;
                    continue;
                }
                out.append(base).append('a');
                i++;
                continue;
            }
            String vowel = VOWELS.get(ch);
            if (vowel != null) {
                out.append(vowel);
            } else if (ch == ANUSVARA) {
                String follower = nxt == -1 ? "" : CONSONANTS.getOrDefault(nxt, "");
                // Before a labial or at the end of a word it sounds 'm' (ಎಂ = em = M, ಕೋಂ = kom).
                String first = Py.head(follower, 1);
                out.append(nxt == -1 || first.equals("p") || first.equals("b") || first.equals("m") ? "m" : "n");
            } else if (ch == VISARGA) {
                out.append('h');
            } else if (ch >= 0x0CE6 && ch <= 0x0CEF) {
                out.append((char) ('0' + (ch - 0x0CE6)));
            } else if (ch == VIRAMA || ch == NUKTA || ch == ZWNJ || ch == ZWJ) {
                // dropped
            } else {
                out.appendCodePoint(ch);
            }
            i++;
        }
        return out.toString();
    }

    /** ಜ್ಞ and ಜ್ಙ (a common misspelling of it) as one JNA code point, like Python's str.replace. */
    private static int[] replaceJna(int[] cps) {
        int[] out = new int[cps.length];
        int n = 0;
        for (int i = 0; i < cps.length; i++) {
            if (i + 2 < cps.length && cps[i] == 0x0C9C && cps[i + 1] == VIRAMA && (cps[i + 2] == 0x0C9E || cps[i + 2] == 0x0C99)) {
                out[n++] = JNA;
                i += 2;
            } else {
                out[n++] = cps[i];
            }
        }
        return java.util.Arrays.copyOf(out, n);
    }

    /** Any supported script to plain ASCII-ish Latin, case preserved for Latin input. */
    static String toLatin(String text) {
        return toLatin(text, false);
    }

    /** As {@link #toLatin(String)}; mark=true wraps each word that came from Kannada in KN_OPEN ... KN_CLOSE. */
    static String toLatin(String text, boolean mark) {
        String nfc = Normalizer.normalize(text, Normalizer.Form.NFC);
        StringBuilder t = new StringBuilder(nfc.length());
        nfc.codePoints().forEach(cp -> {
            String h = HOMOGLYPHS.get(cp);
            if (h != null) {
                t.append(h);
            } else {
                t.appendCodePoint(cp);
            }
        });
        String s = t.toString();
        if (hasKannada(s)) {
            s = kannadaToLatin(s, mark);
        }
        String decomposed = Normalizer.normalize(s, Normalizer.Form.NFKD);
        StringBuilder out = new StringBuilder(decomposed.length());
        decomposed.codePoints().forEach(cp -> {
            if (!CombiningMarks.isCombining(cp)) {
                out.appendCodePoint(cp);
            }
        });
        return out.toString();
    }
}
