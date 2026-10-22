package br.edu.utfpr.javaenergy;

import org.dacapo.harness.Callback;
import org.dacapo.harness.CommandLineArgs;
import org.dacapo.harness.TestHarness;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

/** DaCapo 23.11-MR2 callback: the last k iterations are measured after explicit warmup. */
public final class EnergyCallback extends Callback {
    private final RunRecorder recorder;
    private EnergySampler sampler;
    private RaplCounter counter;
    private long sampleMillis;
    private long maxGapMillis;
    private double powerUpperBoundW;
    private int ordinal;
    private int measuredIterations;
    private boolean warmup;
    private volatile boolean waitingForValidation;
    private String application;
    private EnergySampler.Window window;
    private boolean finished;

    public EnergyCallback(CommandLineArgs args) {
        super(args);
        String output = System.getProperty("study.output");
        if (output == null || output.isBlank()) {
            throw new IllegalArgumentException("Required: -Dstudy.output=<new-directory>");
        }
        try {
            recorder = new RunRecorder(Path.of(output));
        } catch (IOException e) {
            throw new IllegalStateException("Cannot create a new result directory; never reuse one", e);
        }
        try {
            var identity = JvmIdentity.capture();
            String configuration = System.getProperty("study.configuration", "");
            recorder.create("jvm.json", identity);
            JvmIdentity.requireConfiguration(configuration, identity);
            if (!args.getValidate() || !args.getValidateOutput() || args.getIgnoreValidation()) {
                throw new IllegalArgumentException("DaCapo validation must remain enabled and mandatory");
            }
            if (args.getMethodology() != CommandLineArgs.Methodology.ITERATE
                    || args.getIterations() < 2 || args.getArgList().size() != 1) {
                throw new IllegalArgumentException("Use one benchmark and -n >= 2 (warmup plus one measured iteration)");
            }
            measuredIterations = Integer.parseInt(System.getProperty("study.measuredIterations", "1"));
            IterationPlan.require(args.getIterations(), measuredIterations);
            recorder.expectMeasured(measuredIterations);
            sampleMillis = Long.parseLong(System.getProperty("study.sampleMillis", "100"));
            maxGapMillis = Long.parseLong(System.getProperty("study.maxGapMillis", "10000"));
            powerUpperBoundW = Double.parseDouble(System.getProperty("study.powerUpperBoundW", "1000"));
            counter = new RaplCounter(Path.of(System.getProperty("study.raplDir",
                    "/sys/class/powercap/intel-rapl:0")));
            if (maxGapMillis <= sampleMillis || maxGapMillis > 60_000
                    || !Double.isFinite(powerUpperBoundW) || powerUpperBoundW <= 0
                    || powerUpperBoundW * maxGapMillis * 1_000.0 >= counter.rangeUj()) {
                throw new IllegalArgumentException("Unsafe sampling gap/power bound for this counter range");
            }
            Map<String, Object> metadata = new LinkedHashMap<>();
            metadata.put("schema_version", 1);
            metadata.put("run_id", System.getProperty("study.runId", UUID.randomUUID().toString()));
            metadata.put("category", System.getProperty("study.category", "integration"));
            metadata.put("session_id", System.getProperty("study.sessionId"));
            metadata.put("block_id", System.getProperty("study.blockId"));
            metadata.put("order", System.getProperty("study.order"));
            metadata.put("created_at_utc", Instant.now().toString());
            metadata.put("configuration", configuration);
            metadata.put("dacapo_build_version", TestHarness.getBuildVersion());
            // DaCapo's getArgs() returns positional benchmark names, not all CLI options.
            metadata.put("dacapo_benchmarks", args.getArgs());
            Map<String, Object> parameters = new LinkedHashMap<>();
            parameters.put("methodology", args.getMethodology().toString());
            parameters.put("iterations", args.getIterations());
            parameters.put("measured_iterations", measuredIterations);
            parameters.put("input_size", args.getSize());
            parameters.put("thread_count", args.getThreadCount());
            parameters.put("thread_factor", args.getThreadFactor());
            parameters.put("validation", args.getValidate());
            parameters.put("validate_output", args.getValidateOutput());
            parameters.put("ignore_validation_failure", args.getIgnoreValidation());
            parameters.put("scratch_directory", args.getScratchDir());
            parameters.put("watchdog_seconds", args.getWatchdog());
            metadata.put("dacapo_parameters", parameters);
            metadata.put("pre_iteration_gc", args.getPreIterationGC());
            metadata.put("dacapo_artifact", artifact(TestHarness.class));
            metadata.put("meter_artifact", artifact(EnergyCallback.class));
            metadata.put("rapl_domain", counter.domain());
            metadata.put("rapl_directory", counter.directory().toString());
            metadata.put("counter_range_uj", counter.rangeUj());
            metadata.put("sample_interval_ms", sampleMillis);
            metadata.put("max_allowed_gap_ms", maxGapMillis);
            metadata.put("assumed_power_upper_bound_w", powerUpperBoundW);
            metadata.put("increment_guard_slack_uj", 1_000_000);
            metadata.put("time_basis", "midpoints of monotonic timestamps bracketing the first and last RAPL reads");
            metadata.put("energy_scope", "processor package; includes concurrent activity, not the whole computer");
            metadata.put("process_exit_code", null);
            metadata.put("requires_external_exit_code_check", true);
            recorder.create("metadata.json", metadata);
            sampler = new EnergySampler(counter, sampleMillis);
            Runtime.getRuntime().addShutdownHook(new Thread(this::finish, "energy-recorder-shutdown"));
        } catch (Exception e) {
            recorder.fail("Preflight: " + e);
            recorder.finish();
            throw new IllegalStateException("Measurement preflight failed", e);
        }
    }

