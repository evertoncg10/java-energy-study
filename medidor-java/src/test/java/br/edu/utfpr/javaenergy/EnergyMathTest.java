package br.edu.utfpr.javaenergy;

import org.junit.jupiter.api.Test;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;

class EnergyMathTest {
    private static RaplCounter.Reading sample(long energyUj, long timeNanos) {
        return new RaplCounter.Reading(energyUj, timeNanos, timeNanos + 10_000);
    }

    @Test void convertsMicrojoulesAndMonotonicNanoseconds() {
        var result = EnergyMath.summarize(List.of(sample(2_000_000, 0),
                sample(5_000_000, 100_000_000)), 100_000_000, 200_000_000, 500);
        assertEquals(3.0, result.energyJ());
        assertEquals(0.1, result.durationSeconds(), 1e-12);
        assertEquals(0, result.wraps());
    }

    @Test void accumulatesSeveralWrapsAcrossIntermediateReadings() {
        var result = EnergyMath.summarize(List.of(sample(90_000_000, 0),
                sample(10_000_000, 150_000_000), sample(90_000_000, 300_000_000),
                sample(20_000_000, 450_000_000)), 100_000_000, 200_000_000, 600);
        assertEquals(130.0, result.energyJ());
        assertEquals(2, result.wraps());
        assertEquals(0.45, result.durationSeconds(), 1e-12);
    }

    @Test void refusesASamplingGapThatCouldHideACompleteWrap() {
        assertThrows(IllegalArgumentException.class, () -> EnergyMath.summarize(
                List.of(sample(20_000_000, 0), sample(30_000_000, 1_000_000_000)),
                100_000_000, 2_000_000_000, 500));
    }

    @Test void refusesExcessivelyDelayedSampler() {
        assertThrows(IllegalArgumentException.class, () -> EnergyMath.summarize(
                List.of(sample(20_000_000, 0), sample(30_000_000, 300_000_000)),
                1_000_000_000, 200_000_000, 500));
    }

    @Test void refusesAnApparentResetThatWouldImplyAnImpossibleIncrement() {
        assertThrows(IllegalArgumentException.class, () -> EnergyMath.summarize(
                List.of(sample(100_000_000, 0), sample(1, 100_000_000)),
                262_143_328_850L, 200_000_000, 1_000));
    }

    @Test void refusesUnorderedOrOverlappingReads() {
        assertThrows(IllegalArgumentException.class, () -> EnergyMath.summarize(
                List.of(sample(10, 100_000_000), sample(20, 0)),
                100_000_000, 200_000_000, 500));
    }

    @Test void refusesCounterOutsideItsRange() {
        assertThrows(IllegalArgumentException.class, () -> EnergyMath.summarize(
                List.of(sample(100_000_000, 0), sample(20, 100_000_000)),
                100_000_000, 200_000_000, 500));
    }

    @Test void refusesNonAdvancingCounter() {
        assertThrows(IllegalArgumentException.class, () -> EnergyMath.summarize(
                List.of(sample(20, 0), sample(20, 100_000_000)),
                100_000_000, 200_000_000, 500));
    }

    @Test void refusesMissingBoundaries() {
        assertThrows(IllegalArgumentException.class, () -> EnergyMath.summarize(
                List.of(sample(20, 0)), 100_000_000, 200_000_000, 500));
    }
}
