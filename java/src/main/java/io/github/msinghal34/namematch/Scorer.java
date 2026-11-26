package io.github.msinghal34.namematch;

import io.github.msinghal34.namematch.Parser.Organisation;
import io.github.msinghal34.namematch.Parser.ParsedName;
import io.github.msinghal34.namematch.Parser.Person;
import io.github.msinghal34.namematch.Parser.Token;
import java.util.ArrayList;
import java.util.BitSet;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.TreeSet;

/**
 * Score how strongly two names denote the same person, the way a revenue officer reads them.
 *
 * <p>The score is evidence-weighted coverage: distinctive words that agree push it up, common words
 * (Kumar, Reddy) count for less, an initial that explains a spelled-out word counts as weak
 * agreement, and two different words in the same name, contradicting initials, or opposite genders
 * pull it down hard.
 */
final class Scorer {
    private Scorer() {
    }

    static final double MATCH_FLOOR = 0.70;   // token similarity below this is "not the same word"
    static final double NEAR_SIM = 0.75;      // a near-miss word (one letter slip in a short name) when it is allowed
    static final double NEAR_CAP = 0.64;      // ... and the most such a pair can score: "needs a check", never accepted
    /** A part counts as common from 25 sightings per 153,218 persons: the sample the weights were tuned on. */
    private static final double COMMON_RATE = 25.0 / 153_218;

    private static final class Table {
        final java.util.Map<String, Integer> freq;
        final double common;
        final int top;

        Table(Rules.Freq f) {
            this.freq = f.counts;
            this.common = f.persons != 0 ? COMMON_RATE * f.persons : 25;
            int max = 1;
            boolean any = false;
            for (int n : f.counts.values()) {
                max = any ? Math.max(max, n) : n;
                any = true;
            }
            this.top = max;
        }
    }

    /** The table the eaasthi_weights switch picks, worked out once. */
    private static final Table TABLE =
        new Table(Switches.EAASTHI_WEIGHTS && !Rules.TOKEN_FREQ_EAASTHI.counts.isEmpty() ? Rules.TOKEN_FREQ_EAASTHI : Rules.TOKEN_FREQ);

    /** 1.0 for a distinctive word, down to 0.35 for the commonest (kumar). */
    static double weight(String token) {
        int n = TABLE.freq.getOrDefault(Phonetic.key(token), 0);
        if (n <= TABLE.common) {
            return 1.0;
        }
        return 1.0 - 0.65 * Math.log(n / TABLE.common) / Math.log(TABLE.top / TABLE.common);
    }

    private static final class Unit {
        final BitSet idx;
        final String text;
        final double w;
        final boolean kn;       // some word of it came from Kannada script

        Unit(BitSet idx, String text, double w, boolean kn) {
            this.idx = idx;
            this.text = text;
            this.w = w;
            this.kn = kn;
        }

        int size() {
            return idx.cardinality();
        }
    }

    /** Each full word, plus runs of 2-3 adjacent full words joined (for 'Sura Narayana' ~ 'Suranarayana'). */
    private static List<Unit> units(List<Token> tokens) {
        List<Unit> out = new ArrayList<>();
        int n = tokens.size();
        for (int i = 0; i < n; i++) {
            Token t = tokens.get(i);
            if (t.initial) {
                continue;
            }
            BitSet one = new BitSet();
            one.set(i);
            out.add(new Unit(one, t.text, weight(t.text), t.kn));
            for (int j = i + 2; j <= i + 3; j++) {
                if (j > n) {
                    continue;
                }
                boolean allFull = true;
                boolean kn = false;
                StringBuilder text = new StringBuilder();
                double w = 0;
                for (int k = i; k < j; k++) {
                    Token x = tokens.get(k);
                    allFull &= !x.initial;
                    kn |= x.kn;
                    text.append(x.text);
                    w = k == i ? weight(x.text) : Math.max(w, weight(x.text));
                }
                if (allFull) {
                    BitSet run = new BitSet();
                    run.set(i, j);
                    out.add(new Unit(run, text.toString(), w, kn));
                }
            }
        }
        return out;
    }

