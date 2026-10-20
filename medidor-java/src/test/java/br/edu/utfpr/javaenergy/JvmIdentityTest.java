package br.edu.utfpr.javaenergy;

import org.junit.jupiter.api.Test;
import java.util.LinkedHashMap;
import static org.junit.jupiter.api.Assertions.*;

class JvmIdentityTest {
    private LinkedHashMap<String, Object> fixture(int feature, String compact) {
        var identity = new LinkedHashMap<String, Object>();
        identity.put("java_feature", feature);
        identity.put("java_vendor", "Eclipse Adoptium");
        identity.put("use_g1_gc", "true");
        identity.put("use_compact_object_headers", compact);
        return identity;
    }

    @Test void capturesTheActualProcessRatherThanOnlyTheShellVersion() {
        var identity = JvmIdentity.capture();
        assertEquals(Runtime.version().feature(), identity.get("java_feature"));
        assertEquals(ProcessHandle.current().pid(), identity.get("pid"));
        assertNotNull(identity.get("java_executable"));
        assertTrue(identity.containsKey("process_arguments"));
        assertNotNull(identity.get("vm_arguments"));
    }

    @Test void refusesWrongJavaVersionAndWrongCompactHeadersSetting() {
        assertThrows(IllegalArgumentException.class, () -> JvmIdentity.requireConfiguration("A", fixture(25, "false")));
        assertThrows(IllegalArgumentException.class, () -> JvmIdentity.requireConfiguration("D", fixture(25, "false")));
        assertDoesNotThrow(() -> JvmIdentity.requireConfiguration("C", fixture(25, "false")));
        assertDoesNotThrow(() -> JvmIdentity.requireConfiguration("D", fixture(25, "true")));
        assertDoesNotThrow(() -> JvmIdentity.requireConfiguration("A", fixture(17, null)));
    }
}
