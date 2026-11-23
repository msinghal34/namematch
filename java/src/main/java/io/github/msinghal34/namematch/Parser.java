package io.github.msinghal34.namematch;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Turn a raw owner-name string into structured persons and organisations.
 *
 * <p>Handles the shapes seen across Draft Khata, Aadhaar, registered deeds and property tax:
 * several owners in one string, numbering, honorifics, relation clauses (S/o, W/o, bin, ಕೋಂ),
 * GPA / "rep by" clauses, aliases, companies, placeholders, joined initials and Kannada script.
 */
final class Parser {
    private Parser() {
    }

    // ---- structures -----------------------------------------------------------------------

    static final class Token {
        final String text;
        final boolean initial;

        Token(String text, boolean initial) {
            this.text = text;
            this.initial = initial;
        }

        @Override
        public String toString() {
            return initial ? text.toUpperCase(Locale.ROOT) + "." : text;
        }
    }

    static final class Person {
        final List<Token> tokens;
        final List<List<Token>> aliases;
        final List<Token> relative;
        final String gender;      // "m", "f" or "" from honorific / relation evidence
        final String relation;    // kind of the relation clause: "s/o", "w/o", "bin", "kom", ...
        final String role;        // "owner" or "representative"
        final boolean firm;       // written as "M/s <person name>": a proprietorship

        Person(List<Token> tokens, List<List<Token>> aliases, List<Token> relative, String gender, String relation,
               String role, boolean firm) {
            this.tokens = tokens;
            this.aliases = aliases;
            this.relative = relative;
            this.gender = gender;
            this.relation = relation;
            this.role = role;
            this.firm = firm;
        }

        List<String> full() {
            List<String> out = new ArrayList<>();
            for (Token t : tokens) {
                if (!t.initial) {
                    out.add(t.text);
                }
            }
            return out;
        }

        List<String> initials() {
            List<String> out = new ArrayList<>();
            for (Token t : tokens) {
                if (t.initial) {
                    out.add(t.text);
                }
            }
            return out;
        }

        @Override
        public String toString() {
            StringBuilder s = new StringBuilder(join(tokens));
            if (!relative.isEmpty()) {
                s.append(" (rel ").append(join(relative)).append(')');
            }
            if (!gender.isEmpty()) {
                s.append(" [").append(gender).append(']');
            }
            if (!role.equals("owner")) {
                s.append(" <").append(role).append('>');
            }
            return s.toString();
        }
    }

    static final class Organisation {
        final List<String> tokens;
        final String raw;

        Organisation(List<String> tokens, String raw) {
            this.tokens = tokens;
            this.raw = raw;
        }

        @Override
        public String toString() {
            return "ORG(" + String.join(" ", tokens) + ")";
        }
    }

    static final class ParsedName {
        final String raw;
        final List<Person> persons;
        final List<Organisation> orgs;
        final List<Person> representatives;
        final boolean placeholder;
        final String script;      // "latin" or "kannada"

        ParsedName(String raw, List<Person> persons, List<Organisation> orgs, List<Person> representatives,
                   boolean placeholder, String script) {
            this.raw = raw;
            this.persons = persons;
            this.orgs = orgs;
            this.representatives = representatives;
            this.placeholder = placeholder;
            this.script = script;
        }

        boolean empty() {
            return persons.isEmpty() && orgs.isEmpty();
        }
    }

    static String join(List<Token> tokens) {
        StringBuilder s = new StringBuilder();
        for (Token t : tokens) {
            if (s.length() > 0) {
                s.append(' ');
            }
            s.append(t);
        }
        return s.toString();
    }

    // ---- rule data ------------------------------------------------------------------------

    private static final Map<String, Object> L = Rules.table("lists");
    private static final Set<String> HONORIFICS = set(Rules.strings(Rules.RULES, "honorifics"));
    private static final Set<String> FEMALE_HON = set(Rules.strings(Rules.RULES, "female_honorifics"));
    private static final Set<String> MALE_HON = set(Rules.strings(Rules.RULES, "male_honorifics"));
    /** Title words that are also given names, kept when nothing else is left ("Miss Kumari"). */
    private static final Set<String> TITLE_OR_NAME = set(Arrays.asList("kumari", "baby", "master", "major", "selvi", "chiranjeevi"));
    private static final Set<String> HONORIFICS_ANYWHERE =
        set(Arrays.asList("late", "smt", "mrs", "mr", "dr", "shrimati", "srimati", "smti"));
    static final Set<String> ORG_WORDS = orgWords();
    private static final Set<String> PLACEHOLDERS = L.containsKey("placeholders") ? set(Rules.strings(L, "placeholders")) : set(List.of());
    private static final List<String> ORG_NOISE = Rules.strings(L, "org_noise");
    private static final Set<String> ORG_TAIL = orgTail();
    /** Initials spelled out in English letters by the digitisers ("EM ANITA" = M Anita). */
    private static final Map<String, String> SPELLED_INITIALS = new HashMap<>();
    private static final Set<String> FILLER =
        set(Arrays.asList("his", "her", "their", "its", "the", "holder", "gpa", "by", "of", "power", "attorney", "agreement", "sale"));

