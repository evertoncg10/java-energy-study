package br.edu.utfpr.javaenergy;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class IterationPlanTest {
    @Test void defaultMeasuresOnlyTheLastIteration() {
        assertFalse(IterationPlan.isMeasured(3, 4, 1));
        assertTrue(IterationPlan.isMeasured(4, 4, 1));
    }

    @Test void measuresTheLastThreeAfterWarmup() {
        boolean[] measured = new boolean[15];
        for (int i = 1; i <= 15; i++) measured[i - 1] = IterationPlan.isMeasured(i, 15, 3);
        for (int i = 0; i < 12; i++) assertFalse(measured[i], "warmup " + (i + 1));
        for (int i = 12; i < 15; i++) assertTrue(measured[i], "measured " + (i + 1));
    }

    @Test void requiresAtLeastOneWarmup() {
        assertThrows(IllegalArgumentException.class, () -> IterationPlan.require(3, 3));
        assertThrows(IllegalArgumentException.class, () -> IterationPlan.require(4, 0));
        assertThrows(IllegalArgumentException.class, () -> IterationPlan.require(20, 11));
        assertDoesNotThrow(() -> IterationPlan.require(4, 3));
    }

    @Test void rejectsIterationOutsideTheRequestedCount() {
        assertThrows(IllegalArgumentException.class, () -> IterationPlan.isMeasured(0, 4, 1));
        assertThrows(IllegalArgumentException.class, () -> IterationPlan.isMeasured(5, 4, 1));
    }
}
