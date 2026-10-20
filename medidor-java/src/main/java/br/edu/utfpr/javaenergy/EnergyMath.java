package br.edu.utfpr.javaenergy;

import java.util.List;

/** Modular energy deltas with explicit assumptions about unobserved wraps. */
final class EnergyMath {
    record Result(long energyUj, long durationNanos, int wraps, long maximumGapNanos) {
        double energyJ() { return energyUj / 1_000_000.0; }
        double durationSeconds() { return durationNanos / 1_000_000_000.0; }
    }

    private EnergyMath() { }

    static Result summarize(List<RaplCounter.Reading> samples, long rangeUj,
                            long allowedGapNanos, double powerUpperBoundW) {
        if (samples.size() < 2 || rangeUj <= 0 || allowedGapNanos <= 0
                || !Double.isFinite(powerUpperBoundW) || powerUpperBoundW <= 0) {
            throw new IllegalArgumentException("Invalid samples or wrap guards");
        }
        long total = 0;
        long maxGap = 0;
        int wraps = 0;
        for (int i = 0; i < samples.size(); i++) {
            var current = samples.get(i);
            if (current.energyUj() < 0 || current.energyUj() >= rangeUj
                    || current.readDurationNanos() < 0) {
                throw new IllegalArgumentException("Invalid energy reading");
            }
            if (i == 0) continue;
            var previous = samples.get(i - 1);
            long gap = current.afterNanos() - previous.beforeNanos();
            if (current.beforeNanos() < previous.afterNanos() || gap <= 0
                    || gap > allowedGapNanos) {
                throw new IllegalArgumentException("Missing, delayed or unordered RAPL samples");
            }
            // At the declared power bound, this gap cannot conceal a complete wrap.
            // The bound is a recorded assumption, not an RAPL measurement or a TDP.
            double maximumEnergyUj = powerUpperBoundW * (gap / 1_000.0);
            if (maximumEnergyUj >= rangeUj) {
                throw new IllegalArgumentException("Sampling gap could conceal counter wraps");
            }
            long delta = current.energyUj() >= previous.energyUj()
                    ? current.energyUj() - previous.energyUj()
                    : rangeUj - previous.energyUj() + current.energyUj();
            // A counter reset often looks like an enormous modular increment.
            if (delta > maximumEnergyUj + 1_000_000.0) {
                throw new IllegalArgumentException("Energy increment exceeds declared power guard");
            }
            if (current.energyUj() < previous.energyUj()) wraps++;
            total = Math.addExact(total, delta);
            maxGap = Math.max(maxGap, gap);
        }
        long duration = samples.get(samples.size() - 1).midpointNanos()
                - samples.get(0).midpointNanos();
        if (duration <= 0) throw new IllegalArgumentException("Non-positive duration");
        if (total <= 0) throw new IllegalArgumentException("Counter did not advance");
        return new Result(total, duration, wraps, maxGap);
    }
}