    private static final class Candidate {
        final double s;
        final int size;
        final Unit x;
        final Unit y;

        Candidate(double s, int size, Unit x, Unit y) {
            this.s = s;
            this.size = size;
            this.x = x;
            this.y = y;
        }
    }

    static final class Scored {
        final double score;
        final List<String> reasons;

        Scored(double score, List<String> reasons) {
            this.score = score;
            this.reasons = reasons;
        }
    }

    /** Word similarity; a Kannada-written word against an English-written one uses Phonetic.crossSimilarity. */
    private static double similar(String x, boolean xKn, String y, boolean yKn, String recorded) {
        if (Switches.CROSS_SCRIPT && xKn != yKn) {
            String k = xKn ? x : y;
            String latin = xKn ? y : x;
            String g = Phonetic.genderOf(latin);
            // The gender the Kannada side's record states (Smt, W/o, D/o, kom) is not overridden by its readings.
            if (!recorded.isEmpty() && !g.isEmpty() && !g.equals(recorded)) {
                return Phonetic.similarity(k, latin);
            }
            return Phonetic.crossSimilarity(k, latin);
        }
        return Phonetic.similarity(x, y);
    }

    private static boolean genderClash(Token x, Token y) {
        if (Switches.CROSS_SCRIPT && x.kn != y.kn) {
            return x.kn ? Phonetic.crossGenderConflict(x.text, y.text) : Phonetic.crossGenderConflict(y.text, x.text);
        }
        return Phonetic.genderConflict(x.text, y.text);
    }

    private static double total(List<Integer> idx, List<Token> tokens) {
        double t = 0.0;
        for (int i : idx) {
            t += weight(tokens.get(i).text);
        }
        return t;
    }

    private static List<Integer> indices(List<Token> tokens, boolean initial, BitSet used) {
        List<Integer> out = new ArrayList<>();
        for (int i = 0; i < tokens.size(); i++) {
            if (tokens.get(i).initial == initial && !used.get(i)) {
                out.add(i);
            }
        }
        return out;
    }

    private static Integer firstFull(List<Token> tokens) {
        for (int i = 0; i < tokens.size(); i++) {
            if (!tokens.get(i).initial) {
                return i;
            }
        }
        return null;
    }

    static Scored scoreTokens(List<Token> a, List<Token> b, List<Token> relA, List<Token> relB, boolean near) {
        return scoreTokens(a, b, relA, relB, near, "", "");
    }

