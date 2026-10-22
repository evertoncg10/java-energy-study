package br.edu.utfpr.javaenergy;

/** Which DaCapo iterations of one JVM process are measured: always the last k. */
final class IterationPlan {
    static final int MAX_MEASURED = 10;

    private IterationPlan() { }

    static void require(int iterations, int measured) {
        if (measured < 1 || measured > MAX_MEASURED || iterations - measured < 1) {
            throw new IllegalArgumentException(
                    "study.measuredIterations must be 1.." + MAX_MEASURED + " and leave at least one warmup");
        }
    }

    /** ordinal is 1-based, as DaCapo counts iterations. */
    static boolean isMeasured(int ordinal, int iterations, int measured) {
        require(iterations, measured);
        if (ordinal < 1 || ordinal > iterations) throw new IllegalArgumentException("Iteration outside -n");
        return ordinal > iterations - measured;
    }
}
