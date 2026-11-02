# PAE-JVM: JVM Energy Efficiency – Temurin 17 vs 21 vs 25 and Compact Object Headers

[![Java Support](https://img.shields.io/badge/Java-17%20%7C%2021%20%7C%2025-orange?logo=openjdk)](#-configurations-compared)
[![Python Analysis](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](#-level-1--re-run-the-analysis-any-computer)
[![Open Science](https://img.shields.io/badge/Open%20Science-Compliant-success)](#-open-science)
[![DaCapo](https://img.shields.io/badge/DaCapo-23.11--MR2--chopin-informational)](#-workloads-dacapo)
[![Energy](https://img.shields.io/badge/Energy-Intel%20RAPL-lightgrey)](#-how-energy-is-measured)
[![Docker](https://img.shields.io/badge/Docker-analysis-2496ED?logo=docker&logoColor=white)](#option-c-docker)
[![Code: MIT](https://img.shields.io/badge/Code-MIT-yellow)](LICENSE)
[![Data: CC BY 4.0](https://img.shields.io/badge/Data-CC%20BY%204.0-lightgrey)](LICENCA-DADOS.txt)

🇧🇷 [Português](README.md) | 🇺🇸 English

This repository holds the protocol, code, raw data, evidence and statistical analysis of a master's research project
in **Green Software** (Software Engineering) that measures processor energy and execution time of versions and
options of the Java Virtual Machine (**JVM**) from the **Eclipse Temurin** distribution: **JDK 17, 21 and 25**, and JDK 25
**with and without Compact Object Headers** (JEP 519).

The research follows **Design Science Research (DSR)**. The artifact is **PAE-JVM** (*Protocolo de Avaliação
Energética de configurações da JVM*, an energy evaluation protocol for JVM configurations): a meter integrated with the
DaCapo suite, verified JDK selection, a session orchestrator, and rules for noise, failures and analysis. The
experimental collection is the evaluation of this artifact, with criteria (E1 to E7) and hypotheses (H1 to H5)
registered **before** data collection in [`config/registro-previo.json`](config/registro-previo.json).

Everything needed to verify the data, re-run the analysis and repeat the data collection is here, with complete
step-by-step instructions in [How to reproduce](#-how-to-reproduce).

> The code, scripts, file names and program messages are in Portuguese. This English README explains each step and
> translates the messages you will see; a glossary is at the end.

---

## 📑 Contents

- [Research questions](#-research-questions)
- [Configurations compared](#-configurations-compared)
- [Workloads (DaCapo)](#-workloads-dacapo)
- [How energy is measured](#-how-energy-is-measured)
- [Collection design](#-collection-design)
- [Original collection environment](#-original-collection-environment)
- [Metrics](#-metrics)
- [Statistical analysis, criteria and hypotheses](#-statistical-analysis-criteria-and-hypotheses)
- [Main results](#-main-results)
- [Repository layout](#-repository-layout)
- [How to reproduce](#-how-to-reproduce)
  - [Level 1 – Re-run the analysis (any computer)](#-level-1--re-run-the-analysis-any-computer)
  - [Level 2 – Repeat the data collection (Linux with Intel RAPL)](#-level-2--repeat-the-data-collection-linux-with-intel-rapl)
- [Troubleshooting](#-troubleshooting)
- [Tagged versions](#-tagged-versions)
- [Open science](#-open-science)
- [Limitations](#-limitations)
- [Licenses](#-licenses)
- [How to cite](#-how-to-cite)
- [Glossary of Portuguese terms](#-glossary-of-portuguese-terms)

---

## ❓ Research questions

**Design question (DSR):** how can the effect of JVM versions and options on energy and execution time be evaluated
reliably and reproducibly on a personal computer without an external power meter?

**Knowledge questions:**

- **QC1.** When Compact Object Headers are enabled in Eclipse Temurin 25, what changes in processor energy and
  execution time for the same task, and does the change follow the expected mechanism (lower memory footprint and
  less garbage collection work)?
- **QC2.** In the upgrades from Temurin 17 to 21 and from 21 to 25, does the change in energy follow the change in
  time?

---

## ☕ Configurations compared

| Configuration | JDK (Eclipse Temurin) | SDKMAN identifier | Specific option |
|---|---|---|---|
| **A** | 17.0.19+10 | `17.0.19-tem` | – |
| **B** | 21.0.11+10-LTS | `21.0.11-tem` | – |
| **C** | 25.0.3+9-LTS | `25.0.3-tem` | `-XX:-UseCompactObjectHeaders` (off) |
| **D** | 25.0.3+9-LTS | `25.0.3-tem` | `-XX:+UseCompactObjectHeaders` (on) |

Common to all: **G1** collector (`-XX:+UseG1GC`), fixed **1 GB** heap (`-Xms1g -Xmx1g`), garbage collection log
(`-Xlog:gc`), **1 workload thread**, and affinity to the performance cores (one logical CPU per physical core).
Before each process, the program checks the full version, vendor, `java.home`, G1 and the Compact Object Headers state
actually active in the JVM; if anything differs, the process does not run.

Comparisons: **B/A** (17 → 21), **C/B** (21 → 25) and **D/C** (Compact Object Headers on vs off).

---

## 📦 Workloads (DaCapo)

**DaCapo 23.11-MR2-chopin** suite ([official site](https://www.dacapobench.org/)), `default` input size, 1 thread.

| Workload | Role | What it does | Warm-up iterations | Measured iterations |
|---|---|---|---|---|
| **lusearch** | main | text search with Apache Lucene | 1 | 3 |
| **pmd** | main | static analysis of Java code | 7 | 3 |
| **avrora** | exploratory | AVR microcontroller simulation | 12 | 3 |

The number of warm-up iterations for each workload was set in the pilot runs (data in `dados/piloto/`). The main
workloads answer the hypotheses; avrora runs in the same blocks but stays out of the conclusions because it varied
a lot in the pilots.

---

## ⚡ How energy is measured

- **Source:** the **processor package** energy counter through the Linux **Intel RAPL** interface
  (`/sys/class/powercap/intel-rapl:0/energy_uj`). It covers the whole processor (all cores, cache and integrated
  memory controller), not only the JVM and not wall-socket energy.
- **Meter:** Java project in [`medidor-java/`](medidor-java/), running as a DaCapo *callback* inside the JVM itself.
  It reads the counter every **100 ms**, handles counter wrap-around and marks the exact start and end of each DaCapo
  iteration.
- **Idle baseline:** before each process, 10 s of readings with no workload (idle power recorded).
- **Meter overhead:** time of the measured iterations compared with the last warm-up iteration (criterion E4).

---

## 🧪 Collection design

- **Complete, randomized blocks:** each block holds all 12 combinations (3 workloads × 4 configurations) in a drawn
  order. **15 blocks = 180 processes** in total (15 per combination). Each process is a **fresh JVM**.
- **Sessions:** the 15 blocks were split into **4 sessions** (4 + 4 + 4 + 3 blocks) on different days, with random
  draw codes **20261101 to 20261104**. Each session plan is written **before** execution.
- **Machine warm-up:** each session starts with one `pmd`/B process that is not analyzed.
- **Pauses:** at least 10 s between processes, then wait until the package temperature is at most 8 °C above the idle
  temperature measured at the session start (120 s maximum wait).
- **Failures:** a failed process is retried once at the end of the same block; the failure stays recorded. Three
  consecutive failures stop the session. The official collection had **0 failures**.
- **Checks before each process:** charger connected, no Java options inherited from the environment
  (`JAVA_TOOL_OPTIONS` etc.), SHA-256 of the meter and DaCapo equal to the registered values, RAPL counter advancing.
- **Traceability:** each process keeps its command, JVM identity, system state before and after, GC log, meter
  readings and result. At the end of each session, a manifest records the SHA-256 of every file.

Fixed collection parameters: [`config/execucao.json`](config/execucao.json) (status `fixado`, i.e. frozen).

---

## 💻 Original collection environment

| Item | Value |
|---|---|
| Processor | Intel Core i7-13650HX (6 performance + 8 efficiency cores, 20 logical CPUs) |
| Affinity used | logical CPUs 0, 2, 4, 6, 8, 10 (one per performance core) |
| Memory | 16 GB |
| System | Zorin OS (Ubuntu based), Linux kernel 7.0.0-38-generic, installed on bare metal |
| Power | laptop on the charger; power profile "balanced"; `powersave` governor; turbo on |
| JDK selection | SDKMAN 5.23.0 (`sdk use` only in the child process; system default Java untouched) |
| Meter | Java 17 (Maven), SHA-256 `415ddd80…26339995` |

The full system state of each session is in `dados/brutos/<session>/<session>-ambiente-inicial.json` and
`-ambiente-final.json`; for each process, in `system-before.json` and `system-after.json`.

---

## 📏 Metrics

| Metric | Unit | Definition |
|---|---|---|
| Energy (E) | J | mean of the process's 3 measured iterations (package energy per iteration) |
| Time (t) | s | mean of the 3 measured iterations |
| Mean power (P) | W | sum of energies ÷ sum of times of the measured iterations (P = E / t) |
| Garbage collections | count | pauses recorded in the GC log over the whole process |
| GC pauses | ms | sum of pauses over the whole process |
| Heap after GC | MB | median heap occupancy after each collection |
| Meter overhead | % | mean time of measured iterations ÷ time of the last warm-up − 1 |

Power separates two causes: a configuration may use less energy because it finishes sooner (same power, less time) or
because it demands less from the processor (lower power at similar time).

---

## 📊 Statistical analysis, criteria and hypotheses

- **Effect measure:** ratio of medians between configurations (e.g. D/C), with a **95% CI from a block-paired
  bootstrap** (10,000 resamples, random draw code 20261101). A ratio below 1 means a lower value in the numerator
  configuration.
- **Complementary tests** (in `razoes.csv`): Mann-Whitney U with Holm correction and the Vargha-Delaney A12 effect
  size.
- **Sensitivity analysis (exploratory, not pre-registered):** Friedman, blocked ANOVA on logs, paired t-test on logs
  and exact Wilcoxon, with Holm.

**Artifact evaluation criteria (E1–E7):**

| Criterion | Measure | Limit |
|---|---|---|
| E1 Repeatability | energy CV per workload × configuration | ≤ 5% for main workloads |
| E2 Reproducibility across sessions | largest ÷ smallest session median energy − 1 | ≤ 5% for main workloads |
| E3 Sensitivity | half-width of the 95% CI of the D/C energy ratio | ≤ 3 percentage points |
| E4 Intrusion | meter overhead (median) | ≤ 2% |
| E5 Traceability | processes with complete evidence | 100% |
| E6 Feasibility | machine time per session and failures | ≤ 1h30 per session; failures ≤ 5% |
| E7 Naive comparison | measurement without warm-up, pinned cores or random order | descriptive |

**Hypotheses (H1–H5):**

| Hypothesis | Statement | Confirmed if | Refuted if |
|---|---|---|---|
| H1 | Lower energy in D than in C | 95% CI of D/C energy entirely below 1 | entirely above 1 |
| H2 | The D/C energy change follows the time change (no relevant power change) | 95% CI of D/C power within [0.98, 1.02] | CI excludes 1 |
| H3a | Lower heap occupancy after GC in D | 95% CI of D/C entirely below 1 | – |
| H3b | Fewer collections or less pause time in D | 95% CI of at least one ratio entirely below 1 | – |
| H4 | Largest energy reduction in the workload with the largest heap reduction | exploratory, descriptive | – |
| H5 | In B/A and C/B, energy follows time | 95% CI of power within [0.98, 1.02] | – |

**Verdict terms** (Portuguese in the output files): **confirmada** = confirmed (the confirmation rule was met);
**refutada** = refuted (the refutation rule was met); **inconclusiva** = inconclusive (neither rule was met, for a
hypothesis that has both); **não confirmada** = not confirmed (the confirmation rule was not met, for a hypothesis
without a refutation rule). Rationale: [`evidencias/base-oficial/NOTA_TERMOS_VEREDITOS.txt`](evidencias/base-oficial/NOTA_TERMOS_VEREDITOS.txt).

---

## 📈 Main results

Full results: [`resultados/oficial-20261101-termos/resumo.txt`](resultados/oficial-20261101-termos/resumo.txt).
Main workloads (ratio of medians and block-paired 95% CI):

| Workload | Comparison | Energy | Time | Mean power |
|---|---|---|---|---|
| lusearch | B/A (17 → 21) | 0.9335 [0.9192, 0.9479] | 0.9468 [0.9405, 0.9519] | 0.9835 [0.9761, 0.9970] |
| lusearch | C/B (21 → 25) | 1.0202 [1.0104, 1.0271] | 1.0101 [1.0049, 1.0127] | 1.0152 [1.0070, 1.0161] |
| lusearch | D/C (compact) | 0.9955 [0.9888, 1.0175] | 0.9962 [0.9926, 1.0059] | 0.9997 [0.9848, 1.0093] |
| pmd | B/A (17 → 21) | 0.9597 [0.9502, 0.9751] | 0.9486 [0.9423, 0.9503] | 1.0133 [1.0103, 1.0342] |
| pmd | C/B (21 → 25) | 0.9546 [0.9401, 0.9617] | 0.9352 [0.9332, 0.9391] | 1.0142 [1.0052, 1.0260] |
| pmd | D/C (compact) | 1.0037 [0.9903, 1.0154] | 1.0048 [1.0028, 1.0085] | 1.0018 [0.9874, 1.0121] |

| Hypothesis | lusearch | pmd |
|---|---|---|
| H1 lower energy in D | inconclusive | inconclusive |
| H2 no D/C power change | confirmed | confirmed |
| H3a smaller heap in D | not confirmed | confirmed |
| H3b fewer collections/pauses in D | confirmed | confirmed |
| H5 B/A energy follows time | not confirmed | not confirmed |
| H5 C/B energy follows time | confirmed | not confirmed |

Criteria: E1, E3, E4 (median), E5 and E6 **met**; **E2 not met** (largest difference between sessions 6.1%, limit 5%,
in lusearch-A, pmd-A, pmd-B and pmd-D); E7 pending (naive session). Block-paired ratios were stable across sessions,
so comparisons should use within-block ratios rather than absolute energy across different days. All 180 processes
are valid.

---

## 📂 Repository layout

```text
├── README.md / README.en.md        # This documentation (Portuguese / English)
├── LICENSE                         # MIT license (code)
├── LICENCA-DADOS.txt               # CC BY 4.0 license (data, results, evidence, configuration)
├── CITATION.cff                    # Citation metadata
├── Dockerfile / .dockerignore      # Image that re-runs the analysis
├── config/
│   ├── execucao.json               # Frozen collection protocol (JDKs, workloads, iterations, heap, pauses, SHA-256)
│   ├── registro-previo.json        # Pre-registration: criteria E1–E7, hypotheses H1–H5, decision rules
│   └── piloto-t12.json             # Configuration of the pilot that defined the protocol
├── dados/                          # Data
│   ├── brutos/<session>/           # 4 official sessions; one folder per process (e.g. b01-001-lusearch-A)
│   └── piloto/                     # Pilots (outside the official sample)
├── evidencias/                     # Evidence
│   ├── manifestos/                 # SHA-256 of every file of each session and pilot
│   ├── conferencias/               # Quality check of each session and of the whole collection
│   └── base-oficial/               # How official results were produced, incidents, checksums
├── resultados/                     # Results
│   ├── oficial-20261101/           # Official results (tag base-oficial-v1)
│   └── oficial-20261101-termos/    # Same numbers with the current verdict terms (USE THIS ONE)
├── analise/                        # Python package pae-analise (consolidation, statistics, figures, tests)
│   └── requisitos-travados.txt     # Exact library versions (lock file)
├── medidor-java/                   # Energy meter (DaCapo callback, Maven, Java 17)
├── ferramentas/dacapo.json         # DaCapo URL, version and SHA-256 (the suite is not in the repository)
├── scripts/
│   ├── reproduzir_analise.sh       # Re-runs the analysis and compares with the official one (one command)
│   ├── conferir_dados.sh           # Checks the data against the manifests
│   ├── comparar_resultados.py      # Compares two results folders
│   ├── preparar_ambiente_coleta.sh # Prepares a Linux machine to repeat the collection (JDKs, DaCapo, meter)
│   ├── planejar_sessoes_oficiais.sh# Writes the 4 session plans with the original random draw codes
│   ├── sessao.py                   # Plans and runs one session in blocks
│   ├── executar.py / executar.sh   # Prepares or runs one JVM process with all checks
│   ├── selecionar-java.sh          # JDK selection through SDKMAN (called by executar.py)
│   ├── manifesto.py                # Writes or checks a session's SHA-256 manifest
│   ├── conferir_sessao.py          # Checks a session's quality against the protocol
│   ├── conferir_coleta.py          # Checks several sessions together (includes E2)
│   └── tests/                      # Tests of the collection scripts
└── .github/workflows/analise.yml   # Automatic checks (style, types, tests, reproduction and Docker)
```

Inside each process folder (`dados/brutos/<session>/bNN-OOO-workload-config/`):

| File | Content |
|---|---|
| `resultado.json` | verified result: energy and time of each measured iteration, events, idle baseline |
| `command.json` | exact JVM command |
| `java-preflight.json` | effective JVM identity (version, vendor, `java.home`, G1, Compact Object Headers) |
| `sdkman.json` | JDK selected by SDKMAN |
| `artifacts.json` | SHA-256 of the meter and DaCapo used |
| `system-before.json` / `system-after.json` | system state (charger, temperature, memory, swap, power profile) |
| `idle-baseline.json` | idle energy and power before the process |
| `gc.log` | garbage collection log |
| `medidor/` | raw meter readings |
| `stdout.log` / `stderr.log` | DaCapo output |

---

## 🚀 How to reproduce

There are two levels:

| Level | What it does | Where it runs | Time |
|---|---|---|---|
| **1. Re-run the analysis** | verifies the data and recomputes every number from the raw data in the repository | Windows, Linux or macOS | ~5 min |
| **2. Repeat the data collection** | measures again on another machine and analyzes the new data | Linux with Intel RAPL | ~4 h of machine time + setup |

All commands run **in the project's root folder** (the folder containing this README), in a *bash* terminal: Linux or
macOS (Terminal) or Windows with **Git Bash** (installed with [Git for Windows](https://git-scm.com/download/win)).
PowerShell equivalents are shown where they differ.

---

### 🔁 Level 1 – Re-run the analysis (any computer)

#### Prerequisites

| Program | Version | How to check | Where to get it |
|---|---|---|---|
| Git | any recent | `git --version` | <https://git-scm.com/downloads> |
| Python | **3.10 or newer** (official runs: 3.12 and 3.13) | `python --version` or `python3 --version` | <https://www.python.org/downloads/> |
| Disk space | ~300 MB | – | – |
| Internet | only to download the repository and libraries | – | – |

On Windows, when installing Python, tick **"Add python.exe to PATH"**.

#### Step 1 – Download the repository

```bash
git clone https://github.com/evertoncg10/java-energy-study.git
cd java-energy-study
```

To use exactly the version of the published analysis, switch to its tag (optional):

```bash
git checkout analise-v1.1
```

#### Step 2 – Verify data integrity

```bash
bash scripts/conferir_dados.sh
```

Checks every data file against the SHA-256 manifests written at the end of each session and re-runs the collection
check. Expected: `CONFERE` (= matches) on every line and, at the end,
`RESULTADO: todos os dados conferem com os manifestos.` (all data match the manifests).

#### Step 3 – Re-run the analysis (option A: one command)

```bash
bash scripts/reproduzir_analise.sh
```

The script creates the virtual environment `analise/.venv` (first time only), installs the locked library versions,
runs the automated tests, re-runs the analysis into a new folder `resultados/reproducao-YYYYMMDD-HHMMSS` and compares
it with the official results. It takes about 1 minute after installation. Expected output at the end:

```text
idêntico: razoes.csv
idêntico: resumo.txt
...
Arquivos diferentes: 0
```

(`idêntico` = identical; `Arquivos diferentes: 0` = 0 files differ.) To also produce the figures:
`bash scripts/reproduzir_analise.sh --com-figuras`.

#### Step 3 – Re-run the analysis (option B: command by command)

1. Create the virtual environment (first time only):

   ```bash
   python -m venv analise/.venv        # if "python" does not exist, use python3
   ```

2. Activate the virtual environment (in every new terminal):

   | System / terminal | Command |
   |---|---|
   | Windows – Git Bash | `source analise/.venv/Scripts/activate` |
   | Windows – PowerShell | `analise\.venv\Scripts\Activate.ps1` |
   | Windows – Command Prompt (CMD) | `analise\.venv\Scripts\activate.bat` |
   | Linux or macOS | `source analise/.venv/bin/activate` |

   When active, the prompt starts with `(.venv)`. On Windows, also run `export PYTHONUTF8=1` (Git Bash) or
   `$env:PYTHONUTF8=1` (PowerShell) so accented characters are printed correctly.

3. Install the locked versions and run the tests:

   ```bash
   cd analise
   python -m pip install -r requisitos-travados.txt -e ".[dev,figuras]"
   python -m pytest
   cd ..
   ```

   Expected: `41 passed`.

4. Re-run the full analysis (with figures):

   ```bash
   pae-analise analisar --saida resultados/reproducao
   ```

   The output folder (`--saida`) must be new; to run again, use another name (e.g. `resultados/reproducao2`).
   Options: `--sem-figuras` (no figures), `--reamostragens N` (bootstrap resamples, default 10000) and `--semente N`
   (bootstrap random draw code, default 20261101). Only the defaults reproduce the official numbers.

5. Compare with the official results:

   ```bash
   python scripts/comparar_resultados.py resultados/oficial-20261101-termos resultados/reproducao --ignorar-figuras
   ```

   Expected: `Arquivos diferentes: 0`. `metadados.json` always changes (date, system and commit); for it the script
   checks only the `input_sha256` field, which identifies the input data. Figures are left out with
   `--ignorar-figuras` because they are only byte-identical on the same operating system; the numbers (CSV, JSON and
   text) are identical on Windows, Linux and macOS.

6. Only the consolidated dataset (one row per process), to work with the data in another tool:

   ```bash
   pae-analise consolidar --saida resultados/base
   ```

#### Option C: Docker

With [Docker](https://docs.docker.com/get-docker/) installed, no Python needed:

```bash
docker build -t pae-jvm-analise .
docker run --rm pae-jvm-analise
```

The container re-runs the analysis and prints the comparison with the official results (expected:
`Arquivos diferentes: 0`). To write the full analysis, with figures, into `resultados/reproducao-docker` on your
computer:

```bash
docker run --rm -v "$(pwd)/resultados:/saida" pae-jvm-analise pae-analise analisar --saida /saida/reproducao-docker
```

In PowerShell, replace `$(pwd)` with `${PWD}`.

#### Files produced by the analysis

| File | Content |
|---|---|
| `resumo.txt` | readable summary: criteria, ratios, hypotheses, decomposition and sensitivity |
| `base-oficial.csv` / `.json` | consolidated dataset: one row per official process, linked to its source file |
| `base-pilotos.csv` | pilot dataset (kept separate) |
| `descritiva.csv` | n, median, mean, CV, minimum and maximum per workload × configuration × metric |
| `razoes.csv` | B/A, C/B and D/C ratios with 95% CI, Mann-Whitney, Holm and A12 |
| `criterios.json` | computation and verdict of E1 to E6 |
| `hipoteses.csv` / `h4.json` | verdicts of H1 to H5 |
| `decomposicao.csv` | exploratory decomposition log E = log P + log t |
| `sensibilidade-*.csv` | exploratory sensitivity analysis |
| `metadados.json` | date, system, versions, commit and SHA-256 of the input data |
| `figuras/` | energy, ratios, sessions, decomposition, memory and protocol flow (PNG and PDF) |

#### Automatic checks

On every change, GitHub Actions ([`.github/workflows/analise.yml`](.github/workflows/analise.yml)) installs the locked
versions, runs style (ruff), types (mypy) and tests (pytest), re-runs the analysis and compares it with the official
results, and also builds and runs the Docker image.

---

### 🔬 Level 2 – Repeat the data collection (Linux with Intel RAPL)

Repeating the collection measures energy again, on another machine. Absolute values depend on the hardware; what is
expected to reproduce is the **direction and size of the ratios** between configurations under the same protocol.

#### Prerequisites

| Item | Requirement | How to check |
|---|---|---|
| System | Linux installed on bare metal (no virtual machine, WSL or container) | `uname -s` → `Linux` |
| Processor | Intel with the package RAPL domain exposed by the kernel | `cat /sys/class/powercap/intel-rapl:0/name` → `package-0` |
| Cores | Intel hybrid (12th generation or newer) for the original affinity | `cat /sys/devices/cpu_core/cpus` |
| Thermal sensor | `x86_pkg_temp` zone (used for pauses) | `grep -l x86_pkg_temp /sys/class/thermal/thermal_zone*/type` |
| Power | laptop on the charger for the whole session | `cat /sys/class/power_supply/*/online` |
| Permission | user with `sudo` (only to allow reading the RAPL counter) | `sudo -v` |
| Free disk | ~25 GB (DaCapo: 6.3 GB zipped, 15.9 GB extracted) | `df -h .` |
| Programs | `git`, `python3` (3.10+), `curl`, `unzip`, `sha256sum`, Maven 3.9+ | `mvn -version` |
| SDKMAN | with a default Java installed | `sdk version` |

On Ubuntu, Debian, Zorin OS or Mint, install the programs with:

```bash
sudo apt update
sudo apt install git python3 python3-venv curl unzip zip coreutils maven
```

Install SDKMAN with (then open a new terminal):

```bash
curl -s "https://get.sdkman.io" | bash
source "$HOME/.sdkman/bin/sdkman-init.sh"
sdk install java 21.0.11-tem      # serves as default Java; does not affect the collection
```

Without an Intel hybrid processor the collection still runs, but affinity must be turned off
(see [Adapting to other hardware](#adapting-to-other-hardware)).

#### Step 1 – Download the repository

```bash
git clone https://github.com/evertoncg10/java-energy-study.git
cd java-energy-study
```

#### Step 2 – Prepare the environment

```bash
bash scripts/preparar_ambiente_coleta.sh
```

The script checks the system, installs JDKs `17.0.19-tem`, `21.0.11-tem` and `25.0.3-tem` through SDKMAN (without
changing the default Java), downloads DaCapo from the official URL recorded in
[`ferramentas/dacapo.json`](ferramentas/dacapo.json), checks the official SHA-256, extracts it into `ferramentas/dacapo/`,
installs the DaCapo JAR into the local Maven repository, builds and tests the meter and compares the SHA-256 values
with [`config/execucao.json`](config/execucao.json). It can be run again: whatever is ready is only checked. Lines
show `[ok]`, `[aviso]` (warning) or `[erro]` (error). The download takes minutes to hours depending on your connection.

<details>
<summary>The same step, command by command</summary>

```bash
# JDKs (answer "n" when asked whether to make it the default)
sdk install java 17.0.19-tem
sdk install java 21.0.11-tem
sdk install java 25.0.3-tem

# DaCapo 23.11-MR2-chopin
curl -fL -o ferramentas/dacapo-23.11-MR2-chopin.zip \
  https://download.dacapobench.org/chopin/dacapo-23.11-MR2-chopin.zip
echo "70a1fd4ed959f09053bb7ef8b2745a19d6f28dd8a7d0b350362039d89b49eb26  ferramentas/dacapo-23.11-MR2-chopin.zip" | sha256sum -c -
mkdir -p ferramentas/dacapo
unzip -q ferramentas/dacapo-23.11-MR2-chopin.zip -d ferramentas/dacapo
echo "c488cc61fcd02bb04b87e601fd80517b8b0991c0baf564cae17538fdc1edb792  ferramentas/dacapo/dacapo-23.11-MR2-chopin.jar" | sha256sum -c -

# Meter
mvn install:install-file -Dfile=ferramentas/dacapo/dacapo-23.11-MR2-chopin.jar \
  -DgroupId=org.dacapo -DartifactId=dacapo -Dversion=23.11-MR2-chopin -Dpackaging=jar
JAVA_HOME="$HOME/.sdkman/candidates/java/17.0.19-tem" mvn -f medidor-java/pom.xml clean package
sha256sum medidor-java/target/java-energy-meter-0.1.0.jar   # original: 415ddd802fbcde66e77e2f7c1262e79680d92b8fef7a49468a1559ff26339995

# Tests of the collection scripts
python3 -m unittest discover -s scripts/tests
```

</details>

If the meter's SHA-256 differs from the original (another compiler or Maven version), the code is the same but the
program refuses the JAR. In that case, copy the configuration, record the new value and report it as a deviation:

```bash
cp config/execucao.json config/replicacao.json
sha256sum medidor-java/target/java-energy-meter-0.1.0.jar
# edit config/replicacao.json: replace "meter" → "sha256" with the value shown above
```

From then on, add `--config config/replicacao.json` to the commands in steps 4 and 6.

#### Step 3 – Allow reading the RAPL counter

For security, Linux lets only the administrator read the energy counter. The command below allows your user to read
just that counter (it asks for your `sudo` password in the terminal itself; the program never stores passwords):

```bash
bash scripts/executar.sh preparar --configuracao A --liberar-leitura
```

The permission lasts until the computer restarts; after a restart, run it again. It is equivalent to
`sudo chown $(id -u) /sys/devices/virtual/powercap/intel-rapl/intel-rapl:0/energy_uj`.

#### Step 4 – Verification run

One test process, outside the sample (written to `dados/verificacao/`, which is not tracked by Git):

```bash
bash scripts/executar.sh executar --configuracao D --aplicacao pmd
```

Expected: one JSON line ending with `"status": "success"`. This confirms SDKMAN, JDK, Compact Object Headers, RAPL,
affinity, DaCapo and the meter.

#### Step 5 – Prepare the machine before each session

Each session takes about 1 hour (the 4th about 47 min). Before starting:

1. Connect the charger and keep it connected until the end.
2. Close every other program (browser, editors, cloud sync, antivirus scans).
3. Turn off automatic suspend and the screen saver for the session.
4. Do not use the computer during the session.
5. Leave the machine idle for a few minutes (the idle temperature measured at the start defines the pauses).
6. Make sure the RAPL counter is readable (step 3).

#### Step 6 – Plan the sessions

Writes the 4 plans with the same design as the original collection (15 blocks as 4 + 4 + 4 + 3; random draw codes
20261101 to 20261104) into a folder outside the repository:

```bash
bash scripts/planejar_sessoes_oficiais.sh ../planos-pae-jvm
# with a replication configuration:
# bash scripts/planejar_sessoes_oficiais.sh ../planos-pae-jvm config/replicacao.json
```

With the same draw codes, the process order is **identical** to the original collection (checked against the
`plano-antes-execucao.json` of the 4 sessions). For a single plan:

```bash
python3 scripts/sessao.py planejar --config config/execucao.json --categoria oficial \
  --blocos 4 --primeiro-bloco 1 --semente 20261101 --plano ../planos-pae-jvm/plano-sessao1.json
```

(`--blocos` = number of blocks, `--primeiro-bloco` = first block number, `--semente` = random draw code,
`--plano` = plan file.)

#### Step 7 – Run the sessions

One session at a time, preferably on different days, repeating step 5 before each:

```bash
python3 scripts/sessao.py executar --plano ../planos-pae-jvm/plano-sessao1.json
```

The terminal prints `ok` or `FALHA` (failure) for each process and, at the end, `SESSAO=dados/brutos/<session folder>`.
If the session is interrupted (e.g. power loss), continue without repeating what was done:

```bash
python3 scripts/sessao.py executar --plano ../planos-pae-jvm/plano-sessao1.json --retomar
```

Repeat for `plano-sessao2.json`, `plano-sessao3.json` and `plano-sessao4.json`.

#### Step 8 – Freeze and check each session

Right after each session (replace `PASTA` with the folder shown in `SESSAO=`):

```bash
python3 scripts/manifesto.py gerar --sessao dados/brutos/PASTA \
  --saida ../manifestos-pae-jvm/sessao1.json --plano ../planos-pae-jvm/plano-sessao1.json
python3 scripts/conferir_sessao.py --sessao dados/brutos/PASTA
```

The manifest records the SHA-256 of every file (the program never overwrites a manifest). The check shows duration,
failures, temperatures, reading coverage and CV per combination, and ends with `CONFERE` (passes) or `NAO_CONFERE`
(fails). After the 4 sessions, check the whole collection (includes criterion E2):

```bash
python3 scripts/conferir_coleta.py \
  --sessao dados/brutos/PASTA1 --manifesto ../manifestos-pae-jvm/sessao1.json \
  --sessao dados/brutos/PASTA2 --manifesto ../manifestos-pae-jvm/sessao2.json \
  --sessao dados/brutos/PASTA3 --manifesto ../manifestos-pae-jvm/sessao3.json \
  --sessao dados/brutos/PASTA4 --manifesto ../manifestos-pae-jvm/sessao4.json
```

#### Step 9 – Analyze the new data

The analysis reads **all** sessions in `dados/brutos/` and the manifests `evidencias/manifestos/sessao*.json`. To
analyze only your data, move the 4 original sessions and their manifests out of those folders (Git keeps the
originals) and put your manifests in their place:

```bash
mkdir -p ../originais-pae-jvm
mv dados/brutos/20261022T2152* ../originais-pae-jvm/
mv evidencias/manifestos/sessao*.json ../originais-pae-jvm/
cp ../manifestos-pae-jvm/sessao*.json evidencias/manifestos/
```

Git will show those files as deleted; that is expected. To restore the original state later:
`git checkout -- dados/brutos evidencias/manifestos`.

Then activate the analysis environment (Level 1, step 3, items 1 to 3) and run:

```bash
pae-analise analisar --saida resultados/replicacao
```

Compare your `resultados/replicacao/resumo.txt` with the official one, especially the D/C, C/B and B/A ratios.

#### Adapting to other hardware

Any protocol change must be made in a **copy** of the configuration (e.g. `config/replicacao.json`) and reported as a
deviation:

| Situation | What to change in the copy |
|---|---|
| Processor without hybrid cores (no `/sys/devices/cpu_core`) | `"cpu_affinity": null` |
| RAPL counter at another path | `"rapl_directory"` with the path of the `package-0` domain |
| Different meter SHA-256 | `"meter"` → `"sha256"` with the new value |

JDKs, DaCapo, workloads, iterations, heap and pauses must not change; if they do, the result is no longer a
repetition of this protocol.

---

## 🛠️ Troubleshooting

| Message or situation | Cause and fix |
|---|---|
| `python: command not found` | use `python3`; on Windows, reinstall Python ticking "Add python.exe to PATH" |
| Garbled accents or `UnicodeEncodeError` on Windows | `export PYTHONUTF8=1` (Git Bash) or `$env:PYTHONUTF8=1` (PowerShell) |
| PowerShell refuses `Activate.ps1` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or use Git Bash |
| `pae-analise: command not found` | the virtual environment is not active; activate it (Level 1, step 3, item 2) |
| `A pasta de saída já existe e não será sobrescrita` (output folder exists) | use another name in `--saida` |
| Very slow install or analysis on Windows | antivirus may be scanning `analise/.venv`; add the project folder to its exclusions |
| Figures differ from the official ones | normal across operating systems; compare with `--ignorar-figuras` |
| `metadados.json` differs | normal (date, system, commit); what matters is `mesmos dados de entrada: sim` (same input data: yes) |
| `Contador sem leitura. Execute preparar --liberar-leitura…` (counter not readable) | run Level 2, step 3 (permission is lost on restart) |
| `Notebook sem alimentação externa confirmada.` (no charger) | connect the charger |
| `Remova opções Java herdadas antes de executar: …` (inherited Java options) | `unset JAVA_TOOL_OPTIONS JDK_JAVA_OPTIONS _JAVA_OPTIONS CLASSPATH` |
| `SDKMAN precisa ter um Java padrão instalado` (no default Java) | `sdk install java 21.0.11-tem` |
| `SDKMAN não selecionou o JDK` / version not found | the JDK is not installed; if SDKMAN no longer lists it, download the same build from <https://adoptium.net/temurin/archive/> and run `sdk install java 17.0.19-tem <extracted JDK folder>` |
| `SHA-256 divergente para meter` | see Level 2, step 2 (configuration copy with the new SHA-256) |
| `SHA-256 divergente para dacapo` | the DaCapo file is corrupt or another version; download and check again |
| `Nenhum núcleo de desempenho encontrado para a afinidade.` (no performance cores) | processor without hybrid cores; see [Adapting to other hardware](#adapting-to-other-hardware) |
| `Execute como pesquisador, sem sudo no script inteiro.` | run the scripts without `sudo` |
| `Três falhas seguidas; interromper e investigar.` (three failures in a row) | read `stderr.log` and `resultado.json` of the failed process; fix and use `--retomar` |

---

## 🏷️ Tagged versions

| Tag | Content |
|---|---|
| `base-oficial-v1` | official dataset closed after collection, results in `resultados/oficial-20261101` |
| `analise-v1.1` | same numbers, with verdicts in the terms confirmada, não confirmada, refutada and inconclusiva (`resultados/oficial-20261101-termos`) |

How the official results were produced, incidents and checksums: [`evidencias/base-oficial/`](evidencias/base-oficial/).

---

## 🌍 Open science

Following **Open Science** practices, the following are public and reproducible:

- the frozen protocol and the pre-registration of criteria, hypotheses and decision rules, written before collection;
- raw data of all 180 official processes and of the pilots, with no exclusions, plus SHA-256 manifests;
- the code of the meter, the collection scripts and the analysis, with automated tests;
- the exact library versions, the Docker image and the automatic reproduction check;
- the official results and the record of incidents and deviations.

**Not in the repository:** the DaCapo archive (downloaded from the official site and checked by SHA-256) and each
process's DaCapo `scratch` working folders, which are listed in the manifests and included in the full session
packages. The full packages will be published on Zenodo with a DOI, which will be added here.

---

## ⚠️ Limitations

- Energy is that of the **processor package** (RAPL), not wall-socket energy and not the JVM alone; RAPL is the
  processor's own estimate, without external calibration.
- A single machine (laptop) and a single operating system; absolute values do not generalize to other hardware.
- Criterion E2 was not met (6.1% across sessions, limit 5%): compare within-block ratios, not absolute energy across
  days.
- Three DaCapo workloads, one thread and a fixed 1 GB heap; other workloads and settings may behave differently.

---

## 📜 Licenses

- **Code** (`analise/`, `medidor-java/`, `scripts/`): MIT license, in [`LICENSE`](LICENSE).
- **Data, results, evidence and configuration** (`dados/`, `resultados/`, `evidencias/`, `config/`): Creative Commons
  Attribution 4.0 International (CC BY 4.0), in [`LICENCA-DADOS.txt`](LICENCA-DADOS.txt).
- DaCapo (Apache-2.0, with each application's own license) and the Eclipse Temurin JDKs keep their own licenses and
  are not part of this repository.

---

## 📝 How to cite

Citation metadata is in [`CITATION.cff`](CITATION.cff); GitHub shows a ready reference under
**"Cite this repository"**. In BibTeX:

```bibtex
@software{goncalves_pae_jvm_2026,
  author  = {Gonçalves, Everton Cezar},
  title   = {{PAE-JVM – Protocolo de Avaliação Energética de configurações da JVM: dados, análise e código}},
  year    = {2026},
  version = {1.1},
  url     = {https://github.com/evertoncg10/java-energy-study}
}
```

**Author:** Everton Cezar Gonçalves – Federal University of Technology – Paraná (UTFPR), Brazil –
ORCID [0009-0003-7548-2501](https://orcid.org/0009-0003-7548-2501).

---

## 📖 Glossary of Portuguese terms

| Portuguese | English |
|---|---|
| analisar / análise | analyze / analysis |
| bloco | block |
| brutos (dados) | raw (data) |
| código de sorteio / semente | random draw code / seed |
| coleta | data collection |
| conferir / conferência / CONFERE | check / verification / passes |
| configuração | configuration |
| critério | criterion |
| desvio | deviation |
| evidências | evidence |
| executar | run |
| figuras | figures |
| hipótese | hypothesis |
| liberar leitura | allow reading |
| manifesto | manifest (list of files with SHA-256) |
| medidor | meter |
| planejar / plano | plan |
| preparar | prepare |
| razão | ratio |
| registro prévio | pre-registration |
| resultados | results |
| retomar | resume |
| saída | output |
| sessão | session |
