package io.github.msinghal34.namematch;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import org.junit.jupiter.api.Test;

/** The public API on invented names. */
class NameMatchTest {

    @Test
    void sameNameWrittenDifferentlyIsAccepted() {
        MatchResult r = NameMatch.match("Sri. K. Ramesh Kumar S/o Krishnappa", "RAMESH KUMAR K");
        assertEquals(Band.SAME, r.band());
        assertTrue(r.isAccepted());
        assertTrue(r.score() >= 0.80);
    }

    @Test
    void oneLetterSlipGoesToReviewNeverAccepted() {
        MatchResult r = NameMatch.match("Praveen Kumar", "Parvin Kumar");
        assertEquals(0.64, r.score());
        assertEquals(Band.REVIEW, r.band());
        assertFalse(r.isAccepted());
        assertTrue(r.reasons().contains("one-letter slip: needs a check"));
    }

    @Test
    void differentPeopleAreDifferent() {
        MatchResult r = NameMatch.match("Ramesh Kumar", "Suresh Gowda");
        assertEquals(Band.DIFFERENT, r.band());
    }

    @Test
    void kannadaScriptIsRead() {
        assertEquals(Band.SAME, NameMatch.match("ಶ್ರೀ. ರಮೇಶ್ ಗೌಡ. ಬಿ.", "RAMESH GOWDA B").band());
    }

    @Test
    void ownerRowsShowEachOwnerAndTheirBestMatch() {
        MatchResult r = NameMatch.match("1.ANAND RAO 2.SAVITHA RAO W/o Anand Rao", "Sri Anand Rao");
        assertEquals(1.0, r.score());
        assertTrue(r.isPartial(), "Savitha has no counterpart");
        assertEquals(2, r.ownersA().size());
        assertEquals("anand rao", r.ownersA().get(0).owner());
        assertEquals("savitha rao (rel anand rao) [f]", r.ownersA().get(1).owner());
        assertEquals("anand rao", r.ownersA().get(1).bestMatch());
        assertTrue(r.ownersA().get(1).score() < 0.35);
        assertEquals(1, r.ownersB().size());
    }

    @Test
    void ownerModesDecideHowSeveralOwnersCombine() {
        String a = "Ramesh and Suresh";
        String b = "Ramesh";
        assertEquals(Band.SAME, NameMatch.match(a, b).band());
        assertEquals(Band.DIFFERENT, NameMatch.covers(a, b).band());
        assertEquals(Band.DIFFERENT, NameMatch.match(a, b, OwnerMode.ALL).band());
        assertEquals(Band.SAME, NameMatch.covers(b, a).band());
    }

    @Test
    void emptyAndPlaceholderNamesScoreZero() {
        assertEquals(0.0, NameMatch.match("", "Ramesh").score());
        assertEquals(0.0, NameMatch.match(null, "Ramesh").score());
        assertEquals(List.of("placeholder name"), NameMatch.match("Khali", "Ramesh").reasons());
        assertNull(null);
    }

    @Test
    void modesHaveThePythonIds() {
        assertEquals(OwnerMode.ALL_A, OwnerMode.fromId("all_a"));
        assertEquals("likely_same", Band.LIKELY_SAME.id());
        assertThrows(IllegalArgumentException.class, () -> OwnerMode.fromId("some"));
        assertThrows(IllegalArgumentException.class, () -> NameMatch.match("a", "b", null));
    }

    @Test
    void resultsAreImmutable() {
        MatchResult r = NameMatch.match("Ramesh Kumr", "Ramesh Kumar");
        assertThrows(UnsupportedOperationException.class, () -> r.reasons().add("x"));
        assertThrows(UnsupportedOperationException.class, () -> r.ownersA().clear());
    }

    @Test
    void safeToCallFromManyThreads() throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(8);
        try {
            List<Future<Double>> results = new ArrayList<>();
            for (int i = 0; i < 400; i++) {
                String suffix = String.valueOf((char) ('a' + i % 26));
                results.add(pool.submit(() -> NameMatch.match("Venkatesh " + suffix, "Venkatesha " + suffix.toUpperCase()).score()));
            }
            for (Future<Double> f : results) {
                assertEquals(1.0, f.get(), 0.03);
            }
        } finally {
            pool.shutdown();
        }
    }

    @Test
    void kannadaAndEnglishSpellingsOfOneNameMatch() {
        assertTrue(NameMatch.match("PRAVEEN KUMAR", "ಪ್ರವೀಣ ಕುಮಾರ್").isAccepted());
        assertTrue(NameMatch.match("Y K HARIHARA RAO", "ವೈ ಕೆ ಹರಿಹರ ರಾವ್").isAccepted());
        assertTrue(NameMatch.match("Kಲಕ್ಷ್ಮಿ", "Smt K.Lakshmi").isAccepted());
    }

    @Test
    void differentNamesWithTheSameConsonantsGoToReviewNotAccept() {
        MatchResult r = NameMatch.match("KARTIK", "ಕೃತಿಕಾ");
        assertEquals(Band.REVIEW, r.band());
        assertTrue(r.reasons().contains("spelling across scripts: needs a check"));
    }

    @Test
    void oppositeGendersStayApartAcrossScripts() {
        assertEquals(Band.DIFFERENT, NameMatch.match("MUNIYAPPA", "ಮುನಿಯಮ್ಮ").band());
        assertEquals(Band.DIFFERENT, NameMatch.match("ADITI", "ಆದಿತ್ಯ").band());
        assertEquals(Band.DIFFERENT, NameMatch.match("SHIVALINGAMMA", "ಶಿವಲಿಂಗಮ್").band());
    }
}
