package br.edu.utfpr.javaenergy;

import com.sun.management.HotSpotDiagnosticMXBean;
import java.lang.management.ManagementFactory;
import java.util.LinkedHashMap;
import java.util.Map;

final class JvmIdentity {
    private JvmIdentity() { }

    static Map<String, Object> capture() {
        Map<String, Object> identity = new LinkedHashMap<>();
        identity.put("java_version", System.getProperty("java.version"));
        identity.put("java_runtime_version", System.getProperty("java.runtime.version"));
        identity.put("java_vendor", System.getProperty("java.vendor"));
        identity.put("java_home", System.getProperty("java.home"));
        identity.put("java_executable", ProcessHandle.current().info().command().orElse(null));
        identity.put("process_arguments", ProcessHandle.current().info().arguments().orElse(null));
        identity.put("vm_name", System.getProperty("java.vm.name"));
        identity.put("vm_version", System.getProperty("java.vm.version"));
        identity.put("vm_arguments", ManagementFactory.getRuntimeMXBean().getInputArguments());
        identity.put("java_feature", Runtime.version().feature());
        identity.put("pid", ProcessHandle.current().pid());
        identity.put("available_processors", Runtime.getRuntime().availableProcessors());
        identity.put("max_heap_bytes", Runtime.getRuntime().maxMemory());
        identity.put("os_name", System.getProperty("os.name"));
        identity.put("os_version", System.getProperty("os.version"));
        identity.put("os_arch", System.getProperty("os.arch"));
        identity.put("use_g1_gc", flag("UseG1GC"));
        identity.put("use_compact_object_headers", flag("UseCompactObjectHeaders"));
        return identity;
    }

    private static String flag(String name) {
        try {
            return ManagementFactory.getPlatformMXBean(HotSpotDiagnosticMXBean.class)
                    .getVMOption(name).getValue();
        } catch (IllegalArgumentException e) {
            return null; // The flag does not exist on older JVMs.
        }
    }

    static void requireConfiguration(String configuration, Map<String, Object> identity) {
        int feature = (int) identity.get("java_feature");
        int expected = switch (configuration) {
            case "A" -> 17;
            case "B" -> 21;
            case "C", "D" -> 25;
            default -> throw new IllegalArgumentException("study.configuration must be A, B, C or D");
        };
        if (feature != expected) throw new IllegalArgumentException("JDK does not match configuration");
        if (!"Eclipse Adoptium".equals(identity.get("java_vendor"))) {
            throw new IllegalArgumentException("Expected Eclipse Temurin (Eclipse Adoptium)");
        }
        if (!"true".equals(identity.get("use_g1_gc"))) {
            throw new IllegalArgumentException("Expected G1; use -XX:+UseG1GC");
        }
        if (feature == 25) {
            String expectedCompact = configuration.equals("D") ? "true" : "false";
            if (!expectedCompact.equals(identity.get("use_compact_object_headers"))) {
                throw new IllegalArgumentException("Compact object headers do not match configuration");
            }
        }
    }
}
