package br.edu.utfpr.javaenergy;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.FileAlreadyExistsException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;
import static org.junit.jupiter.api.Assertions.*;

class RecorderTest {
    @TempDir Path temporary;

    @Test void refusesExistingOutputSoPreviousMeasurementsArePreserved() throws Exception {
        Path output = temporary.resolve("run");
        var recorder = new RunRecorder(output);
        recorder.create("original.json", Map.of("value", 17));
        assertThrows(FileAlreadyExistsException.class, () -> new RunRecorder(output));
        assertEquals("{\"value\":17}\n", Files.readString(output.resolve("original.json")));
    }

    @Test void marksIncompleteProcessAsFailure() throws Exception {
        Path output = temporary.resolve("run");
        var recorder = new RunRecorder(output);
        recorder.finish();
        assertTrue(Files.readString(output.resolve("summary.json")).contains("\"status\":\"failure\""));
    }

    @Test void warmupIsNotCountedAsAnIndependentMeasurement() throws Exception {
        Path output = temporary.resolve("run");
        var recorder = new RunRecorder(output);
        recorder.iteration(Map.of("application", "pmd", "warmup", true), true, true);
        recorder.finish();
        assertTrue(Files.readString(output.resolve("summary.json")).contains("\"measured_iterations\":0"));
        assertTrue(Files.readString(output.resolve("summary.json")).contains("\"status\":\"failure\""));
    }

    @Test void preservesWarmupFailureEvenIfAMeasuredIterationFollows() throws Exception {
        Path output = temporary.resolve("run");
        var recorder = new RunRecorder(output);
        recorder.iteration(Map.of("application", "pmd", "warmup", true), false, true);
        recorder.iteration(Map.of("application", "pmd", "warmup", false), true, false);
        recorder.finish();
        assertTrue(Files.readString(output.resolve("summary.json")).contains("\"status\":\"failure\""));
    }

    @Test void distinguishesValidMeasurementFromExternalProcessExitCheck() throws Exception {
        Path output = temporary.resolve("run");
        var recorder = new RunRecorder(output);
        recorder.iteration(Map.of("application", "pmd", "warmup", false), true, false);
        recorder.finish();
        String summary = Files.readString(output.resolve("summary.json"));
        assertTrue(summary.contains("\"status\":\"measurement_valid\""));
        assertTrue(summary.contains("\"requires_external_exit_code_check\":true"));
    }

    @Test void encodesControlCharactersNullAndUnicodeWithoutInvalidJsonNumbers() {
        var record = new LinkedHashMap<String, Object>();
        record.put("text", "linha\n\"\\\t\u0001á😀");
        record.put("missing", null);
        assertEquals("{\"text\":\"linha\\n\\\"\\\\\\t\\u0001á\\ud83d\\ude00\",\"missing\":null}", Json.encode(record));
        assertThrows(IllegalArgumentException.class, () -> Json.encode(Double.NaN));
    }
}