    static Scored scoreTokens(List<Token> a, List<Token> b, List<Token> relA, List<Token> relB, boolean near,
                              String genderA, String genderB) {
        List<String> reasons = new ArrayList<>();
        List<Unit> ua = units(a);
        List<Unit> ub = units(b);
        List<Candidate> candidates = new ArrayList<>();
        Set<List<String>> nearPairs = new HashSet<>();
        Set<List<String>> vowelPairs = new HashSet<>();   // Kannada vs English words with only the vowels different
        for (Unit x : ua) {
            for (Unit y : ub) {
                if (x.size() > 1 && y.size() > 1) {
                    continue;
                }
                String recorded = x.kn ? genderA : genderB;     // the gender the Kannada side's record states
                double s = similar(x.text, x.kn, y.text, y.kn, recorded);
                if (s < MATCH_FLOOR && near && x.size() == 1 && y.size() == 1) {
                    String latinGender = Phonetic.genderOf(x.kn ? y.text : x.text);
                    boolean contradicts = !recorded.isEmpty() && !latinGender.isEmpty() && !latinGender.equals(recorded);
                    if (Phonetic.nearMiss(x.text, y.text)) {
                        s = NEAR_SIM;
                        nearPairs.add(List.of(x.text, y.text));
                    } else if (Switches.CROSS_SCRIPT && x.kn != y.kn && !contradicts
                            && (x.kn ? Phonetic.crossVowelsOnly(x.text, y.text) : Phonetic.crossVowelsOnly(y.text, x.text))) {
                        s = NEAR_SIM;
                        vowelPairs.add(List.of(x.text, y.text));
                    }
                }
                if (s >= MATCH_FLOOR) {
                    candidates.add(new Candidate(s, x.size() + y.size(), x, y));
                }
            }
        }
        // Highest (similarity, size) first; ties keep their order, as Python's stable sort does.
        candidates.sort((p, q) -> p.s != q.s ? Double.compare(q.s, p.s) : Integer.compare(q.size, p.size));

        BitSet usedA = new BitSet();
        BitSet usedB = new BitSet();
        double matchedMass = 0.0;
        double matchedW = 0.0;
        for (Candidate c : candidates) {
            if (c.x.idx.intersects(usedA) || c.y.idx.intersects(usedB)) {
                continue;
            }
            usedA.or(c.x.idx);
            usedB.or(c.y.idx);
            double w = (c.x.w + c.y.w) / 2;
            matchedMass += c.s * w;
            matchedW += w;
            if (nearPairs.contains(List.of(c.x.text, c.y.text))) {
                reasons.add(c.x.text + "?" + c.y.text + " one letter apart");
            } else if (vowelPairs.contains(List.of(c.x.text, c.y.text))) {
                reasons.add(c.x.text + "?" + c.y.text + " vowels differ across scripts");
            } else if (!c.x.text.equals(c.y.text)) {
                reasons.add(c.x.text + "~" + c.y.text + " " + Py.fixed(c.s, 2));
            }
        }

        List<Integer> freeA = indices(a, false, usedA);
        List<Integer> freeB = indices(b, false, usedB);
        List<Integer> initA = indices(a, true, usedA);
        List<Integer> initB = indices(b, true, usedB);

        // Initials against initials of the same letter.
        for (Integer i : new ArrayList<>(initA)) {
            for (int k = 0; k < initB.size(); k++) {
                Integer j = initB.get(k);
                if (a.get(i).text.equals(b.get(j).text)) {
                    initA.remove(i);
                    initB.remove(k);
                    break;
                }
            }
        }

        Integer firstA = firstFull(a);
        Integer firstB = firstFull(b);

        // Initials that explain a spelled-out word on the other side ('K' ~ 'Krishnamurthy').
        double explainedW = 0.0;
        Object[][] explainSides = {{initA, a, freeB}, {initB, b, freeA}};
        for (Object[] row : explainSides) {
            @SuppressWarnings("unchecked") List<Integer> inits = (List<Integer>) row[0];
            @SuppressWarnings("unchecked") List<Token> side = (List<Token>) row[1];
            @SuppressWarnings("unchecked") List<Integer> otherFree = (List<Integer>) row[2];
            List<Token> other = side == a ? b : a;
            for (Integer i : new ArrayList<>(inits)) {
                for (int k = 0; k < otherFree.size(); k++) {
                    Integer j = otherFree.get(k);
                    if (Phonetic.initialOf(other.get(j).text).contains(side.get(i).text)) {
                        inits.remove(i);
                        otherFree.remove(k);
                        explainedW += weight(other.get(j).text);
                        reasons.add(side.get(i).text.toUpperCase(Locale.ROOT) + ".=" + other.get(j).text);
                        break;
                    }
                }
            }
        }

        // A word on one side that is the other side's recorded relative ('PRABHAKARA K NARASIMHA' vs
        // 'PRABHAKARA K S/O K NARASIMHA'): the father's name appended, not a different person. Only
        // when the person who carries the relative was matched by their own given name.
        if (Switches.RELATIVE_EXPLAINS) {
            boolean carrierB = firstB != null && usedB.get(firstB);
            boolean carrierA = firstA != null && usedA.get(firstA);
            Object[][] relSides = {{a, freeA, relB, carrierB}, {b, freeB, relA, carrierA}};
            for (Object[] row : relSides) {
                if (!(Boolean) row[3]) {
                    continue;
                }
                @SuppressWarnings("unchecked") List<Token> side = (List<Token>) row[0];
                @SuppressWarnings("unchecked") List<Integer> free = (List<Integer>) row[1];
                @SuppressWarnings("unchecked") List<Token> rel = (List<Token>) row[2];
                List<String> relWords = new ArrayList<>();
                for (Token t : rel) {
                    if (!t.initial) {
                        relWords.add(t.text);
                    }
                }
                for (Integer i : new ArrayList<>(free)) {
                    for (String r : relWords) {
                        if (Phonetic.similarity(side.get(i).text, r) >= MATCH_FLOOR) {
                            free.remove(i);
                            explainedW += weight(side.get(i).text);
                            reasons.add(side.get(i).text + "=relative");
                            break;
                        }
                    }
                }
            }
        }

        int initConflicts = Math.min(initA.size(), initB.size());
        // An initial left over on one side while the other side still has an unexplained word:
        // 'Kavya Thimmappa K' vs 'K B Thimmappa' - B. should have been Kavya and is not.
        int wordConflicts = 0;
        if (Switches.WORD_CONFLICT && initConflicts == 0) {
            wordConflicts = Math.min(initA.size(), freeB.size()) + Math.min(initB.size(), freeA.size());
        }
        int missingInits = Math.max(initA.size(), initB.size()) - initConflicts - wordConflicts;
        if (missingInits != 0) {
            List<String> letters = new ArrayList<>();
            for (int i : initA) {
                letters.add(a.get(i).text.toUpperCase(Locale.ROOT));
            }
            for (int j : initB) {
                letters.add(b.get(j).text.toUpperCase(Locale.ROOT));
            }
            reasons.add("initials on one side only: " + String.join(" ", letters));
        }

        boolean genderClash = false;
        for (int i : freeA) {
            for (int j : freeB) {
                if (genderClash(a.get(i), b.get(j))) {
                    genderClash = true;
                    break;
                }
            }
            if (genderClash) {
                break;
            }
        }
        double massA = total(freeA, a);
        double massB = total(freeB, b);
        double conflict = !freeA.isEmpty() && !freeB.isEmpty() ? Math.min(massA, massB) : 0.0;
        double extra = Math.max(massA, massB) - conflict;

        if (matchedW == 0) {
            if (genderClash) {
                reasons.add("gender conflict");
            }
            return new Scored(0.0, reasons);
        }

        // An extra word on one side (surname, father's name) costs less than a word that disagrees.
        double denominator = matchedW + conflict + extra * 0.4 + explainedW * 0.08 + missingInits * 0.08;
        double score = matchedMass / denominator;
        if (conflict != 0) {
            score *= 0.55;
            List<String> names = new ArrayList<>();
            for (int i : freeA) {
                names.add(a.get(i).text);
            }
            names.add("/");
            for (int j : freeB) {
                names.add(b.get(j).text);
            }
            reasons.add("differs: " + String.join(" ", names));
        } else if (extra != 0) {
            List<String> names = new ArrayList<>();
            for (int i : freeA) {
                names.add(a.get(i).text);
            }
            for (int j : freeB) {
                names.add(b.get(j).text);
            }
            reasons.add("extra: " + String.join(" ", names));
        }
        if (initConflicts != 0) {
            score *= Math.pow(0.75, initConflicts);
            reasons.add("initials differ (" + initConflicts + ")");
        }
        if (wordConflicts != 0) {
            // Milder when the given names (leading words) agree: 'Raghunandan B K' vs 'Raghunandan Venugopal Sharma'.
            boolean givenAgree = firstA != null && usedA.get(firstA) && firstB != null && usedB.get(firstB);
            score *= Math.pow(givenAgree ? 0.85 : 0.5, wordConflicts);
            reasons.add("initial does not fit a word (" + wordConflicts + ")");
        }
        if (genderClash) {
            score = Math.min(score, 0.2);
            reasons.add("gender conflict");
        }
        return new Scored(score, reasons);
    }