    static {
        String[] kv = {"em", "m", "en", "n", "es", "s", "el", "l", "aar", "r", "ech", "h", "hech", "h", "jee", "g"};
        for (int k = 0; k < kv.length; k += 2) {
            SPELLED_INITIALS.put(kv[k], kv[k + 1]);
        }
    }

    // Marker tokens inserted into the text before tokenising.
    static final String SEP = "\u0001sep";
    static final String REL = "\u0001rel";
    static final String REP = "\u0001rep";
    static final String ALIAS = "\u0001alias";

    private static Set<String> set(List<String> items) {
        return Collections.unmodifiableSet(new HashSet<>(items));
    }

    private static Set<String> orgWords() {
        Set<String> s = new HashSet<>(Rules.strings(L, "org_words"));
        s.remove("m/s");
        return Collections.unmodifiableSet(s);
    }

    private static Set<String> orgTail() {
        Set<String> s = new HashSet<>(Rules.strings(L, "org_noise"));
        s.addAll(ORG_WORDS);
        return s;
    }

    // ---- marking ------------------------------------------------------------------------

    /** Python's re.escape: a backslash before ()[]{}?*+-|^$\.&~# and whitespace. */
    private static String pyEscape(String p) {
        StringBuilder out = new StringBuilder();
        for (char c : p.toCharArray()) {
            if ("()[]{}?*+-|^$\\.&~# \t\n\r\u000b\f".indexOf(c) >= 0) {
                out.append('\\');
            }
            out.append(c);
        }
        return out.toString();
    }

    private static Pattern phraseRegex(List<String> phrases) {
        List<String> alts = new ArrayList<>();
        for (String p : phrases) {
            alts.add(pyEscape(p).replace("\\ ", "[\\s.]*"));
        }
        // Longest first; equal lengths keep their order (Python's sort is stable).
        alts.sort((x, y) -> Integer.compare(y.length(), x.length()));
        return Py.re("(?<![a-z\\x01:])(?:" + String.join("|", alts) + ")(?![a-z])");
    }

    /** "S/o", "s / o", "S\\o", "s/olate", and the slash lost in digitisation ("W O") between words. */
    private static final Pattern REL_SLASH = Py.re(
        "(?<![a-z/])([sdwhc])\\s*[/\\\\]\\s*o(?=late(?![a-z])|[^a-z]|$)\\.?"
            + "|(?<=[a-z])([sdw])/o(?=[^a-z]|$)"
            + "|(?<![a-z.])([sdw])\\s+o(?=\\s+[a-z])(?![a-z])"
            + "|(?<![a-z])([sdw])\\.\\s*o\\.");
    /** "&lt;agent&gt; GPA holder for &lt;owner&gt;": the owner comes after. */
    private static final Pattern HOLDER_FOR = Py.re(
        "^(.*?)(?<![a-z])(?:(?:is\\s+)?(?:the\\s+)?(?:(?:gpa|spa|poa|pa|power of attorney)\\s*)?holders?"
            + "|is\\s+(?:the\\s+)?(?:gpa|spa|poa|pa))\\s+(?:for|of)(?![a-z])(.*)$");
    private static final Map<String, Object> RELATIONS = Rules.table("relations");
    private static final Pattern TRAILING = phraseRegex(Rules.strings(L, "trailing"));
    private static final Pattern REPRESENTATION = phraseRegex(Rules.strings(L, "representation"));
    private static final Pattern ALIASES = phraseRegex(without(Rules.strings(L, "alias"), "@"));
    private static final Pattern REL_WORDS = phraseRegex(relationWords());
    private static final Pattern SPACE_DOT = Py.re("[\\s.]+");
    private static final Pattern STRIP_CHARS = Py.re("[=*_~`^]");
    private static final Pattern SEPARATORS = Py.re("[|;&+()\\[\\]{}\\n\\t]");
    private static final Pattern AND_WORDS = Py.re("(?<![a-z\\x01:])(and|an|with|mattu|maththu|haagu)(?![a-z])");
    private static final Pattern NUMBERS = Py.re("(?<![a-z0-9])\\d+(?![a-z0-9])");
    private static final Pattern DIGIT_WORDS = Py.re("[a-z]*\\d[a-z0-9]*");
    private static final Pattern A_TO_Z = Py.re("[a-z]");
    private static final Pattern JOINED_CAPS = Py.re("(?<![A-Za-z.])(MS|MR|SH|AN|NA)(?=\\s+[A-Z]{2,})");
    private static final Pattern PIECES = Py.re("\\x01\\w+(?::[\\w/]+)?|m/s|[a-z]+");

