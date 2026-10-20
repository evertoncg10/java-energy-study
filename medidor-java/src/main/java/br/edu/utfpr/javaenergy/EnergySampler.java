package br.edu.utfpr.javaenergy;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/** Samples in memory. Result-file writes happen only outside the measured window. */
final class EnergySampler implements AutoCloseable {
    record Window(List<RaplCounter.Reading> readings, String failure) { }
    private final RaplCounter counter;
    private final ScheduledExecutorService executor;
    private final List<RaplCounter.Reading> readings = new ArrayList<>();
    private boolean active;
    private String failure;

    EnergySampler(RaplCounter counter, long intervalMillis) {
        if (intervalMillis < 10 || intervalMillis > 1_000) {
            throw new IllegalArgumentException("study.sampleMillis must be between 10 and 1000");
        }
        this.counter = counter;
        executor = Executors.newSingleThreadScheduledExecutor(task -> {
            Thread thread = new Thread(task, "rapl-sampler");
            thread.setDaemon(true);
            return thread;
        });
        executor.scheduleWithFixedDelay(this::sample, intervalMillis, intervalMillis, TimeUnit.MILLISECONDS);
    }

    synchronized void start() throws IOException {
        if (active) throw new IllegalStateException("Measurement already active");
        readings.clear();
        failure = null;
        readings.add(counter.read());
        active = true;
    }

    private synchronized void sample() {
        if (!active || failure != null) return;
        try {
            if (readings.size() >= 1_000_000) throw new IOException("Sample limit exceeded");
            readings.add(counter.read());
        } catch (IOException | RuntimeException e) {
            failure = e.toString();
        }
    }

    synchronized Window stop() {
        if (!active) throw new IllegalStateException("Measurement not active");
        sample();
        active = false;
        return new Window(List.copyOf(readings), failure);
    }

    synchronized boolean isActive() { return active; }

    @Override
    public void close() {
        executor.shutdownNow();
    }
}