    private static Map<String, Object> artifact(Class<?> type) throws Exception {
        Path path = Path.of(type.getProtectionDomain().getCodeSource().getLocation().toURI());
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("path", path.toString());
        if (Files.isRegularFile(path)) {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            try (var input = Files.newInputStream(path)) {
                byte[] buffer = new byte[65_536];
                int count;
                while ((count = input.read(buffer)) >= 0) digest.update(buffer, 0, count);
            }
            result.put("sha256", HexFormat.of().formatHex(digest.digest()));
            result.put("size_bytes", Files.size(path));
        } else {
            result.put("sha256", null);
            result.put("kind", "development_classes");
        }
        return result;
    }

    @Override
    public void start(String benchmark) {
        if (waitingForValidation || (application != null && !application.equals(benchmark))) {
            recorder.fail("Overlapping iterations or multiple benchmarks in one JVM");
            throw new IllegalStateException("Unsupported benchmark sequence");
        }
        super.start(benchmark); // DaCapo console output precedes our first energy read.
        application = benchmark;
        ordinal++;
        // The last k iterations are measured; DaCapo's own isWarmup() only marks the final one.
        warmup = !IterationPlan.isMeasured(ordinal, args.getIterations(), measuredIterations);
        window = null;
        waitingForValidation = true;
        recorder.create("iteration-" + ordinal + ".started.json", Map.of(
                "application", benchmark, "ordinal", ordinal, "warmup", warmup,
                "created_at_utc", Instant.now().toString()));
        if (!warmup) {
            try {
                sampler.start();
            } catch (IOException e) {
                recorder.fail("Start energy read: " + e);
                throw new IllegalStateException("Cannot begin energy measurement", e);
            }
        }
    }

    @Override
    public void stop(long duration) {
        if (!warmup) window = sampler.stop(); // Last read before persistence and validation.
        super.stop(duration);
    }

    @Override
    public void complete(String benchmark, boolean valid) {
        Map<String, Object> record = new LinkedHashMap<>();
        record.put("schema_version", 1);
        record.put("application", benchmark);
        record.put("ordinal", ordinal);
        record.put("warmup", warmup);
        record.put("input_size", args.getSize());
        record.put("threads_argument", args.getThreadCount());
        record.put("dacapo_valid", valid);
        record.put("dacapo_duration_ms", elapsed);
        record.put("energy_j", null);
        record.put("time_s", null);
        String failure = valid ? null : "DaCapo validation failed";
        if (!warmup) {
            if (window == null) {
                failure = "Missing stop boundary";
            } else {
                String sampleFile = "iteration-" + ordinal + ".samples.json";
                var samples = window.readings().stream().map(r -> new long[]{
                        r.energyUj(), r.beforeNanos(), r.afterNanos()}).toList();
                recorder.create(sampleFile, Map.of("columns",
                        new String[]{"energy_uj", "before_nanos", "after_nanos"}, "samples", samples));
                record.put("samples_file", sampleFile);
                record.put("sample_count", samples.size());
                if (window.failure() != null) failure = window.failure();
                try {
                    var result = EnergyMath.summarize(window.readings(), counter.rangeUj(),
                            Math.multiplyExact(maxGapMillis, 1_000_000), powerUpperBoundW);
                    record.put("counter_wraps", result.wraps());
                    record.put("max_gap_nanos", result.maximumGapNanos());
                    record.put("first_read_duration_nanos", window.readings().get(0).readDurationNanos());
                    record.put("last_read_duration_nanos", window.readings().get(samples.size() - 1).readDurationNanos());
                    if (failure == null) {
                        record.put("energy_j", result.energyJ());
                        record.put("time_s", result.durationSeconds());
                    }
                } catch (RuntimeException e) {
                    failure = "Energy calculation: " + e;
                }
            }
        }
        record.put("status", failure == null ? warmup ? "warmup_valid" : "measurement_valid" : "failure");
        record.put("failure", failure);
        recorder.iteration(record, failure == null, warmup);
        waitingForValidation = false;
        super.complete(benchmark, valid);
        if (failure != null) {
            recorder.fail(failure);
            throw new IllegalStateException("Invalid measurement: " + failure);
        }
    }

    private synchronized void finish() {
        if (finished) return;
        finished = true;
        try {
            if (waitingForValidation) recorder.fail("Process ended before iteration validation");
            if (sampler != null && sampler.isActive()) {
                var partial = sampler.stop();
                recorder.create("interrupted.samples.json", Map.of("samples", partial.readings().stream()
                        .map(r -> new long[]{r.energyUj(), r.beforeNanos(), r.afterNanos()}).toList()));
                recorder.fail("Process ended during measured iteration");
            }
            recorder.finish();
        } finally {
            if (sampler != null) sampler.close();
        }
    }
}