    private static List<String> without(List<String> items, String drop) {
        List<String> out = new ArrayList<>(items);
        out.removeIf(drop::equals);
        return out;
    }

    private static List<String> relationWords() {
        List<String> out = new ArrayList<>();
        for (String k : RELATIONS.keySet()) {
            if (!k.contains("/")) {
                out.add(k);
            }
        }
        return out;
    }

    private static String firstGroup(Matcher m) {
        for (int g = 1; g <= m.groupCount(); g++) {
            String s = m.group(g);
            if (s != null && !s.isEmpty()) {
                return s;
            }
        }
        throw new IllegalStateException("no group matched");
    }

    private static String ocrDigits(String word) {
        if (!A_TO_Z.matcher(word).find()) {
            return " " + SEP + " ";
        }
        StringBuilder out = new StringBuilder(word.length());
        for (char c : word.toCharArray()) {
            int k = "0134568927".indexOf(c);
            out.append(k >= 0 ? "oieasgbgzt".charAt(k) : c);
        }
        return out.toString();
    }

    static String mark(String text) {
        text = Py.sub(STRIP_CHARS, text, "");
        if (Switches.HOLDER_FOR) {
            String[] parts = text.split("\\|", -1);
            for (int k = 0; k < parts.length; k++) {
                parts[k] = Py.sub(HOLDER_FOR, parts[k], m -> m.group(2) + " rep by " + m.group(1));
            }
            text = String.join("|", parts);
        }
        text = text.replace("@", " " + ALIAS + " ");
        text = Py.sub(REL_SLASH, text, m -> " " + REL + ":" + firstGroup(m) + "/o ");
        text = Py.sub(TRAILING, text, " ");
        text = Py.sub(REPRESENTATION, text, " " + REP + " ");
        text = Py.sub(ALIASES, text, " " + ALIAS + " ");
        text = Py.sub(REL_WORDS, text,
            m -> " " + REL + ":" + Py.sub(SPACE_DOT, m.group(0), " ").strip().replace(' ', '_') + " ");
        // Owner separators. "an" is a common typo for "and" between names.
        text = Py.sub(SEPARATORS, text, " " + SEP + " ");
        // "mattu" is Kannada for "and", left untranslated by the digitisers.
        text = Py.sub(AND_WORDS, text, " " + SEP + " ");
        text = text.replace(",", " " + SEP + " ");
        // Numbering ("1.", "2)", "(3)") and stray digits separate owners; digits inside words are OCR slips.
        text = Py.sub(NUMBERS, text, " " + SEP + " ");
        text = Py.sub(DIGIT_WORDS, text, m -> ocrDigits(m.group(0)));
        return text;
    }

    // ---- tokens and persons ---------------------------------------------------------------

    private static List<String> joinLetters(List<String> words) {
        List<String> out = new ArrayList<>();
        StringBuilder run = new StringBuilder();
        for (String w : words) {
            if (w.length() == 1) {
                run.append(w);
                continue;
            }
            if (run.length() > 0) {
                out.add(run.toString());
                run.setLength(0);
            }
            out.add(w);
        }
        if (run.length() > 0) {
            out.add(run.toString());
        }
        out.removeIf("p"::equals);
        return out;
    }

    private static boolean hasVowel(String word) {
        for (char c : word.toCharArray()) {
            if ("aeiouy".indexOf(c) >= 0) {
                return true;
            }
        }
        return false;
    }