    private static final Set<String> PARENT = Set.of("s/o", "d/o", "bin", "binti", "bint", "son of", "daughter of");
    private static final Set<String> SPOUSE = Set.of("w/o", "h/o", "kom", "kon", "wife of", "husband of");

    private static String kind(String relation) {
        return PARENT.contains(relation) ? "parent" : SPOUSE.contains(relation) ? "spouse" : "";
    }

    private static List<String> plus(List<String> reasons, String reason) {
        List<String> out = new ArrayList<>(reasons);
        out.add(reason);
        return out;
    }

    /** Use the recorded relatives as evidence against, not only for, a match. */
    private static Scored relatives(Person p, Person q, double score, List<String> reasons) {
        if (!Switches.RELATIVE_CONFLICT || score == 0) {
            return new Scored(score, reasons);
        }
        String kp = kind(p.relation);
        String kq = kind(q.relation);
        if (!p.relative.isEmpty() && !q.relative.isEmpty() && !kp.isEmpty() && !kq.isEmpty()) {
            double r = scoreTokens(p.relative, q.relative, List.of(), List.of(), false).score;
            if (kp.equals(kq) && r < 0.35) {
                // 'Ramesh S/o Krishna' vs 'Ramesh S/o Gopal': namesakes with different fathers.
                return new Scored(score * 0.5, plus(reasons, "relatives differ"));
            }
            if (!kp.equals(kq) && r >= 0.8) {
                // 'Lakshmi W/o Ramesh' vs 'Lakshmi D/o Ramesh': his wife and his daughter.
                return new Scored(score * 0.5, plus(reasons, "same relative, different relation"));
            }
        }
        // An initial usually stands for the father: 'RAMESH B' vs 'RAMESH S/O KRISHNA'.
        Person[][] orders = {{p, q}, {q, p}};
        for (Person[] xy : orders) {
            Person x = xy[0];
            Person y = xy[1];
            if (!kind(y.relation).equals("parent") || y.relative.isEmpty() || !x.relative.isEmpty()) {
                continue;
            }
            List<String> father = new ArrayList<>();
            for (Token t : y.relative) {
                if (!t.initial) {
                    father.add(t.text);
                }
            }
            Set<String> own = new TreeSet<>(x.initials());
            own.removeAll(y.initials());
            if (!father.isEmpty() && !own.isEmpty()) {
                Set<String> fits = Phonetic.initialOf(father.get(0));
                boolean any = false;
                for (String i : own) {
                    any |= fits.contains(i);
                }
                if (!any) {
                    return new Scored(score * 0.75, plus(reasons,
                        "initials " + String.join(" ", own).toUpperCase(Locale.ROOT) + " do not fit father " + father.get(0)));
                }
            }
        }
        return new Scored(score, reasons);
    }

