from pae_analise.gclog import parse_gc_text

LOG = """[0.003s][info][gc] Using G1
[1.286s][info][gc] GC(0) Pause Young (Normal) (G1 Evacuation Pause) 51M->2M(1024M) 2.685ms
[1.349s][info][gc] GC(2) Pause Full (System.gc()) 37M->3M(1024M) 4.064ms
[2.000s][info][gc] GC(3) Pause Young (Concurrent Start) (Metadata GC Threshold) 100M->20M(1024M) 1.000ms
[2.100s][info][gc] GC(4) Concurrent Mark Cycle
[2.200s][info][gc] GC(4) Pause Remark 30M->30M(1024M) 0.500ms
[2.300s][info][gc] GC(4) Pause Cleanup 30M->30M(1024M) 0.100ms
[2.400s][info][gc] GC(4) Concurrent Mark Cycle 30.000ms
[3.000s][info][gc] GC(5) Pause Young (Normal) (G1 Evacuation Pause) (Evacuation Failure: Pinned) 2048K->1024K(1G) 0.200ms
"""


def test_counts_every_pause_line_and_ignores_concurrent_lines() -> None:
    summary = parse_gc_text(LOG)
    assert summary.uses_g1
    assert summary.pauses == 6
    assert (summary.young_pauses, summary.full_pauses, summary.other_pauses) == (3, 1, 2)
    assert summary.unparsed_pause_lines == 0


def test_pause_time_is_the_sum_of_pause_lines() -> None:
    assert abs(parse_gc_text(LOG).pause_time_ms - 8.549) < 1e-9


def test_heap_after_is_the_median_after_the_arrow_in_mb() -> None:
    # Valores depois da seta: 2, 3, 20, 30, 30 e 1 MB (1024K) -> mediana 11,5.
    assert parse_gc_text(LOG).heap_after_median_mb == 11.5


def test_flags_pause_lines_out_of_format() -> None:
    summary = parse_gc_text("[1s][info][gc] GC(1) Pause Young something unexpected\n")
    assert summary.pauses == 0
    assert summary.unparsed_pause_lines == 1
    assert summary.heap_after_median_mb is None