    /** Short vowel-less clusters are joined initials: 'ns' to N S, 'kb' to K B. */
    private static List<Token> splitWord(String word) {
        if (Switches.SPELLED_INITIALS && SPELLED_INITIALS.containsKey(word)) {
            return List.of(new Token(SPELLED_INITIALS.get(word), true));
        }
        if (word.length() == 1) {
            return List.of(new Token(word, true));
        }
        if (word.length() <= 3 && !hasVowel(word) && !Phonetic.VARIANT_WORDS.contains(word)) {
            List<Token> out = new ArrayList<>();
            for (char c : word.toCharArray()) {
                out.add(new Token(String.valueOf(c), true));
            }
            return out;
        }
        return List.of(new Token(word, false));
    }

    private static final class Cleaned {
        final List<Token> tokens;
        final String gender;

        Cleaned(List<Token> tokens, String gender) {
            this.tokens = tokens;
            this.gender = gender;
        }
    }

    private static Cleaned cleanPerson(List<String> words) {
        String gender = "";
        List<String> original = words;
        // Leading honorifics, possibly several ("mr dr", "surg lt cdr").
        int start = 0;
        while (start < words.size() && HONORIFICS.contains(words.get(start))) {
            String w = words.get(start);
            if (FEMALE_HON.contains(w)) {
                gender = "f";
            } else if (MALE_HON.contains(w)) {
                gender = "m";
            }
            start++;
        }
        List<String> kept = new ArrayList<>();
        for (String w : words.subList(start, words.size())) {
            if (!HONORIFICS_ANYWHERE.contains(w)) {
                kept.add(w);
            }
        }
        if (kept.isEmpty() && !original.isEmpty() && TITLE_OR_NAME.contains(original.get(original.size() - 1))) {
            kept.add(original.get(original.size() - 1));     // "Miss Kumari": the title word is the name
        }
        List<Token> tokens = new ArrayList<>();
        for (String w : kept) {
            tokens.addAll(splitWord(w));
        }
        return new Cleaned(tokens, gender);
    }

    private static boolean anyFull(List<Token> tokens) {
        for (Token t : tokens) {
            if (!t.initial) {
                return true;
            }
        }
        return false;
    }

    private static boolean isOrg(List<String> words, String rawSegment) {
        if (rawSegment.contains("m/s") || rawSegment.contains("m/ s")) {
            return true;
        }
        for (String w : words) {
            if (ORG_WORDS.contains(w)) {
                return true;
            }
        }
        return false;
    }

    private static final class Segment {
        final List<String> name = new ArrayList<>();
        final List<List<String>> alias = new ArrayList<>();
        final List<String> rel = new ArrayList<>();
        String relKind = "";
        final List<String> rep = new ArrayList<>();
        String mode = "name";
    }

