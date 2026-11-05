# PAE-JVM Data Dictionary

🇺🇸 English | Back to the [README (English)](README.en.md) · [README (Português)](README.md)

This document describes every column of the result tables and the main fields of the raw data files, so that the data
can be read and reused without knowing Portuguese. Column and field names are already in English. Some **values**
are in Portuguese, and each of them is translated here.

All results files live in [`resultados/oficial-20261101-termos/`](resultados/oficial-20261101-termos/), the folder that
should be used for any new work. The raw data live in `dados/brutos/<session>/`, one folder per process.

---

## Contents

- [Common values](#common-values)
- [base-oficial.csv and base-pilotos.csv (one row per process)](#base-oficialcsv-and-base-pilotoscsv-one-row-per-process)
- [descritiva.csv (descriptive statistics)](#descritivacsv-descriptive-statistics)
- [razoes.csv (ratios between configurations)](#razoescsv-ratios-between-configurations)
- [hipoteses.csv and h4.json (hypotheses)](#hipotesescsv-and-h4json-hypotheses)
- [criterios.json (evaluation criteria E1 to E6)](#criteriosjson-evaluation-criteria-e1-to-e6)
- [decomposicao.csv (energy = power × time)](#decomposicaocsv-energy--power--time)
- [sensibilidade-global.csv and sensibilidade-contrastes.csv (sensitivity analysis)](#sensibilidade-globalcsv-and-sensibilidade-contrastescsv-sensitivity-analysis)
- [metadados.json (run metadata)](#metadadosjson-run-metadata)
- [Naive session of criterion E7](#naive-session-of-criterion-e7)
- [Raw data of a session](#raw-data-of-a-session)
- [Raw data of a process](#raw-data-of-a-process)

---

## Common values

These values appear in several files.

| Column | Value | Meaning |
|---|---|---|
| `application` | `lusearch`, `pmd`, `avrora` | DaCapo workload |
| `role` | `principal` | main workload (answers the hypotheses) |
| `role` | `exploratorio` | exploratory workload (reported, but outside the conclusions) |
| `configuration` | `A`, `B`, `C`, `D` | Temurin 17.0.19, 21.0.11, 25.0.3 with Compact Object Headers off, 25.0.3 with them on |
| `comparison` | `B/A`, `C/B`, `D/C` | numerator configuration ÷ denominator configuration |
| `category` | `oficial` / `piloto` | official process / pilot process (outside the official sample) |
| `session` | e.g. `20261022T215204Z` | session folder name (UTC time when the session plan was written) |
| `metric` | `energy_j` | energy per measured iteration, in joules |
| `metric` | `time_s` | time per measured iteration, in seconds |
| `metric` | `power_w` | mean power, in watts |
| `metric` | `gc_pauses` | number of garbage collection pauses |
| `metric` | `gc_pause_time_ms` | total garbage collection pause time, in milliseconds |
| `metric` | `gc_heap_after_median_mb` | median heap occupancy after a collection, in MB |
| `metric` | `meter_overhead` | meter overhead (fraction, not percent) |

The `label` column repeats the metric in Portuguese, for the report. Its values are `energia (J)` (energy),
`tempo (s)` (time), `potência média (W)` (mean power), `número de coletas` (number of collections),
`tempo de pausas (ms)` (pause time), `heap após coleta (MB)` (heap after collection) and `sobrecarga do medidor`
(meter overhead).

Session codes and their random draw codes (seeds) are `20261022T215204Z` = session 1 (20261101),
`20261022T215207Z` = session 2 (20261102), `20261022T215211Z` = session 3 (20261103) and `20261022T215214Z` =
session 4 (20261104).

---

## base-oficial.csv and base-pilotos.csv (one row per process)

`base-oficial.csv` has the 180 official processes and `base-pilotos.csv` the pilot processes. Both have the same
columns. `base-oficial.json` holds the same data as JSON. Empty cells mean the value does not apply or was not
recorded (mostly in older pilots).

| Column | Unit | Meaning |
|---|---|---|
| `category` | – | `oficial` or `piloto` |
| `session` | – | session folder name |
| `seed` | – | random draw code that set the order of the session |
| `block` | – | block number (1 to 15 in the official collection) |
| `order` | – | position of the process inside its session |
| `name` | – | process folder name, `bNN-OOO-application-configuration` (block, order, workload, configuration) |
| `application` | – | DaCapo workload |
| `role` | – | `principal` or `exploratorio` |
| `configuration` | – | A, B, C or D |
| `java_runtime_version` | – | Java version reported by the JVM itself before the run |
| `compact_headers` | – | state of Compact Object Headers reported by the JVM (`true`/`false`; empty on JDKs 17 and 21, which do not have the option) |
| `energy_j` | J | mean package energy of the measured iterations |
| `time_s` | s | mean time of the measured iterations |
| `power_w` | W | sum of energies ÷ sum of times of the measured iterations |
| `energy_iterations_j` | J | energy of each measured iteration, separated by `\|` |
| `time_iterations_s` | s | time of each measured iteration, separated by `\|` |
| `measured_iterations` | – | number of measured iterations (3 in the official collection) |
| `warmup_iterations` | – | number of warm-up iterations before the measured ones |
| `last_warmup_dacapo_ms` | ms | duration of the last warm-up iteration, as reported by DaCapo |
| `measured_dacapo_mean_ms` | ms | mean duration of the measured iterations, as reported by DaCapo |
| `meter_overhead` | fraction | `measured_dacapo_mean_ms ÷ last_warmup_dacapo_ms − 1` (criterion E4) |
| `gc_pauses` | count | garbage collection pauses in the whole process (`young + full + other`) |
| `gc_young_pauses` | count | young (and mixed) collection pauses |
| `gc_full_pauses` | count | full collection pauses |
| `gc_other_pauses` | count | other G1 pauses (Remark and Cleanup of the concurrent cycle) |
| `gc_pause_time_ms` | ms | sum of all pause times in the GC log |
| `gc_heap_after_median_mb` | MB | median heap occupancy after each collection (the GC log has 1 MB resolution) |
| `idle_power_w` | W | mean package power during the 10 s idle baseline before the process |
| `start_celsius` | °C | package temperature when the process started, after the cooling pause |
| `wall_seconds` | s | total wall-clock time of the process, including JDK checks and warm-up |
| `valid` | – | `True` when the process passed every check |
| `problems` | – | reasons for an invalid process, in Portuguese (empty in all official processes) |
| `missing_files` | – | required evidence files that are missing (empty in all official processes) |
| `source` | – | path of the process folder in the repository |
| `result_sha256` | – | SHA-256 of the process's `resultado.json` |

---

## descritiva.csv (descriptive statistics)

One row per workload × configuration × metric, computed over the official processes.

| Column | Meaning |
|---|---|
| `application`, `role`, `configuration`, `metric`, `label` | see [Common values](#common-values) |
| `n` | number of processes (15 per combination) |
| `median`, `mean`, `min`, `max` | median, mean, minimum and maximum, in the metric's unit |
| `cv` | coefficient of variation, sample standard deviation ÷ mean (fraction) |

---

## razoes.csv (ratios between configurations)

One row per workload × metric × comparison. This is the main effect table of the study.

| Column | Meaning |
|---|---|
| `application`, `role`, `metric`, `label`, `comparison` | see [Common values](#common-values) |
| `blocks` | number of blocks with both configurations (15) |
| `median_numerator` | median of the metric in the numerator configuration |
| `median_denominator` | median of the metric in the denominator configuration |
| `ratio` | `median_numerator ÷ median_denominator`; below 1 means a lower value in the numerator |
| `ci_low`, `ci_high` | 95% confidence interval of the ratio (block-paired bootstrap, 10,000 resamples, seed 20261101) |
| `change_pct` | `(ratio − 1) × 100`, the change in percent |
| `half_width_pp` | half-width of the confidence interval, in percentage points (criterion E3) |
| `mann_whitney_u` | Mann-Whitney U statistic (two-sided, normal approximation) |
| `p_value` | p-value of the Mann-Whitney test |
| `p_holm` | p-value after Holm correction |
| `a12` | Vargha-Delaney A12, the probability that a numerator value is larger than a denominator value |
| `a12_magnitude` | size of A12: `desprezível` (negligible), `pequeno` (small), `médio` (medium), `grande` (large) |

The A12 sizes follow the usual Vargha-Delaney cut-offs on `|A12 − 0.5|`, which are below 0.06 negligible, below 0.14
small, below 0.21 medium, and large otherwise.

---

## hipoteses.csv and h4.json (hypotheses)

`hipoteses.csv` has one row per hypothesis and workload.

| Column | Meaning |
|---|---|
| `hypothesis` | `H1`, `H2`, `H3a`, `H3b`, `H5 (B/A)`, `H5 (C/B)` (statements in the [README](README.en.md#-statistical-analysis-criteria-and-hypotheses)) |
| `application`, `role` | see [Common values](#common-values) |
| `decision` | verdict, one of `confirmada` (confirmed), `não confirmada` (not confirmed), `refutada` (refuted), `inconclusiva` (inconclusive) |

H4 is descriptive and goes to `h4.json`.

| Field | Meaning |
|---|---|
| `energy_ratio` | D/C energy ratio of each workload |
| `heap_ratio` | D/C ratio of heap occupancy after collection of each workload |
| `order_by_energy_reduction` | workloads from the largest to the smallest energy reduction |
| `order_by_heap_reduction` | workloads from the largest to the smallest heap reduction |
| `same_order` | `true` when both orders match (H4 expectation) |

---

## criterios.json (evaluation criteria E1 to E6)

Each criterion has a `met` field (`true` or `false`) and the values used to decide it. E7 depends on a separate naive
session and is not in this file.

| Criterion | Fields |
|---|---|
| `E1` repeatability | `limit` (0.05); `cells` with `cv` per workload × configuration; `max_main` (largest CV of the main workloads) |
| `E2` reproducibility across sessions | `limit` (0.05); `cells` with `session_medians` (median energy per session) and `spread` (largest ÷ smallest − 1); `max_main`; `above_limit` (combinations above the limit) |
| `E3` sensitivity | `limit_pp` (3); `cells` with `half_width_pp` of the D/C energy ratio |
| `E4` intrusion | `limit` (0.02); `cells` with the `median` meter overhead; `met_absolute` (same test on the absolute value) |
| `E5` traceability | `processes`, `complete`, `share`; `incomplete` (names of incomplete processes); `manifests` (manifest file of each session); `sessions_without_manifest` |
| `E6` feasibility | `limit_minutes` (90); `limit_failure_share` (0.05); `sessions` with `elapsed_minutes`, `attempts`, `failures`, `failure_share` and `idle_celsius` |

---

## decomposicao.csv (energy = power × time)

Exploratory. Since E = P × t in each process, within each block `log(E_x/E_y) = log(P_x/P_y) + log(t_x/t_y)`. The
file reports the median over blocks of each term.

| Column | Meaning |
|---|---|
| `application`, `comparison` | see [Common values](#common-values) |
| `blocks` | number of blocks used |
| `median_log_energy`, `median_log_power`, `median_log_time` | median of each log-ratio term |
| `energy_change_pct`, `power_change_pct`, `time_change_pct` | the same medians as percent changes, `(exp(median) − 1) × 100` |
| `time_share` | share of the energy change explained by time, `median_log_time ÷ median_log_energy` (empty when the energy change is below 1%) |

---

## sensibilidade-global.csv and sensibilidade-contrastes.csv (sensitivity analysis)

Exploratory analysis, **not** in the pre-registration, used only to check whether other methods would change the
conclusions. It covers energy, time and mean power.

`sensibilidade-global.csv` tests whether the four configurations differ at all.

| Column | Meaning |
|---|---|
| `application`, `role`, `metric`, `label` | see [Common values](#common-values); `label` is `energia`, `tempo` or `potência média` |
| `blocks` | complete blocks (all four configurations present) |
| `friedman_chi2`, `friedman_df`, `friedman_p` | Friedman test |
| `anova_f`, `anova_df1`, `anova_df2`, `anova_p` | blocked ANOVA on the logarithm of the metric |

`sensibilidade-contrastes.csv` repeats each comparison with other methods.

| Column | Meaning |
|---|---|
| `application`, `role`, `metric`, `label`, `comparison` | see [Common values](#common-values) |
| `pairs` | number of block pairs |
| `main_ratio`, `main_ci_low`, `main_ci_high` | ratio and 95% CI of the main analysis (same as `razoes.csv`) |
| `main_direction`, `t_direction` | direction of the effect, `menor` (lower), `maior` (higher) or `sem diferença` (no difference, CI contains 1) |
| `geo_ratio`, `geo_ci_low`, `geo_ci_high` | geometric mean of the paired ratios and its 95% CI (paired t-test on logs) |
| `t_statistic`, `t_p`, `t_p_holm` | paired t-test on logs, p-value and Holm-corrected p-value |
| `wilcoxon_w_plus`, `wilcoxon_p`, `wilcoxon_p_holm` | exact Wilcoxon signed-rank test, p-value and Holm-corrected p-value |
| `agrees` | `True` when the t-test direction agrees with the main analysis |

---

## metadados.json (run metadata)

| Field | Meaning |
|---|---|
| `tool`, `version` | analysis package and its version |
| `created_at_utc` | when the analysis was run |
| `python`, `platform` | Python version and operating system of the run |
| `repository_commit` | Git commit of the repository at the time of the run |
| `settings` | `resamples` (10,000), `level` (0.95) and `seed` (20261101) of the bootstrap |
| `official_processes` | number of official processes read |
| `input_sha256` | SHA-256 that identifies the input data (the same on any computer) |

---

## Naive session of criterion E7

Criterion E7 compares the official protocol with a "naive" measurement (fixed order A, B, C, D, no pinned cores, no
pauses, 1 warm-up and 1 measured iteration). The naive session is **outside the official sample**. Its raw data live
in `dados/ingenua/ingenua-20261103T194354Z/`, with the same files as an official process folder, and its results
in [`resultados/ingenua-e7-20261103/`](resultados/ingenua-e7-20261103/), produced by `scripts/analisar_ingenua.py`.
In these files the **repetition** (1 to 10) plays the role of the block.

### base-ingenua.csv (one row per naive process)

| Column | Meaning |
|---|---|
| `name` | process folder name, e.g. `r01-001-lusearch-A` (repetition 1, first process of the session, workload, configuration) |
| `repetition` | repetition number (1 to 10) |
| `order` | position of the process in the session (1 to 120) |
| `application`, `configuration` | see [Common values](#common-values) |
| `java_runtime_version` | Java version reported by the JVM |
| `compact_headers` | whether Compact Object Headers were on (empty when the JVM does not report it) |
| `energy_j`, `time_s`, `power_w` | energy (J), time (s) and mean power (W) of the measured iteration |
| `gc_pauses` | number of garbage collection pauses |
| `start_celsius` | processor package temperature at the start of the process, in °C |
| `valid` | `True` if the process passed all checks |
| `problems` | checks that failed (empty when valid) |

### descritiva-ingenua.csv (descriptive statistics)

| Column | Meaning |
|---|---|
| `application`, `configuration`, `metric` | see [Common values](#common-values) |
| `n` | number of naive processes (10 per combination) |
| `median`, `cv` | median and coefficient of variation (fraction) in the naive session |
| `official_median`, `official_cv` | the same values in the official collection, for comparison |

### comparacao-e7.csv (naive versus official conclusions)

| Column | Meaning |
|---|---|
| `application`, `role`, `metric`, `comparison` | see [Common values](#common-values) |
| `repetitions` | number of repetitions with both configurations (10) |
| `naive_ratio`, `naive_ci_low`, `naive_ci_high` | ratio of medians and its 95% confidence interval in the naive session (repetition-paired bootstrap, 10,000 resamples, seed 20261101) |
| `naive_half_width_pp` | half-width of the naive confidence interval, in percentage points |
| `naive_direction` | conclusion read from the naive interval |
| `official_ratio`, `official_ci_low`, `official_ci_high`, `official_half_width_pp` | the same values in the official collection |
| `official_direction` | conclusion read from the official interval |
| `same_direction` | `True` if the naive measurement reaches the same conclusion as the official collection |

The direction values are `menor` (lower, whole interval below 1), `maior` (higher, whole interval above 1) and
`sem diferença` (no difference, the interval contains 1).

### temperatura-por-posicao.csv

| Column | Meaning |
|---|---|
| `application`, `configuration` | see [Common values](#common-values) |
| `median_start_celsius` | median package temperature at the start of the process, in °C, to show the effect of the fixed order |

### resumo-e7.txt and metadados.json

`resumo-e7.txt` is the readable summary of the comparison, in Portuguese. `metadados.json` records the session name
(`sessao`), the number of processes (`processos`), the invalid processes (`invalidos`), the official results used as
reference (`referencia_oficial`) and the bootstrap settings (`reamostragens` resamples, `nivel` level, `semente`
seed, `bloco` block = `repetição` repetition).

---

## Raw data of a session

Each folder in `dados/brutos/` is one session.

| File | Content |
|---|---|
| `plano-antes-execucao.json` | session plan written **before** execution, with the seed, blocks, pauses and the list `runs` (block, order, workload, configuration, name of each process) |
| `progresso.jsonl` | one line per process as it finished, with `success`, `wall_seconds`, `failure` and `cooling` (`limit_celsius`, `start_celsius`, `end_celsius`, `waited_seconds`, `timed_out`) |
| `<session>-temperatura-ociosa.json` | 60 s of idle package temperature readings at the session start; `median_celsius` sets the cooling limit (+8 °C) |
| `<session>-ambiente-inicial.json` / `-ambiente-final.json` | full system state at the start and end of the session |
| `<session>-resumo-sessao.json` | session summary (status, failures, duration) |
| `aquecimento-maquina/` | machine warm-up process (`pmd`/B), not analyzed |
| `bNN-OOO-<workload>-<configuration>/` | one folder per process (next section) |

The SHA-256 of every file of each session is in `evidencias/manifestos/sessaoN.json`.

---

## Raw data of a process

| File | Content |
|---|---|
| `resultado.json` | verified result of the process (fields below) |
| `command.json` | exact JVM command line |
| `config.json` | protocol settings used for this process |
| `java-preflight.json` | JVM identity checked before the run (version, vendor, `java.home`, G1, Compact Object Headers) |
| `sdkman.json` | JDK selected through SDKMAN |
| `artifacts.json` | SHA-256 of the meter and DaCapo files |
| `system-before.json` / `system-after.json` | system state (charger, temperature, memory, swap, power profile) |
| `idle-baseline.json` | idle energy and power before the process |
| `started.json` | start time of the process |
| `automation.json` | SHA-256 of the collection scripts used to run the process |
| `gc.log` | garbage collection log (`-Xlog:gc`) |
| `stdout.log` / `stderr.log` | DaCapo output |
| `medidor/` | raw meter output (below) |

Main fields of `resultado.json`:

| Field | Meaning |
|---|---|
| `status` | `success` when the process ran and its measurement was verified |
| `measurement_verified` | `true` when the meter output passed every check |
| `session_id`, `block_id`, `order` | session, block and position of the process |
| `configuration`, `application`, `category` | configuration, workload and category (`official`, `pilot` or `verification`) |
| `cpu_affinity` | core pinning policy and the logical CPUs used |
| `idle_baseline` | `seconds`, `energy_j` and `mean_power_w` of the idle baseline |
| `verified_measurement.energy_j`, `.time_s` | mean energy and time of the measured iterations |
| `verified_measurement.measured_energy_j`, `.measured_time_s` | energy and time of each measured iteration |
| `verified_measurement.warmup_dacapo_ms`, `.measured_dacapo_ms` | DaCapo durations of the warm-up and measured iterations |
| `verified_measurement.java_runtime_version` | Java version seen by the meter inside the JVM |
| `events` | ordered list of steps (JDK selection, checks, run) with UTC times |
| `started_at_utc`, `finished_at_utc`, `total_wall_seconds` | start, end and duration of the process |

Files in `medidor/` (meter output):

| File | Content |
|---|---|
| `iterations.jsonl` | one line per DaCapo iteration, with `ordinal`, `warmup` (`true` for warm-up), `dacapo_valid`, `dacapo_duration_ms`, `energy_j` and `time_s` (empty for warm-up) |
| `iteration-N.started.json` | start record of iteration N |
| `iteration-N.samples.json` | counter samples of a measured iteration, every 100 ms, as `energy_uj` (RAPL counter, microjoules), `before_nanos` and `after_nanos` (monotonic clock around each read) |
| `jvm.json` | JVM identity and arguments as seen from inside the measured JVM |
| `metadata.json` | run identity (process name, category, session, block, configuration, DaCapo version and parameters) |
| `summary.json` | final meter status (`measurement_valid` when all measured iterations are valid) |
