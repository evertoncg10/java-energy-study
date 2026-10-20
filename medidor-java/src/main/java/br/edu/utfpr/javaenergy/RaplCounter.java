package br.edu.utfpr.javaenergy;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

/** Reads exactly one RAPL package domain, without adding its subdomains. */
final class RaplCounter {
    record Reading(long energyUj, long beforeNanos, long afterNanos) {
        long midpointNanos() { return beforeNanos + (afterNanos - beforeNanos) / 2; }
        long readDurationNanos() { return afterNanos - beforeNanos; }
    }

    private final Path directory;
    private final String domain;
    private final long rangeUj;

    RaplCounter(Path directory) throws IOException {
        this.directory = directory.toRealPath();
        domain = Files.readString(this.directory.resolve("name")).trim();
        if (!domain.matches("package-\\d+")) {
            throw new IOException("Expected a package domain, got: " + domain);
        }
        rangeUj = readLong("max_energy_range_uj");
        if (rangeUj <= 0) throw new IOException("Invalid RAPL counter range");
        read(); // Fail before the workload if access is denied.
    }

    Reading read() throws IOException {
        long before = System.nanoTime();
        long energy = readLong("energy_uj");
        long after = System.nanoTime();
        if (energy < 0 || energy >= rangeUj) {
            throw new IOException("RAPL reading outside [0, max_energy_range_uj)");
        }
        return new Reading(energy, before, after);
    }

    private long readLong(String name) throws IOException {
        try {
            return Long.parseLong(Files.readString(directory.resolve(name)).trim());
        } catch (NumberFormatException e) {
            throw new IOException("Invalid integer in " + name, e);
        }
    }

    Path directory() { return directory; }
    String domain() { return domain; }
    long rangeUj() { return rangeUj; }
}
