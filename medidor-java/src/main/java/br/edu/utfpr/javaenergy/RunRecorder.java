package br.edu.utfpr.javaenergy;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;

/** One new directory per JVM process. Existing results are never overwritten. */
final class RunRecorder {
    private final Path directory;
    private boolean failed;
    private String failure;
    private int measured;
    private String application;

    RunRecorder(Path directory) throws IOException {
        this.directory = directory.toAbsolutePath();
        Files.createDirectories(this.directory.getParent());
        Files.createDirectory(this.directory);
    }

    synchronized void create(String name, Object value) {
        try {
            Files.writeString(directory.resolve(name), Json.encode(value) + "\n", StandardCharsets.UTF_8,
                    StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    synchronized void iteration(Map<String, Object> record, boolean valid, boolean warmup) {
        if (!valid) fail(String.valueOf(record.getOrDefault("failure", "Invalid DaCapo iteration or measurement")));
        if (!warmup) measured++;
        application = record.get("application").toString();
        try {
            Files.writeString(directory.resolve("iterations.jsonl"), Json.encode(record) + "\n",
                    StandardCharsets.UTF_8, StandardOpenOption.CREATE, StandardOpenOption.APPEND);
        } catch (IOException e) {
            fail("Could not persist iteration: " + e);
            throw new UncheckedIOException(e);
        }
    }

    synchronized void fail(String reason) {
        failed = true;
        if (failure == null) failure = reason;
    }

    synchronized void finish() {
        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("schema_version", 1);
        summary.put("finished_at_utc", Instant.now().toString());
        summary.put("application", application);
        summary.put("measured_iterations", measured);
        summary.put("status", !failed && measured == 1 ? "measurement_valid" : "failure");
        summary.put("requires_external_exit_code_check", true);
        summary.put("failure", failure != null ? failure : measured != 1 ? "Expected exactly one measured iteration" : null);
        try {
            Path temp = directory.resolve("summary.json.tmp");
            Files.writeString(temp, Json.encode(summary) + "\n", StandardCharsets.UTF_8);
            Files.move(temp, directory.resolve("summary.json"), StandardCopyOption.REPLACE_EXISTING,
                    StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }
}
