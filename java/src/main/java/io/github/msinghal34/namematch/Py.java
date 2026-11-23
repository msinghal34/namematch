package io.github.msinghal34.namematch;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.function.Function;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** The few Python behaviours the port must reproduce exactly. */
final class Py {
    private Py() {
    }

    /**
     * Flags that make java.util.regex read patterns the way Python's re does for str patterns:
     * Unicode \s and \d, and only "\n" ending a line for '.', '^' and '$'.
     */
    static final int FLAGS = Pattern.UNICODE_CHARACTER_CLASS | Pattern.UNIX_LINES;

    static Pattern re(String regex) {
        return Pattern.compile(regex, FLAGS);
    }

    /** Python's round(x, digits): the exact binary value, rounded half to even. */
    static double round(double x, int digits) {
        if (Double.isNaN(x) || Double.isInfinite(x)) {
            return x;
        }
        return new BigDecimal(x).setScale(digits, RoundingMode.HALF_EVEN).doubleValue();
    }

    /** Python's f"{x:.{digits}f}": the exact binary value, rounded half to even. */
    static String fixed(double x, int digits) {
        return new BigDecimal(x).setScale(digits, RoundingMode.HALF_EVEN).toPlainString();
    }

    /** re.sub with a function: every non-overlapping match replaced by what {@code f} returns. */
    static String sub(Pattern p, String text, Function<Matcher, String> f) {
        Matcher m = p.matcher(text);
        if (!m.find()) {
            return text;
        }
        StringBuilder out = new StringBuilder(text.length() + 16);
        int last = 0;
        do {
            out.append(text, last, m.start());
            out.append(f.apply(m));
            last = m.end();
        } while (m.find());
        out.append(text, last, text.length());
        return out.toString();
    }

    /** re.sub with a literal replacement. */
    static String sub(Pattern p, String text, String literal) {
        return sub(p, text, m -> literal);
    }

    /** Python's {@code s in "chars"} for a one-character (or empty) string. */
    static boolean inChars(String s, String chars) {
        return chars.contains(s);
    }

    /** The last character as a string, or "" (Python's s[-1:]). */
    static String last(String s) {
        return s.isEmpty() ? "" : s.substring(s.length() - 1);
    }

    /** Python's s[:n]. */
    static String head(String s, int n) {
        return s.length() <= n ? s : s.substring(0, n);
    }
}