    private static List<List<Token>> variants(Person p) {
        List<List<Token>> out = new ArrayList<>();
        out.add(p.tokens);
        out.addAll(p.aliases);
        return out;
    }

    static Scored personScore(Person p, Person q) {
        Scored first = personScore(p, q, false);
        // A pair the rules call different gets a second look allowing one-letter slips in short names
        // (Praveen / Parvin, Manish / Munish). Such a pair goes to an officer, never to acceptance, and
        // a pair the rules already score 0.35 or more is left exactly as it was.
        if (Switches.NEAR_MISS && first.score < 0.35) {
            Scored second = personScore(p, q, true);
            double s2 = Math.min(second.score, NEAR_CAP);
            boolean slipped = false;
            for (String r : second.reasons) {
                slipped |= r.contains("one letter apart");
            }
            if (s2 > first.score && slipped) {
                return new Scored(s2, plus(second.reasons, "one-letter slip: needs a check"));
            }
            boolean vowels = false;
            for (String r : second.reasons) {
                vowels |= r.contains("vowels differ across scripts");
            }
            if (s2 > first.score && vowels) {
                return new Scored(s2, plus(second.reasons, "spelling across scripts: needs a check"));
            }
        }
        return first;
    }

    private static Scored personScore(Person p, Person q, boolean near) {
        Scored best = null;
        for (List<Token> ta : variants(p)) {
            for (List<Token> tb : variants(q)) {
                Scored s = scoreTokens(ta, tb, p.relative, q.relative, near, p.gender, q.gender);
                if (best == null || s.score > best.score) {
                    best = s;
                }
            }
        }
        Scored r = relatives(p, q, best.score, best.reasons);
        double score = r.score;
        List<String> reasons = r.reasons;
        if (Switches.FIRM_CAP && p.firm != q.firm && score > 0.6) {
            score = 0.6;
            reasons = plus(reasons, "M/s firm named after a person");
        }
        if (!p.gender.isEmpty() && !q.gender.isEmpty() && !p.gender.equals(q.gender) && score > 0.35) {
            score = 0.35;
            reasons = plus(reasons, "opposite honorific/relation gender");
        }
        return new Scored(score, reasons);
    }

