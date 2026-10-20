package br.edu.utfpr.javaenergy;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import static org.junit.jupiter.api.Assertions.*;

class RaplCounterTest {
    @TempDir Path directory;

    private void fixture(String domain, String energy) throws IOException {
        Files.writeString(directory.resolve("name"), domain);
        Files.writeString(directory.resolve("max_energy_range_uj"), "1000000000\n");
        Files.writeString(directory.resolve("energy_uj"), energy);
    }

    @Test void readsOnePackageAndBracketsTheRead() throws Exception {
        fixture("package-0\n", "1234567\n");
        var counter = new RaplCounter(directory);
        var reading = counter.read();
        assertEquals("package-0", counter.domain());
        assertEquals(1234567, reading.energyUj());
        assertTrue(reading.afterNanos() >= reading.beforeNanos());
        assertEquals(1_000_000_000, counter.rangeUj());
    }

    @Test void refusesSubdomains() throws Exception {
        fixture("core\n", "1234567\n");
        assertThrows(IOException.class, () -> new RaplCounter(directory));
    }

    @Test void refusesMissingCounter() throws Exception {
        fixture("package-0\n", "1\n");
        Files.delete(directory.resolve("energy_uj"));
        assertThrows(IOException.class, () -> new RaplCounter(directory));
    }

    @Test void refusesMalformedOrOutOfRangeCounter() throws Exception {
        fixture("package-0\n", "not-a-number\n");
        assertThrows(IOException.class, () -> new RaplCounter(directory));
        Files.writeString(directory.resolve("energy_uj"), "1000000000\n");
        assertThrows(IOException.class, () -> new RaplCounter(directory));
    }
}
