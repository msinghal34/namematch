package io.github.msinghal34.namematch;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * The rule data shared with the Python library: rules.toml, token_freq.tsv and name_gender.tsv,
 * packaged next to this class. Read once.
 */
final class Rules {
    private Rules() {
    }

    static final Map<String, Object> RULES = Collections.unmodifiableMap(Toml.parse(read("rules.toml")));
    static final String VERSION = (String) RULES.get("version");
    static final Map<String, Integer> TOKEN_FREQ = loadFreq();
    static final Map<String, String> NAME_GENDER = loadGender();

    @SuppressWarnings("unchecked")
    static Map<String, Object> table(String name) {
        return (Map<String, Object>) RULES.get(name);
    }

    @SuppressWarnings("unchecked")
    static List<String> strings(Map<String, Object> table, String key) {
        return (List<String>) table.get(key);
    }

    @SuppressWarnings("unchecked")
    static List<List<String>> pairsOf(Map<String, Object> table, String key) {
        return (List<List<String>>) table.get(key);
    }

    private static String read(String name) {
        try (InputStream in = Rules.class.getResourceAsStream(name)) {
            if (in == null) {
                return null;
            }
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new UncheckedIOException("cannot read " + name, e);
        }
    }

    private static List<String> dataLines(String name) {
        String text = read(name);
        List<String> out = new ArrayList<>();
        if (text == null) {
            return out;
        }
        for (String line : text.split("\r\n|\n|\r", -1)) {
            if (!line.isEmpty() && !line.startsWith("#")) {
                out.add(line);
            }
        }
        return out;
    }

    private static Map<String, Integer> loadFreq() {
        Map<String, Integer> out = new HashMap<>();
        for (String line : dataLines("token_freq.tsv")) {
            String[] f = line.split("\t", -1);
            out.put(f[0], Integer.parseInt(f[1]));
        }
        return Collections.unmodifiableMap(out);
    }

    private static Map<String, String> loadGender() {
        Map<String, String> out = new HashMap<>();
        for (String line : dataLines("name_gender.tsv")) {
            String[] f = line.split("\t", -1);
            out.put(f[0], Integer.parseInt(f[1]) > Integer.parseInt(f[2]) ? "m" : "f");
        }
        return Collections.unmodifiableMap(out);
    }

    /**
     * The subset of TOML that rules.toml uses: comments, [table] headers, bare or "quoted" keys,
     * and values that are basic strings or (nested, multi-line) arrays of them.
     */
    static final class Toml {
        private final String s;
        private int i;

        private Toml(String s) {
            this.s = s;
        }

        static Map<String, Object> parse(String text) {
            if (text == null) {
                throw new IllegalStateException("rules.toml is missing from the jar");
            }
            return new Toml(text).document();
        }

        private Map<String, Object> document() {
            Map<String, Object> root = new LinkedHashMap<>();
            Map<String, Object> current = root;
            while (true) {
                skipBlank();
                if (i >= s.length()) {
                    return root;
                }
                if (s.charAt(i) == '[') {
                    i++;
                    String name = key();
                    expect(']');
                    Map<String, Object> t = new LinkedHashMap<>();
                    root.put(name, t);
                    current = t;
                } else {
                    String k = key();
                    skipSpaces();
                    expect('=');
                    skipSpaces();
                    current.put(k, value());
                }
            }
        }

        private String key() {
            skipSpaces();
            if (s.charAt(i) == '"') {
                return string();
            }
            int start = i;
            while (i < s.length() && (Character.isLetterOrDigit(s.charAt(i)) || s.charAt(i) == '_' || s.charAt(i) == '-')) {
                i++;
            }
            if (start == i) {
                throw error("key expected");
            }
            return s.substring(start, i);
        }

        private Object value() {
            char c = s.charAt(i);
            if (c == '"') {
                return string();
            }
            if (c == '[') {
                i++;
                List<Object> items = new ArrayList<>();
                while (true) {
                    skipBlank();
                    if (s.charAt(i) == ']') {
                        i++;
                        return Collections.unmodifiableList(items);
                    }
                    items.add(value());
                    skipBlank();
                    if (s.charAt(i) == ',') {
                        i++;
                    } else if (s.charAt(i) != ']') {
                        throw error("',' or ']' expected");
                    }
                }
            }
            throw error("only strings and arrays are supported");
        }

        private String string() {
            expect('"');
            StringBuilder out = new StringBuilder();
            while (s.charAt(i) != '"') {
                char c = s.charAt(i++);
                if (c == '\\') {
                    char e = s.charAt(i++);
                    switch (e) {
                        case 'n': out.append('\n'); break;
                        case 't': out.append('\t'); break;
                        case '"': out.append('"'); break;
                        case '\\': out.append('\\'); break;
                        default: throw error("unsupported escape \\" + e);
                    }
                } else {
                    out.append(c);
                }
            }
            i++;
            return out.toString();
        }

        private void expect(char c) {
            if (i >= s.length() || s.charAt(i) != c) {
                throw error("'" + c + "' expected");
            }
            i++;
        }

        private void skipSpaces() {
            while (i < s.length() && (s.charAt(i) == ' ' || s.charAt(i) == '\t')) {
                i++;
            }
        }

        /** Spaces, newlines and comments. */
        private void skipBlank() {
            while (i < s.length()) {
                char c = s.charAt(i);
                if (c == '#') {
                    while (i < s.length() && s.charAt(i) != '\n') {
                        i++;
                    }
                } else if (Character.isWhitespace(c)) {
                    i++;
                } else {
                    return;
                }
            }
        }

        private IllegalStateException error(String what) {
            int line = 1;
            for (int k = 0; k < Math.min(i, s.length()); k++) {
                if (s.charAt(k) == '\n') {
                    line++;
                }
            }
            return new IllegalStateException("rules.toml line " + line + ": " + what);
        }
    }
}