    static Scored orgScore(Organisation o, Organisation r) {
        List<Token> a = new ArrayList<>();
        for (String t : o.tokens) {
            a.add(new Token(t, false));
        }
        List<Token> b = new ArrayList<>();
        for (String t : r.tokens) {
            b.add(new Token(t, false));
        }
        return scoreTokens(a, b, List.of(), List.of(), false);
    }

    /** A person or an organisation, in the order Python's _entities lists them. */
    private static List<Object> entities(ParsedName p) {
        List<Object> out = new ArrayList<>(p.persons);
        out.addAll(p.orgs);
        return out;
    }

    private static Scored pairScore(Object ea, Object eb) {
        boolean pa = ea instanceof Person;
        boolean pb = eb instanceof Person;
        if (pa != pb) {
            return new Scored(0.0, List.of("person vs organisation"));
        }
        if (pa) {
            return personScore((Person) ea, (Person) eb);
        }
        return orgScore((Organisation) ea, (Organisation) eb);
    }

    private static List<OwnerRow> ownerRows(List<Object> x, List<Object> y, double[][] scores, boolean transpose) {
        List<OwnerRow> rows = new ArrayList<>();
        for (int i = 0; i < x.size(); i++) {
            Integer bestJ = null;
            double best = 0.0;
            for (int j = 0; j < y.size(); j++) {
                double s = transpose ? scores[j][i] : scores[i][j];
                if (bestJ == null || s > best) {
                    bestJ = j;
                    best = s;
                }
            }
            rows.add(new OwnerRow(x.get(i).toString(), bestJ == null ? null : y.get(bestJ).toString(),
                Py.round(Math.min(best, 1.0), 3)));
        }
        return Collections.unmodifiableList(rows);
    }

