package io.github.msinghal34.namematch;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.util.List;

/**
 * Command line:
 *
 * <pre>
 * java -jar namematch.jar "NAME A" "NAME B" [any|all_a|all]   score, band and reasons
 * java -jar namematch.jar --jsonl &lt; pairs.tsv                  one JSON result per line
 * </pre>
 *
 * <p>For --jsonl each input line is "A&lt;TAB&gt;B" or "A&lt;TAB&gt;B&lt;TAB&gt;mode", with tab, newline
 * and backslash inside a name written as \t, \n and \\.
 */
public final class Cli {
    private Cli() {
    }

    public static void main(String[] args) throws IOException {
        PrintStream out = new PrintStream(System.out, true, "UTF-8");
        if (args.length == 1 && args[0].equals("--jsonl")) {
            jsonl();
            return;
        }
        if (args.length < 2 || args.length > 3) {
            out.println("usage: java -jar namematch.jar \"NAME A\" \"NAME B\" [any|all_a|all]");
            out.println("       java -jar namematch.jar --jsonl < pairs.tsv");
            System.exit(2);
        }
        MatchResult r = NameMatch.match(args[0], args[1], args.length == 3 ? OwnerMode.fromId(args[2]) : OwnerMode.ANY);
        out.println("score  " + Py.fixed(r.score(), 3) + "  (" + r.band().id() + ")");
        out.println("pair   " + r.left() + "  ~  " + r.right());
        for (String reason : r.reasons()) {
            out.println("  - " + reason);
        }
    }

    private static void jsonl() throws IOException {
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
        BufferedWriter w = new BufferedWriter(new OutputStreamWriter(System.out, StandardCharsets.UTF_8));
        String line;
        while ((line = in.readLine()) != null) {
            String[] f = line.split("\t", -1);
            OwnerMode mode = f.length > 2 ? OwnerMode.fromId(f[2]) : OwnerMode.ANY;
            w.write(toJson(NameMatch.match(unescape(f[0]), unescape(f[1]), mode)));
            w.write('\n');
        }
        w.flush();
    }

    private static String unescape(String s) {
        StringBuilder out = new StringBuilder(s.length());
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c == '\\' && i + 1 < s.length()) {
                char e = s.charAt(++i);
                out.append(e == 't' ? '\t' : e == 'n' ? '\n' : e == 'r' ? '\r' : e);
            } else {
                out.append(c);
            }
        }
        return out.toString();
    }

    /** The result as one line of JSON, with the Python library's field names. */
    static String toJson(MatchResult r) {
        StringBuilder s = new StringBuilder(256);
        s.append("{\"score\":").append(r.score());
        s.append(",\"band\":").append(str(r.band().id()));
        s.append(",\"reasons\":[");
        List<String> reasons = r.reasons();
        for (int i = 0; i < reasons.size(); i++) {
            s.append(i > 0 ? "," : "").append(str(reasons.get(i)));
        }
        s.append("],\"left\":").append(str(r.left()));
        s.append(",\"right\":").append(str(r.right()));
        s.append(",\"owners\":").append(str(r.ownerMode().id()));
        s.append(",\"partial\":").append(r.isPartial());
        s.append(",\"owners_a\":");
        rows(s, r.ownersA());
        s.append(",\"owners_b\":");
        rows(s, r.ownersB());
        return s.append('}').toString();
    }

    private static void rows(StringBuilder s, List<OwnerRow> rows) {
        s.append('[');
        for (int i = 0; i < rows.size(); i++) {
            OwnerRow row = rows.get(i);
            s.append(i > 0 ? "," : "").append("{\"owner\":").append(str(row.owner()))
                .append(",\"best_match\":").append(row.bestMatch() == null ? "null" : str(row.bestMatch()))
                .append(",\"score\":").append(row.score()).append('}');
        }
        s.append(']');
    }

    private static String str(String v) {
        StringBuilder s = new StringBuilder(v.length() + 2).append('"');
        for (int i = 0; i < v.length(); i++) {
            char c = v.charAt(i);
            if (c == '"' || c == '\\') {
                s.append('\\').append(c);
            } else if (c < 0x20) {
                s.append(String.format("\\u%04x", (int) c));
            } else {
                s.append(c);
            }
        }
        return s.append('"').toString();
    }
}
