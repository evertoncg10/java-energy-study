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

This repository stores everything used in a master's research project on **Green Software**, in the field of Software
Engineering, including the measurement protocol, the code, the raw data, the evidence and the statistical analysis.

The starting point is a practical doubt that is simple to state. When we change the Java version, does the program
end up using more or less energy? To answer it with confidence, however, we first need to know how to measure well,
and that is what this research focuses on.

The focus, therefore, is **how to measure**, reliably and reproducibly, the effect of versions and options of the Java
Virtual Machine (**JVM**) on energy and execution time, using only a personal computer. To evaluate the protocol built
for this purpose, we applied it to a real case, in which we compared the processor energy and the execution time of three
versions of the **Eclipse Temurin** distribution, **JDKs 17, 21 and 25**, and also JDK 25 **with and without Compact
Object Headers** (JEP 519), a new feature that promises to reduce memory use. The formal research questions are in
the [Research questions](#-research-questions) section.

The research follows the **Design Science Research (DSR)** method. This means that, besides measuring, we built and
evaluated an artifact, **PAE-JVM** (*Protocolo de Avaliação Energética de configurações da JVM*, an energy evaluation
protocol for JVM configurations). It brings together an energy meter integrated with the DaCapo benchmark suite, a
verified JDK selection for every run, an orchestrator that organizes the measurement sessions, and a set of rules for
dealing with noise, failures and analysis. The data collection served precisely to evaluate this protocol. The
evaluation criteria (E1 to E7) and the hypotheses (H1 to H5) were registered **before** the collection, in
[`config/registro-previo.json`](config/registro-previo.json), so that the results could not influence the rules.

If you want to check the data, re-run the analysis or even repeat the measurements on another computer, you will find
the whole path here, explained step by step in [How to reproduce](#-how-to-reproduce).

> The code, scripts, file names and program messages are in Portuguese. This English README explains each step and
> translates the messages you will see along the way; there is also a glossary at the end.

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

The main question, from the DSR point of view, is about the method, that is, **how can we evaluate, reliably and
reproducibly, the effect of JVM versions and options on energy and execution time on a personal computer, without an
external power meter?** Many developers and researchers only have their own laptop to work with, and PAE-JVM was
designed for exactly that situation.

To test the protocol in practice, we applied it to two concrete questions:

- **QC1.** When Compact Object Headers are turned on in Eclipse Temurin 25, what changes in processor energy and
  execution time for the same task? And does that change happen for the expected reason, that is, less memory in use
  and less work for the garbage collector?
- **QC2.** When we move from Temurin 17 to 21, and from 21 to 25, does energy change in the same proportion as time?

---

## ☕ Configurations compared

We compared four configurations, always using the Eclipse Temurin distribution installed through SDKMAN:

| Configuration | JDK (Eclipse Temurin) | SDKMAN identifier | Specific option |
|---|---|---|---|
| **A** | 17.0.19+10 | `17.0.19-tem` | – |
| **B** | 21.0.11+10-LTS | `21.0.11-tem` | – |
| **C** | 25.0.3+9-LTS | `25.0.3-tem` | `-XX:-UseCompactObjectHeaders` (off) |
| **D** | 25.0.3+9-LTS | `25.0.3-tem` | `-XX:+UseCompactObjectHeaders` (on) |

To keep the comparison fair, everything else stayed the same across the four configurations, with the **G1** garbage collector
(`-XX:+UseG1GC`), a fixed **1 GB** heap (`-Xms1g -Xmx1g`), garbage collection logging turned on (`-Xlog:gc`), the
workload running with **1 thread**, and the process pinned to the processor's performance cores (one logical CPU per
physical core).

One important safeguard is that, before every run, the program asks the JVM itself which version, vendor and installation
folder it is using, whether G1 is active, and whether Compact Object Headers are on or off. If any answer differs
from what is expected, the run does not even start. This way we know for sure that each measurement belongs to the
right configuration.

We make three comparisons, **B/A** (from 17 to 21), **C/B** (from 21 to 25) and **D/C** (Compact Object Headers on
versus off, on the same JDK 25).

---

## 📦 Workloads (DaCapo)

As the workload, we used the **DaCapo 23.11-MR2-chopin** suite ([official site](https://www.dacapobench.org/)), a
collection of real Java applications widely used in JVM research. We chose three applications, all with the
`default` input size and 1 thread:

| Workload | Role | What it does | Warm-up iterations | Measured iterations |
|---|---|---|---|---|
| **lusearch** | main | text search with Apache Lucene | 1 | 3 |
| **pmd** | main | static analysis of Java code | 7 | 3 |
| **avrora** | exploratory | AVR microcontroller simulation | 12 | 3 |

The JVM needs a few rounds to "warm up", that is, for the JIT compiler to optimize the code and for the time of each
round to settle. That is why each application first runs a few warm-up iterations, which are not measured, and only
then the 3 measured iterations. The number of warm-up iterations for each application was set during the pilot runs,
whose data are in `dados/piloto/`.

The two main workloads, lusearch and pmd, are the ones that answer the hypotheses. avrora runs in the same blocks but
was left out of the conclusions because it varied a lot in the pilots. It uses the processor lightly, which makes it
more sensitive to whatever is happening in the background.

---

## ⚡ How energy is measured

Intel processors have a built-in energy counter called **RAPL** (*Running Average Power Limit*), which Linux exposes
in the file `/sys/class/powercap/intel-rapl:0/energy_uj`. We used the **processor package** counter, which covers the
whole processor, including all cores, the cache and the integrated memory controller. It is worth keeping this in mind when
reading the results, because the value is neither the energy of the JVM alone nor the energy drawn from the wall
socket.

The counter is read by a small meter written in Java, in the [`medidor-java/`](medidor-java/) folder. It runs as a
DaCapo *callback*, inside the very JVM being measured, so it knows exactly when each iteration starts and ends. During
the run, the meter reads the counter every **100 ms** and handles the moment when the counter "wraps around" and
starts again from zero.

Before each process, the program also measures energy with the machine idle for 10 seconds, which records the idle
power at that moment. And to find out whether the meter itself disturbs the measurement, we compare the time of the
measured iterations with that of the last warm-up iteration (this is criterion E4).

---

## 🧪 Collection design

Energy measurement is sensitive to many things, such as temperature, system tasks and even the order in which runs happen. The
collection was designed to keep these effects under control.

Runs were organized in **complete blocks**. Each block contains all 12 possible combinations (3 workloads × 4
configurations), in a randomly drawn order. There were **15 blocks, for a total of 180 processes**, that is, 15
measurements for each combination. Each process is a **fresh JVM**, started from scratch, so that no run inherits the
state of the previous one.

The 15 blocks were split into **4 sessions**, held on different days, with 4, 4, 4 and 3 blocks. Each session used its
own random draw code, from **20261101 to 20261104**, and each session's plan, with the exact order of the processes,
was written **before** the session started. Every session begins with a machine warm-up run (`pmd` in configuration
B), which is left out of the analysis.

Between one process and the next, the program waits at least 10 seconds and then waits for the processor to cool
down to no more than 8 °C above the idle temperature measured at the start of the session, waiting 120 seconds at
most. If a process fails, it is retried once at the end of the same block, and the failure stays on record. If there
are three failures in a row, the session stops so the problem can be investigated. The official collection had no
failures at all.

Before each process, the program also checks that the charger is connected, that no "hidden" Java options are set in
environment variables (such as `JAVA_TOOL_OPTIONS`), that the meter and DaCapo are exactly the registered files (by
SHA-256), and that the RAPL counter is moving.

Finally, everything is kept. Each process records the command used, the JVM identity, the system state before and
after, the garbage collection log, the meter readings and the result. At the end of each session, a manifest records
the SHA-256 of every file, which makes it possible to prove later that nothing was changed.

All these parameters are fixed in [`config/execucao.json`](config/execucao.json) (its status is `fixado`, meaning
frozen).

---

## 💻 Original collection environment

The measurements were taken on a personal laptop with the following setup:

| Item | Value |
|---|---|
| Processor | Intel Core i7-13650HX (6 performance + 8 efficiency cores, 20 logical CPUs) |
| Affinity used | logical CPUs 0, 2, 4, 6, 8, 10 (one per performance core) |
| Memory | 16 GB |
| System | Zorin OS (Ubuntu based), Linux kernel 7.0.0-38-generic, installed on bare metal |
| Power | laptop on the charger; power profile "balanced"; `powersave` governor; turbo on |
| JDK selection | SDKMAN 5.23.0 (`sdk use` only in the child process; system default Java untouched) |
| Meter | Java 17 (Maven), SHA-256 `415ddd80…26339995` |

If you need more detail, the full system state at the start and end of each session is in
`dados/brutos/<session>/<session>-ambiente-inicial.json` and `-ambiente-final.json`. For each process, the files
`system-before.json` and `system-after.json` show the state of the machine before and after the run.

---

## 📏 Metrics

For each process, we compute the following measures:

| Metric | Unit | Definition |
|---|---|---|
| Energy (E) | J | mean of the process's 3 measured iterations (package energy per iteration) |
| Time (t) | s | mean of the 3 measured iterations |
| Mean power (P) | W | sum of energies ÷ sum of times of the measured iterations (P = E / t) |
| Garbage collections | count | pauses recorded in the GC log over the whole process |
| GC pauses | ms | sum of pauses over the whole process |
| Heap after GC | MB | median heap occupancy after each collection |
| Meter overhead | % | mean time of measured iterations ÷ time of the last warm-up − 1 |

Mean power helps explain *why* there is a difference in energy. A configuration may use less energy because it
finishes sooner, at the same power, or because it demands less from the processor, with lower power over a similar
time. These are different explanations, and power tells them apart.

---

## 📊 Statistical analysis, criteria and hypotheses

To compare two configurations, we use the **ratio of medians**. For example, a D/C energy ratio of 0.98 means that
configuration D used 2% less energy than C. The uncertainty of this ratio is given by a **95% confidence interval**
computed with a block-paired *bootstrap*, with 10,000 resamples and random draw code 20261101. "Block-paired" means
that each comparison is made between runs of the same block, which ran close together in time and under the same
machine conditions.

The `razoes.csv` file also includes complementary tests, such as Mann-Whitney U with Holm correction and the Vargha-Delaney
A12 effect size. On top of that, we ran an exploratory sensitivity analysis, which was not in the pre-registration,
using the Friedman test, blocked ANOVA on logs, paired t-test on logs and exact Wilcoxon, all with Holm correction. Its
purpose is to check whether the conclusions would change with other methods.

The protocol was evaluated against seven criteria, defined before the collection:

| Criterion | Measure | Limit |
|---|---|---|
| E1 Repeatability | energy CV per workload × configuration | ≤ 5% for main workloads |
| E2 Reproducibility across sessions | largest ÷ smallest session median energy − 1 | ≤ 5% for main workloads |
| E3 Sensitivity | half-width of the 95% CI of the D/C energy ratio | ≤ 3 percentage points |
| E4 Intrusion | meter overhead (median) | ≤ 2% |
| E5 Traceability | processes with complete evidence | 100% |
| E6 Feasibility | machine time per session and failures | ≤ 1h30 per session; failures ≤ 5% |
| E7 Naive comparison | measurement without warm-up, pinned cores or random order | descriptive |

And these are the hypotheses, also registered in advance, with the rule that decides each one:

| Hypothesis | Statement | Confirmed if | Refuted if |
|---|---|---|---|
| H1 | Lower energy in D than in C | 95% CI of D/C energy entirely below 1 | entirely above 1 |
| H2 | The D/C energy change follows the time change (no relevant power change) | 95% CI of D/C power within [0.98, 1.02] | CI excludes 1 |
| H3a | Lower heap occupancy after GC in D | 95% CI of D/C entirely below 1 | – |
| H3b | Fewer collections or less pause time in D | 95% CI of at least one ratio entirely below 1 | – |
| H4 | Largest energy reduction in the workload with the largest heap reduction | exploratory, descriptive | – |
| H5 | In B/A and C/B, energy follows time | 95% CI of power within [0.98, 1.02] | – |

The verdicts use four terms that are common in confirmatory Software Engineering studies (the output files show them
in Portuguese). A hypothesis is **confirmada** (confirmed) when its confirmation rule is met and **refutada**
(refuted) when its refutation rule is met. When a hypothesis has both rules and neither is met, it is
**inconclusiva** (inconclusive). When a hypothesis only has a confirmation rule and that rule is not met, it is
**não confirmada** (not confirmed). The full reasoning behind these terms is in
[`evidencias/base-oficial/NOTA_TERMOS_VEREDITOS.txt`](evidencias/base-oficial/NOTA_TERMOS_VEREDITOS.txt).

---

## 📈 Main results

The table below summarizes the main workloads. Each cell shows the ratio of medians and, in brackets, the 95%
confidence interval. The complete results, with every workload and measure, are in
[`resultados/oficial-20261101-termos/resumo.txt`](resultados/oficial-20261101-termos/resumo.txt).

| Workload | Comparison | Energy | Time | Mean power |
|---|---|---|---|---|
| lusearch | B/A (17 → 21) | 0.9335 [0.9192, 0.9479] | 0.9468 [0.9405, 0.9519] | 0.9835 [0.9761, 0.9970] |
| lusearch | C/B (21 → 25) | 1.0202 [1.0104, 1.0271] | 1.0101 [1.0049, 1.0127] | 1.0152 [1.0070, 1.0161] |
| lusearch | D/C (compact) | 0.9955 [0.9888, 1.0175] | 0.9962 [0.9926, 1.0059] | 0.9997 [0.9848, 1.0093] |
| pmd | B/A (17 → 21) | 0.9597 [0.9502, 0.9751] | 0.9486 [0.9423, 0.9503] | 1.0133 [1.0103, 1.0342] |
| pmd | C/B (21 → 25) | 0.9546 [0.9401, 0.9617] | 0.9352 [0.9332, 0.9391] | 1.0142 [1.0052, 1.0260] |
| pmd | D/C (compact) | 1.0037 [0.9903, 1.0154] | 1.0048 [1.0028, 1.0085] | 1.0018 [0.9874, 1.0121] |

In short, moving from Java 17 to 21 reduced energy in both main workloads (about 7% for lusearch and 4% for pmd).
From 21 to 25, pmd saved another 4.5%, while lusearch used 2% more. Compact Object Headers, on the other hand, brought
no detectable change in energy, even though they reduced the garbage collector's work.

The hypothesis verdicts came out as follows:

| Hypothesis | lusearch | pmd |
|---|---|---|
| H1 lower energy in D | inconclusive | inconclusive |
| H2 no D/C power change | confirmed | confirmed |
| H3a smaller heap in D | not confirmed | confirmed |
| H3b fewer collections/pauses in D | confirmed | confirmed |
| H5 B/A energy follows time | not confirmed | not confirmed |
| H5 C/B energy follows time | confirmed | not confirmed |

As for the protocol, criteria E1, E3, E4 (by the median), E5 and E6 were met. Criterion **E2 was not met**, since the
largest energy difference between sessions was 6.1%, above the 5% limit, in the combinations lusearch-A, pmd-A, pmd-B
and pmd-D. Criterion E7 still depends on the naive session. This E2 result is itself an important lesson. Absolute
energy changes from one day to the next, but the ratios between configurations within each block stayed stable
across sessions. That is why we recommend comparing configurations through within-block ratios rather than through
absolute energy measured on different days. All 180 processes were considered valid.

---

## 📂 Repository layout

The repository is organized as follows:

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

Each measured process has its own folder, with a name such as `b01-001-lusearch-A` (block 1, first process of the
session, workload lusearch, configuration A). Inside it you will find:

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

There are two ways to reproduce this work, and each one needs a different amount of preparation.

The first is to **re-run the analysis**. You use the data already in the repository, check that they have not been
changed, and recompute every number from the raw data. It works on any computer (Windows, Linux or macOS) and takes
about 5 minutes.

The second is to **repeat the data collection**, that is, measure everything again on another machine and analyze the
new data. This one needs a computer running Linux with an Intel processor that supports RAPL, plus about 4 hours of
machine time, not counting the setup.

| Level | What it does | Where it runs | Time |
|---|---|---|---|
| **1. Re-run the analysis** | verifies the data and recomputes every number from the raw data in the repository | Windows, Linux or macOS | ~5 min |
| **2. Repeat the data collection** | measures again on another machine and analyzes the new data | Linux with Intel RAPL | ~4 h of machine time + setup |

In both cases, run the commands **in the project's root folder**, which is the folder containing this README, using a
*bash* terminal. On Linux and macOS, just open the Terminal. On Windows, use **Git Bash**, which comes with
[Git for Windows](https://git-scm.com/download/win). Whenever a command is different in PowerShell, the text says so.

---

### 🔁 Level 1 – Re-run the analysis (any computer)

#### Prerequisites

All you need is Git and Python:

| Program | Version | How to check | Where to get it |
|---|---|---|---|
| Git | any recent | `git --version` | <https://git-scm.com/downloads> |
| Python | **3.10 or newer** (official runs: 3.12 and 3.13) | `python --version` or `python3 --version` | <https://www.python.org/downloads/> |
| Disk space | ~300 MB | – | – |
| Internet | only to download the repository and libraries | – | – |

On Windows, when installing Python, remember to tick **"Add python.exe to PATH"**. Without it, the terminal cannot
find Python.

#### Step 1 – Download the repository

Start by downloading the repository and moving into its folder:

```bash
git clone https://github.com/evertoncg10/java-energy-study.git
cd java-energy-study
```

If you want to work with exactly the version used in the published analysis, switch to its tag. This step is
optional:

```bash
git checkout analise-v1.1
```

#### Step 2 – Verify data integrity

Before analyzing anything, it is worth confirming that the data you downloaded are the same data that were measured.
At the end of each session we recorded a manifest with the SHA-256 of every file, and the script below compares the
current files with those manifests:

```bash
bash scripts/conferir_dados.sh
```

If everything is in order, every line shows `CONFERE` (it matches) and the last one says
`RESULTADO: todos os dados conferem com os manifestos.` (all data match the manifests). The script also re-runs the
check of the whole collection, with a summary of each session.

#### Step 3 – Re-run the analysis (option A: one command)

The simplest way is to let a script do all the work:

```bash
bash scripts/reproduzir_analise.sh
```

The first time, it creates a Python virtual environment in `analise/.venv` and installs the libraries in exactly the
versions used in the official analysis. Then it runs the automated tests, re-runs the analysis into a new folder
(`resultados/reproducao-YYYYMMDD-HHMMSS`) and compares the result with the official numbers. Once the installation is
done, the whole process takes about 1 minute. At the end, you should see something like this:

```text
idêntico: razoes.csv
idêntico: resumo.txt
...
Arquivos diferentes: 0
```

Here `idêntico` means identical, and `Arquivos diferentes: 0` means that no file differs. If you also want the
figures, run `bash scripts/reproduzir_analise.sh --com-figuras`.

#### Step 3 – Re-run the analysis (option B: command by command)

If you would rather understand each stage, or if you are using PowerShell or the Command Prompt, follow the commands
below.

1. Create the virtual environment. You only need to do this the first time:

   ```bash
   python -m venv analise/.venv        # if "python" does not exist, use python3
   ```

2. Activate the virtual environment. This has to be done in every new terminal, and the command depends on your
   system:

   | System / terminal | Command |
   |---|---|
   | Windows – Git Bash | `source analise/.venv/Scripts/activate` |
   | Windows – PowerShell | `analise\.venv\Scripts\Activate.ps1` |
   | Windows – Command Prompt (CMD) | `analise\.venv\Scripts\activate.bat` |
   | Linux or macOS | `source analise/.venv/bin/activate` |

   You know it worked when the terminal starts showing `(.venv)` at the beginning of the line. On Windows, also run
   `export PYTHONUTF8=1` (Git Bash) or `$env:PYTHONUTF8=1` (PowerShell), so that accented characters show up
   correctly.

3. Install the libraries in their locked versions and run the tests:

   ```bash
   cd analise
   python -m pip install -r requisitos-travados.txt -e ".[dev,figuras]"
   python -m pytest
   cd ..
   ```

   The tests should end with `41 passed`.

4. Now run the full analysis, with figures:

   ```bash
   pae-analise analisar --saida resultados/reproducao
   ```

   The output folder (`--saida`) has to be new, because the program never overwrites results. To run it again, use
   another name, such as `resultados/reproducao2`. The command accepts a few options, such as `--sem-figuras` (skips the
   figures), `--reamostragens N` (bootstrap resamples, default 10000) and `--semente N` (bootstrap random draw code,
   default 20261101). Only the default values reproduce the official numbers.

5. Finally, compare your result with the official one:

   ```bash
   python scripts/comparar_resultados.py resultados/oficial-20261101-termos resultados/reproducao --ignorar-figuras
   ```

   The expected output is `Arquivos diferentes: 0`. Two details help in reading it. The `metadados.json` file always
   changes, because it records the date, the system and the commit of each run; that is why the script only checks
   its `input_sha256` field, which identifies the input data. The figures are left out with `--ignorar-figuras`
   because they are only byte-identical on the same operating system. The numbers, in the CSV, JSON and text files,
   come out identical on Windows, Linux and macOS.

6. If you only want the consolidated dataset, with one row per process, to work with the data in another tool (a
   spreadsheet, R and so on), use:

   ```bash
   pae-analise consolidar --saida resultados/base
   ```

#### Option C: Docker

If you have [Docker](https://docs.docker.com/get-docker/) installed, you do not even need Python. Just build the image
and run it:

```bash
docker build -t pae-jvm-analise .
docker run --rm pae-jvm-analise
```

The container re-runs the analysis and prints the comparison with the official results. Here too, the expected
output is `Arquivos diferentes: 0`. If you want to keep the full analysis, with figures, in the
`resultados/reproducao-docker` folder on your computer, use:

```bash
docker run --rm -v "$(pwd)/resultados:/saida" pae-jvm-analise pae-analise analisar --saida /saida/reproducao-docker
```

In PowerShell, replace `$(pwd)` with `${PWD}`.

#### Files produced by the analysis

The analysis output folder contains the following files:

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

The best place to start is `resumo.txt`, which brings the main numbers together in plain text.

#### Automatic checks

You do not have to take our word for it. On every change to the repository, GitHub Actions
([`.github/workflows/analise.yml`](.github/workflows/analise.yml)) installs the locked versions, checks style (ruff),
types (mypy) and tests (pytest), verifies the integrity of the data, re-runs the analysis and compares the result with
the official one. It also builds and runs the Docker image.

---

### 🔬 Level 2 – Repeat the data collection (Linux with Intel RAPL)

Repeating the collection means measuring everything again, on another computer. It is worth setting expectations
right away. Absolute energy values depend on the hardware, so they will not match ours. What you should expect to
reproduce is the **direction and size of the ratios** between configurations, using the same protocol.

#### Prerequisites

The collection has much more specific requirements than the analysis, because it depends on the processor's energy
counter:

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

To install the programs on Ubuntu, Debian, Zorin OS or Mint, use:

```bash
sudo apt update
sudo apt install git python3 python3-venv curl unzip zip coreutils maven
```

To install SDKMAN, use the commands below (and then open a new terminal):

```bash
curl -s "https://get.sdkman.io" | bash
source "$HOME/.sdkman/bin/sdkman-init.sh"
sdk install java 21.0.11-tem      # serves as default Java; does not affect the collection
```

If your processor is not an Intel hybrid, the collection still works, but you need to turn off core affinity. The
section [Adapting to other hardware](#adapting-to-other-hardware) explains how.

#### Step 1 – Download the repository

```bash
git clone https://github.com/evertoncg10/java-energy-study.git
cd java-energy-study
```

#### Step 2 – Prepare the environment

We provide a script that prepares the machine in one go:

```bash
bash scripts/preparar_ambiente_coleta.sh
```

It starts by checking the system. Then it installs JDKs `17.0.19-tem`, `21.0.11-tem` and `25.0.3-tem` through SDKMAN,
without touching your computer's default Java. Next, it downloads DaCapo from the official URL recorded in
[`ferramentas/dacapo.json`](ferramentas/dacapo.json), checks the file's official SHA-256 and extracts it into
`ferramentas/dacapo/`. Finally, it installs the DaCapo JAR into the local Maven repository, builds and tests the
meter, and compares the SHA-256 values with those recorded in [`config/execucao.json`](config/execucao.json).

Each output line shows `[ok]`, `[aviso]` (warning) or `[erro]` (error), so you know what happened. You can run the
script as many times as you need, because whatever is already in place is only checked. The DaCapo download can take anywhere
from a few minutes to a few hours, depending on your connection.

<details>
<summary>Prefer to do it by hand? Here is the same step, command by command</summary>

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

The SHA-256 of the meter you built may turn out different from the original. This happens when the compiler or the
Maven version is not exactly the same. The code is identical but, to be safe, the program refuses a JAR that does not
match. In that case, make a copy of the configuration, record the new value in it, and note this as a protocol
deviation:

```bash
cp config/execucao.json config/replicacao.json
sha256sum medidor-java/target/java-energy-meter-0.1.0.jar
# edit config/replicacao.json: replace "meter" → "sha256" with the value shown above
```

From then on, add `--config config/replicacao.json` to the commands in steps 4 and 6.

#### Step 3 – Allow reading the RAPL counter

For security, Linux only lets the administrator read the energy counter. The command below allows your user to read
just that counter. It will ask for your `sudo` password in the terminal itself; the program never sees or stores the
password.

```bash
bash scripts/executar.sh preparar --configuracao A --liberar-leitura
```

This permission lasts until the computer restarts. After a restart, just run the command again. For the curious, it
is equivalent to `sudo chown $(id -u) /sys/devices/virtual/powercap/intel-rapl/intel-rapl:0/energy_uj`.

#### Step 4 – Verification run

Before the real collection, do a test run. It stays outside the sample and is written to `dados/verificacao/`, a
folder that Git does not track:

```bash
bash scripts/executar.sh executar --configuracao D --aplicacao pmd
```

If everything is right, you will see a JSON line ending with `"status": "success"`. This single test already
confirms that SDKMAN, the JDK, Compact Object Headers, RAPL, core affinity, DaCapo and the meter are all working.

#### Step 5 – Prepare the machine before each session

Each session takes about 1 hour (the fourth, which is shorter, takes about 47 minutes). Since any parallel activity
interferes with the measured energy, prepare the machine before you start:

1. Connect the charger and keep it connected until the end.
2. Close every other program, including the browser, editors, cloud sync and antivirus scans.
3. Turn off automatic suspend and the screen saver for the session.
4. Do not use the computer while the session is running.
5. Leave the machine idle for a few minutes before starting, because the temperature measured at the start defines
   the pauses for the session.
6. Make sure the RAPL counter is readable (step 3).

#### Step 6 – Plan the sessions

The next step is to write the session plans. The script below creates the 4 plans with the same design as the
original collection (15 blocks split as 4 + 4 + 4 + 3, with random draw codes 20261101 to 20261104) and saves them in a
folder outside the repository:

```bash
bash scripts/planejar_sessoes_oficiais.sh ../planos-pae-jvm
# if you created a replication configuration:
# bash scripts/planejar_sessoes_oficiais.sh ../planos-pae-jvm config/replicacao.json
```

Because the random draw codes are the same, the order of the processes comes out **identical** to the original
collection. We checked this by comparing the generated plans with the `plano-antes-execucao.json` files of the 4
sessions. If you want to create one plan at a time, this is the command:

```bash
python3 scripts/sessao.py planejar --config config/execucao.json --categoria oficial \
  --blocos 4 --primeiro-bloco 1 --semente 20261101 --plano ../planos-pae-jvm/plano-sessao1.json
```

In it, `--blocos` is the number of blocks, `--primeiro-bloco` the number of the first block, `--semente` the random
draw code and `--plano` the plan file.

#### Step 7 – Run the sessions

Run one session at a time, preferably on different days, and repeat step 5 before each one:

```bash
python3 scripts/sessao.py executar --plano ../planos-pae-jvm/plano-sessao1.json
```

During the session, the terminal prints `ok` or `FALHA` (failure) for each process. At the end it shows
`SESSAO=dados/brutos/<session folder>`, with the name of the folder where the data were saved. If the session is
interrupted, by a power cut for example, you can pick up where it stopped without repeating what was already done:

```bash
python3 scripts/sessao.py executar --plano ../planos-pae-jvm/plano-sessao1.json --retomar
```

Then do the same with `plano-sessao2.json`, `plano-sessao3.json` and `plano-sessao4.json`.

#### Step 8 – Freeze and check each session

As soon as each session finishes, write its manifest and check the quality of the data. Replace `PASTA` with the
folder name shown in `SESSAO=`:

```bash
python3 scripts/manifesto.py gerar --sessao dados/brutos/PASTA \
  --saida ../manifestos-pae-jvm/sessao1.json --plano ../planos-pae-jvm/plano-sessao1.json
python3 scripts/conferir_sessao.py --sessao dados/brutos/PASTA
```

The manifest records the SHA-256 of every file in the session, and the program never overwrites an existing manifest.
The check shows the duration, failures, temperatures, reading coverage and CV of each combination, and ends with
`CONFERE` (all good) or `NAO_CONFERE` (something is wrong). Once all 4 sessions are done, check the whole collection,
which includes criterion E2:

```bash
python3 scripts/conferir_coleta.py \
  --sessao dados/brutos/PASTA1 --manifesto ../manifestos-pae-jvm/sessao1.json \
  --sessao dados/brutos/PASTA2 --manifesto ../manifestos-pae-jvm/sessao2.json \
  --sessao dados/brutos/PASTA3 --manifesto ../manifestos-pae-jvm/sessao3.json \
  --sessao dados/brutos/PASTA4 --manifesto ../manifestos-pae-jvm/sessao4.json
```

#### Step 9 – Analyze the new data

The analysis reads **all** sessions in `dados/brutos/` and all manifests `evidencias/manifestos/sessao*.json`. To
analyze only your own data, move the 4 original sessions and their manifests out of those folders and put your
manifests in their place. Do not worry about the originals, because Git keeps all of them.

```bash
mkdir -p ../originais-pae-jvm
mv dados/brutos/20261022T2152* ../originais-pae-jvm/
mv evidencias/manifestos/sessao*.json ../originais-pae-jvm/
cp ../manifestos-pae-jvm/sessao*.json evidencias/manifestos/
```

Git will show those files as deleted, which is expected. To go back to the original state later, use
`git checkout -- dados/brutos evidencias/manifestos`.

Next, activate the analysis environment (Level 1, step 3, items 1 to 3) and run:

```bash
pae-analise analisar --saida resultados/replicacao
```

To evaluate the replication, compare your `resultados/replicacao/resumo.txt` with the official one, especially the
D/C, C/B and B/A ratios.

#### Adapting to other hardware

Not every computer is like the one we used. If you need to change something in the protocol, make the change in a
**copy** of the configuration (for example, `config/replicacao.json`) and record the change as a deviation. These are
the most common situations:

| Situation | What to change in the copy |
|---|---|
| Processor without hybrid cores (no `/sys/devices/cpu_core`) | `"cpu_affinity": null` |
| RAPL counter at another path | `"rapl_directory"` with the path of the `package-0` domain |
| Different meter SHA-256 | `"meter"` → `"sha256"` with the new value |

The JDKs, DaCapo, workloads, iterations, heap and pauses should not change. If they do, what you have is a new
experiment, not a repetition of this protocol.

---

## 🛠️ Troubleshooting

Here are the most common problems and what to do in each case. The messages appear in Portuguese because that is the
program's language, so each one comes with a translation.

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

Two versions of the repository are marked with Git tags, so they can be retrieved at any time:

| Tag | Content |
|---|---|
| `base-oficial-v1` | official dataset closed after collection, results in `resultados/oficial-20261101` |
| `analise-v1.1` | same numbers, with verdicts in the terms confirmada, não confirmada, refutada and inconclusiva (`resultados/oficial-20261101-termos`) |

The [`evidencias/base-oficial/`](evidencias/base-oficial/) folder explains how the official results were produced and
includes the incident record and the checksums.

---

## 🌍 Open science

This work follows **Open Science** practices, and everything that supports the results is available to anyone who wants
to check it. That includes the frozen protocol and the pre-registration of criteria, hypotheses and decision rules,
written before the collection; the raw data of all 180 official processes and of the pilots, with no exclusions, along
with the SHA-256 manifests; the code of the meter, the collection scripts and the analysis, with automated tests; the
exact library versions, the Docker image and the automatic reproduction check; and, finally, the official results
together with the record of incidents and deviations.

Only two things are kept out of the repository, because of their size. The first is the DaCapo archive, which can be
downloaded from the official site and checked by its SHA-256. The second is the working folders (`scratch`) that
DaCapo creates for each process. They are listed in the manifests and are part of the full session packages, which
will be published on Zenodo with their own DOI, to be added here.

---

## ⚠️ Limitations

Like any research, this one has limits that should be kept in mind when reading the results. The energy measured is
that of the **processor package**, through RAPL. It is not wall-socket energy, nor the energy of the JVM alone, and
RAPL is the processor's own estimate, without external calibration. All measurements came from a single machine, a
laptop, with a single operating system, so the absolute values do not carry over to other hardware. Criterion E2 was
not met (a 6.1% difference between sessions, against a 5% limit), which reinforces the recommendation to compare
within-block ratios rather than absolute energy across different days. Lastly, we used three DaCapo workloads, with
one thread and a fixed 1 GB heap; other workloads and settings may behave differently.

---

## 📜 Licenses

The **code** (the `analise/`, `medidor-java/` and `scripts/` folders) is under the MIT license, described in
[`LICENSE`](LICENSE). The **data, results, evidence and configuration** (the `dados/`, `resultados/`, `evidencias/`
and `config/` folders) are under the Creative Commons Attribution 4.0 International license (CC BY 4.0), described in
[`LICENCA-DADOS.txt`](LICENCA-DADOS.txt). DaCapo (Apache-2.0, with each application's own license) and the Eclipse
Temurin JDKs keep their own licenses and are not part of this repository.

---

## 📝 How to cite

If this work is useful to you, please cite it. The citation metadata is in [`CITATION.cff`](CITATION.cff), and GitHub
shows a ready-made reference under the **"Cite this repository"** button. In BibTeX:

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

Since the code and the messages are in Portuguese, this list may help you find your way around:

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
