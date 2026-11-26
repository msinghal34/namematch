package io.github.msinghal34.namematch;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.fail;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

/**
 * Every case in conformance/cases.jsonl, which the Python library wrote, must come out of the Java
 * library field for field: score, band, reasons, the deciding pair, the partial flag and every
 * owner row.
 */
class ConformanceTest {

    @Test
    void javaReproducesPythonOnEveryCase() throws IOException {
        List<String> failures = new ArrayList<>();
        int n = 0;
        try (InputStream in = getClass().getResourceAsStream("/cases.jsonl")) {
            assertTrue(in != null, "cases.jsonl is missing; run python conformance/make_cases.py");
            BufferedReader r = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8));
            String line;
            while ((line = r.readLine()) != null) {
                if (line.isEmpty()) {
                    continue;
                }
                n++;
                JsonObject c = JsonParser.parseString(line).getAsJsonObject();
                String a = c.get("a").getAsString();
                String b = c.get("b").getAsString();
                String mode = c.get("owners").getAsString();
                JsonObject want = c.getAsJsonObject("expected");
                JsonObject got = JsonParser.parseString(Cli.toJson(NameMatch.match(a, b, OwnerMode.fromId(mode)))).getAsJsonObject();
                if (!same(want, got)) {
                    failures.add(String.format("%s | %s | %s%n  python: %s%n  java:   %s", a, b, mode, want, got));
                }
            }
        }
        assertTrue(n > 7000, "expected the full case file, read " + n + " cases");
        if (!failures.isEmpty()) {
            fail(failures.size() + " of " + n + " cases differ; first ones:\n"
                + String.join("\n", failures.subList(0, Math.min(15, failures.size()))));
        }
    }

    /** JSON equality with numbers compared as doubles (Python writes 1.0 and 1 alike). */
    private static boolean same(JsonElement x, JsonElement y) {
        if (x.isJsonNull() || y.isJsonNull()) {
            return x.isJsonNull() && y.isJsonNull();
        }
        if (x.isJsonPrimitive() && y.isJsonPrimitive()) {
            if (x.getAsJsonPrimitive().isNumber() && y.getAsJsonPrimitive().isNumber()) {
                return x.getAsDouble() == y.getAsDouble();
            }
            return x.equals(y);
        }
        if (x.isJsonArray() && y.isJsonArray()) {
            JsonArray xa = x.getAsJsonArray();
            JsonArray ya = y.getAsJsonArray();
            if (xa.size() != ya.size()) {
                return false;
            }
            for (int i = 0; i < xa.size(); i++) {
                if (!same(xa.get(i), ya.get(i))) {
                    return false;
                }
            }
            return true;
        }
        if (x.isJsonObject() && y.isJsonObject()) {
            JsonObject xo = x.getAsJsonObject();
            JsonObject yo = y.getAsJsonObject();
            if (!xo.keySet().equals(yo.keySet())) {
                return false;
            }
            for (String k : xo.keySet()) {
                if (!same(xo.get(k), yo.get(k))) {
                    return false;
                }
            }
            return true;
        }
        return false;
    }

    @Test
    void versionComesFromTheSharedRules() {
        assertEquals("0.5.0", NameMatch.VERSION);
    }
}