    static MatchResult match(ParsedName pa, ParsedName pb, OwnerMode owners) {
        if (pa.placeholder || pb.placeholder) {
            return new MatchResult(0.0, List.of("placeholder name"), pa.raw, pb.raw, owners, false, List.of(), List.of());
        }
        if (pa.empty() || pb.empty()) {
            return new MatchResult(0.0, List.of("no name to compare"), pa.raw, pb.raw, owners, false, List.of(), List.of());
        }
        List<Object> entsA = entities(pa);
        List<Object> entsB = entities(pb);
        Scored[][] detail = new Scored[entsA.size()][entsB.size()];
        double[][] scores = new double[entsA.size()][entsB.size()];
        for (int i = 0; i < entsA.size(); i++) {
            for (int j = 0; j < entsB.size(); j++) {
                detail[i][j] = pairScore(entsA.get(i), entsB.get(j));
                scores[i][j] = Math.min(detail[i][j].score, 1.0);
            }
        }
        List<OwnerRow> rowsA = ownerRows(entsA, entsB, scores, false);
        List<OwnerRow> rowsB = ownerRows(entsB, entsA, scores, true);
        // Only meaningful with several owners on a side: one owner against one is just the score itself.
        boolean partial = false;
        if (rowsA.size() + rowsB.size() > 2) {
            for (OwnerRow r : rowsA) {
                partial |= r.score() < Band.SAME.floor();
            }
            for (OwnerRow r : rowsB) {
                partial |= r.score() < Band.SAME.floor();
            }
        }
        Builder out = new Builder(pa, pb, entsA, entsB, detail, owners, partial, rowsA, rowsB);

        if (owners == OwnerMode.ANY) {
            int bi = 0;
            int bj = 0;
            for (int i = 0; i < entsA.size(); i++) {
                for (int j = 0; j < entsB.size(); j++) {
                    if (scores[i][j] > scores[bi][bj]) {
                        bi = i;
                        bj = j;
                    }
                }
            }
            return out.result(bi, bj, scores[bi][bj], List.of());   // a zero keeps the pair's own reason (gender, company)
        }

        if (owners == OwnerMode.ALL_A) {
            // The weakest owner of A, each taking its best counterpart in B.
            int wi = 0;
            double weakest = Double.NaN;
            for (int i = 0; i < entsA.size(); i++) {
                double best = scores[i][0];
                for (int j = 1; j < entsB.size(); j++) {
                    best = Math.max(best, scores[i][j]);
                }
                if (i == 0 || best < weakest) {
                    wi = i;
                    weakest = best;
                }
            }
            int bj = 0;
            for (int j = 1; j < entsB.size(); j++) {
                if (scores[wi][j] > scores[wi][bj]) {
                    bj = j;
                }
            }
            return out.result(wi, bj, scores[wi][bj],
                entsA.size() > 1 ? List.of("weakest of " + entsA.size() + " owner(s) in A") : List.of());
        }

        // ALL: pair owners one-to-one, strongest pairs first; an owner left over on either side scores 0.
        List<double[]> pairs = new ArrayList<>();
        for (int i = 0; i < entsA.size(); i++) {
            for (int j = 0; j < entsB.size(); j++) {
                pairs.add(new double[] {scores[i][j], i, j});
            }
        }
        pairs.sort((x, y) -> x[0] != y[0] ? Double.compare(y[0], x[0]) : x[1] != y[1] ? Double.compare(y[1], x[1])
            : Double.compare(y[2], x[2]));
        Set<Integer> usedA = new HashSet<>();
        Set<Integer> usedB = new HashSet<>();
        List<double[]> chosen = new ArrayList<>();
        for (double[] p : pairs) {
            int i = (int) p[1];
            int j = (int) p[2];
            if (!usedA.contains(i) && !usedB.contains(j)) {
                usedA.add(i);
                usedB.add(j);
                chosen.add(p);
            }
        }
        List<String> missing = new ArrayList<>();
        for (int k = 0; k < entsA.size(); k++) {
            if (!usedA.contains(k)) {
                missing.add("no counterpart in B for " + entsA.get(k));
            }
        }
        for (int k = 0; k < entsB.size(); k++) {
            if (!usedB.contains(k)) {
                missing.add("no counterpart in A for " + entsB.get(k));
            }
        }
        if (!missing.isEmpty()) {
            return out.result(null, null, 0.0, missing);
        }
        double[] weakest = chosen.get(0);
        for (double[] c : chosen) {
            if (c[0] < weakest[0] || (c[0] == weakest[0] && (c[1] < weakest[1] || (c[1] == weakest[1] && c[2] < weakest[2])))) {
                weakest = c;
            }
        }
        return out.result((int) weakest[1], (int) weakest[2], weakest[0],
            chosen.size() > 1 ? List.of("weakest of " + chosen.size() + " owner pair(s)") : List.of());
    }

    private static final class Builder {
        final ParsedName pa;
        final ParsedName pb;
        final List<Object> entsA;
        final List<Object> entsB;
        final Scored[][] detail;
        final OwnerMode owners;
        final boolean partial;
        final List<OwnerRow> rowsA;
        final List<OwnerRow> rowsB;

        Builder(ParsedName pa, ParsedName pb, List<Object> entsA, List<Object> entsB, Scored[][] detail, OwnerMode owners,
                boolean partial, List<OwnerRow> rowsA, List<OwnerRow> rowsB) {
            this.pa = pa;
            this.pb = pb;
            this.entsA = entsA;
            this.entsB = entsB;
            this.detail = detail;
            this.owners = owners;
            this.partial = partial;
            this.rowsA = rowsA;
            this.rowsB = rowsB;
        }

        MatchResult result(Integer i, Integer j, double score, List<String> extra) {
            List<String> reasons = new ArrayList<>();
            if (i != null) {
                List<String> own = detail[i][j].reasons;
                if (!own.isEmpty()) {
                    reasons.addAll(own);
                } else if (score == 0) {
                    reasons.add("no part agrees");
                }
            }
            reasons.addAll(extra);
            String left = i != null ? entsA.get(i).toString() : pa.raw;
            String right = j != null ? entsB.get(j).toString() : pb.raw;
            return new MatchResult(Py.round(score, 3), reasons, left, right, owners, partial, rowsA, rowsB);
        }
    }
}