    static ParsedName parse(String raw) {
        raw = raw == null ? "" : raw;
        String script = Translit.hasKannada(raw) ? "kannada" : "latin";
        String latin = Translit.toLatin(raw);
        // In capitals, a two-letter word without a dot before a name is joined initials, not a
        // title or "and": "MS RAMESH" = M S Ramesh, "AN RAMESH" = A N Ramesh.
        latin = Py.sub(JOINED_CAPS, latin, m -> m.group(1).charAt(0) + " " + m.group(1).charAt(1));
        String text = mark(latin.toLowerCase(Locale.ROOT));
        // Tokenise into markers and words; any other punctuation is whitespace.
        List<String> pieces = new ArrayList<>();
        Matcher pm = PIECES.matcher(text.replace("'", " ").replace("-", " "));
        while (pm.find()) {
            pieces.add(pm.group());
        }

        List<Segment> segments = new ArrayList<>();
        Segment current = new Segment();
        segments.add(current);
        for (String piece : pieces) {
            if (piece.equals(SEP)) {
                current = new Segment();
                segments.add(current);
            } else if (piece.startsWith(REL)) {
                int colon = piece.indexOf(':');
                String kind = colon >= 0 ? piece.substring(colon + 1) : "";
                if (current.name.isEmpty() && segments.size() > 1 && !segments.get(segments.size() - 2).name.isEmpty()
                        && segments.get(segments.size() - 2).rel.isEmpty()) {
                    // "G. Prakash, S/o Ranga Rao": the clause belongs to the previous owner.
                    segments.remove(segments.size() - 1);
                    current = segments.get(segments.size() - 1);
                }
                if (current.mode.equals("rep") || current.mode.equals("rep_rel")) {
                    current.mode = "rep_rel";     // a relative of the representative: not evidence
                    continue;
                }
                current.mode = "rel";
                current.relKind = kind.replace('_', ' ');
            } else if (piece.equals(REP)) {
                current.mode = "rep";
            } else if (piece.equals(ALIAS)) {
                current.mode = "alias";
                current.alias.add(new ArrayList<>());
            } else {
                switch (current.mode) {
                    case "rep_rel":
                        break;
                    case "name":
                        current.name.add(piece);
                        break;
                    case "alias":
                        current.alias.get(current.alias.size() - 1).add(piece);
                        break;
                    case "rel":
                        current.rel.add(piece);
                        break;
                    default:
                        current.rep.add(piece);
                }
            }
        }

        // "(India) Pvt Ltd" after a company name is part of it, not another owner.
        List<Segment> merged = new ArrayList<>();
        for (Segment seg : segments) {
            if (!merged.isEmpty() && !seg.name.isEmpty() && ORG_TAIL.containsAll(seg.name) && seg.rel.isEmpty()
                    && seg.rep.isEmpty()) {
                merged.get(merged.size() - 1).name.addAll(seg.name);
            } else {
                merged.add(seg);
            }
        }
        segments = merged;

        List<Person> persons = new ArrayList<>();
        List<Organisation> orgs = new ArrayList<>();
        List<Person> reps = new ArrayList<>();
        boolean placeholder = false;
        for (Segment seg : segments) {
            List<String> words = seg.name;
            if (words.isEmpty() && seg.rep.isEmpty()) {
                continue;
            }
            if (!words.isEmpty()) {
                String segmentText = String.join(" ", words);
                if (words.get(0).equals("m/s") && !anyIn(words, ORG_WORDS)) {
                    List<String> rest = new ArrayList<>();
                    for (String w : words.subList(1, words.size())) {
                        if (!PLACEHOLDERS.contains(w)) {
                            rest.add(w);
                        }
                    }
                    Cleaned c = cleanPerson(rest);
                    if (anyFull(c.tokens)) {
                        persons.add(new Person(c.tokens, List.of(), List.of(), c.gender, "", "owner", true));
                    }
                } else if (isOrg(words, segmentText)) {
                    List<String> kept = new ArrayList<>();
                    for (String w : words) {
                        if (!ORG_NOISE.contains(w) || w.length() == 1) {
                            kept.add(w);
                        }
                    }
                    List<String> orgWords = joinLetters(kept);
                    if (!orgWords.isEmpty()) {
                        List<String> canon = new ArrayList<>();
                        for (String w : orgWords) {
                            canon.add(Phonetic.canonical(w));
                        }
                        orgs.add(new Organisation(canon, segmentText));
                    }
                } else {
                    List<String> meaningful = new ArrayList<>();
                    for (String w : words) {
                        if (!PLACEHOLDERS.contains(w)) {
                            meaningful.add(w);
                        }
                    }
                    if (meaningful.isEmpty()) {
                        placeholder = true;
                    } else {
                        Cleaned c = cleanPerson(meaningful);
                        List<Token> relTokens = seg.rel.isEmpty() ? List.of() : cleanPerson(seg.rel).tokens;
                        Object rg = RELATIONS.get(seg.relKind);
                        String relGender = rg == null ? "" : (String) rg;
                        List<List<Token>> aliases = new ArrayList<>();
                        for (List<String> x : seg.alias) {
                            List<Token> a = cleanPerson(x).tokens;
                            if (!a.isEmpty()) {
                                aliases.add(a);
                            }
                        }
                        Person p = new Person(c.tokens, aliases, relTokens, c.gender.isEmpty() ? relGender : c.gender,
                            seg.relKind, "owner", false);
                        if (anyFull(c.tokens) || !p.aliases.isEmpty()) {
                            persons.add(p);
                        } else if (!c.tokens.isEmpty() && persons.isEmpty() && seg.rep.isEmpty()) {
                            persons.add(p);
                        }
                    }
                }
            }
            if (!seg.rep.isEmpty()) {
                List<String> rest = new ArrayList<>();
                for (String w : seg.rep) {
                    if (!PLACEHOLDERS.contains(w) && !FILLER.contains(w)) {
                        rest.add(w);
                    }
                }
                Cleaned c = cleanPerson(rest);
                if (anyFull(c.tokens)) {
                    reps.add(new Person(c.tokens, List.of(), List.of(), c.gender, "", "representative", false));
                }
            }
        }
        return new ParsedName(raw, persons, orgs, reps, placeholder && persons.isEmpty() && orgs.isEmpty(), script);
    }

    private static boolean anyIn(List<String> words, Set<String> set) {
        for (String w : words) {
            if (set.contains(w)) {
                return true;
            }
        }
        return false;
    }
}
