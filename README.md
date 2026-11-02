# PAE-JVM: Eficiência Energética de JVMs – Temurin 17 vs 21 vs 25 e cabeçalhos compactos

[![Java Support](https://img.shields.io/badge/Java-17%20%7C%2021%20%7C%2025-orange?logo=openjdk)](#-configurações-comparadas)
[![Python Analysis](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](#-nível-1--refazer-a-análise-qualquer-computador)
[![Open Science](https://img.shields.io/badge/Open%20Science-Compliant-success)](#-ciência-aberta)
[![DaCapo](https://img.shields.io/badge/DaCapo-23.11--MR2--chopin-informational)](#-cargas-de-trabalho-dacapo)
[![Energia](https://img.shields.io/badge/Energia-Intel%20RAPL-lightgrey)](#-como-a-energia-é-medida)
[![Docker](https://img.shields.io/badge/Docker-an%C3%A1lise-2496ED?logo=docker&logoColor=white)](#opção-c-docker)
[![Código: MIT](https://img.shields.io/badge/C%C3%B3digo-MIT-yellow)](LICENSE)
[![Dados: CC BY 4.0](https://img.shields.io/badge/Dados-CC%20BY%204.0-lightgrey)](LICENCA-DADOS.txt)

🇧🇷 Português | 🇺🇸 [English](README.en.md)

Este repositório reúne o protocolo, o código, os dados brutos, as evidências e a análise estatística de uma pesquisa
de mestrado em **Software Verde** (Engenharia de Software) que mede o consumo de energia do processador e o tempo de
execução de versões e opções da máquina virtual Java (**JVM**) da distribuição **Eclipse Temurin**: **JDK 17, 21 e 25**,
e o JDK 25 **com e sem cabeçalhos compactos de objeto** (*Compact Object Headers*, JEP 519).

A pesquisa segue o método **Design Science Research (DSR)**. O artefato construído é o **PAE-JVM – Protocolo de
Avaliação Energética de configurações da JVM**: medidor integrado à suíte DaCapo, seleção verificada do JDK,
orquestrador de sessões, regras de ruído, de falha e de análise. A coleta experimental é a avaliação desse artefato,
com critérios (E1 a E7) e hipóteses (H1 a H5) registrados **antes** da coleta em
[`config/registro-previo.json`](config/registro-previo.json).

Tudo o que é preciso para conferir os dados, refazer a análise e repetir a coleta está aqui, com o passo a passo
completo na seção [Como reproduzir](#-como-reproduzir).

---

## 📑 Sumário

- [Perguntas da pesquisa](#-perguntas-da-pesquisa)
- [Configurações comparadas](#-configurações-comparadas)
- [Cargas de trabalho (DaCapo)](#-cargas-de-trabalho-dacapo)
- [Como a energia é medida](#-como-a-energia-é-medida)
- [Desenho da coleta](#-desenho-da-coleta)
- [Ambiente da coleta original](#-ambiente-da-coleta-original)
- [Métricas](#-métricas)
- [Análise estatística, critérios e hipóteses](#-análise-estatística-critérios-e-hipóteses)
- [Principais resultados](#-principais-resultados)
- [Estrutura do repositório](#-estrutura-do-repositório)
- [Como reproduzir](#-como-reproduzir)
  - [Nível 1 – Refazer a análise (qualquer computador)](#-nível-1--refazer-a-análise-qualquer-computador)
  - [Nível 2 – Repetir a coleta (Linux com Intel RAPL)](#-nível-2--repetir-a-coleta-linux-com-intel-rapl)
- [Solução de problemas](#-solução-de-problemas)
- [Versões marcadas](#-versões-marcadas)
- [Ciência aberta](#-ciência-aberta)
- [Limitações](#-limitações)
- [Licenças](#-licenças)
- [Como citar](#-como-citar)

---

## ❓ Perguntas da pesquisa

**Pergunta de projeto (DSR):** como avaliar, de forma confiável e reprodutível, o efeito de versões e opções da JVM
sobre a energia e o tempo de execução em um computador pessoal sem medidor externo?

**Perguntas de conhecimento:**

- **QC1.** Ao ativar os cabeçalhos compactos no Eclipse Temurin 25, o que muda na energia do processador e no tempo
  de execução da mesma tarefa, e essa mudança segue o mecanismo esperado (menor ocupação de memória e menos trabalho
  de coleta de lixo)?
- **QC2.** Nas atualizações do Temurin 17 para o 21 e do 21 para o 25, a mudança de energia acompanha a mudança de
  tempo?

---

## ☕ Configurações comparadas

| Configuração | JDK (Eclipse Temurin) | Identificador no SDKMAN | Opção específica |
|---|---|---|---|
| **A** | 17.0.19+10 | `17.0.19-tem` | – |
| **B** | 21.0.11+10-LTS | `21.0.11-tem` | – |
| **C** | 25.0.3+9-LTS | `25.0.3-tem` | `-XX:-UseCompactObjectHeaders` (desligado) |
| **D** | 25.0.3+9-LTS | `25.0.3-tem` | `-XX:+UseCompactObjectHeaders` (ligado) |

Opções comuns a todas: coletor **G1** (`-XX:+UseG1GC`), heap fixo de **1 GB** (`-Xms1g -Xmx1g`), log de coleta de lixo
(`-Xlog:gc`), **1 thread** da carga e afinidade aos núcleos de desempenho (um processador lógico por núcleo físico).
Antes de cada processo, o programa confere a versão completa, o fornecedor, o `java.home`, o G1 e o estado dos
cabeçalhos compactos efetivamente ativos na JVM; se algo divergir, o processo não roda.

Comparações: **B/A** (17 → 21), **C/B** (21 → 25) e **D/C** (cabeçalhos compactos ligados contra desligados).

---

## 📦 Cargas de trabalho (DaCapo)

Suíte **DaCapo 23.11-MR2-chopin** ([site oficial](https://www.dacapobench.org/)), entrada `default`, 1 thread.

| Carga | Papel | O que faz | Iterações de preparação | Iterações medidas |
|---|---|---|---|---|
| **lusearch** | principal | busca de texto com Apache Lucene | 1 | 3 |
| **pmd** | principal | análise estática de código Java | 7 | 3 |
| **avrora** | exploratória | simulação de microcontroladores AVR | 12 | 3 |

O número de preparações (*warm-up*) de cada carga foi definido nos pilotos (dados em `dados/piloto/`). As cargas
principais respondem às hipóteses; a avrora roda nos mesmos blocos, mas fica fora das conclusões, porque variou
muito nos pilotos.

---

## ⚡ Como a energia é medida

- **Fonte:** contador de energia do **pacote do processador** pela interface **Intel RAPL** do Linux
  (`/sys/class/powercap/intel-rapl:0/energy_uj`). Mede o processador inteiro (todos os núcleos, cache e controlador
  de memória integrado), não só a JVM nem a energia da tomada.
- **Medidor:** projeto Java em [`medidor-java/`](medidor-java/), executado como *callback* da DaCapo dentro da
  própria JVM. Lê o contador a cada **100 ms**, trata a volta do contador e marca o início e o fim exatos de cada
  iteração da DaCapo.
- **Linha de base ociosa:** antes de cada processo, 10 s de leitura sem carga (potência ociosa registrada).
- **Sobrecarga do medidor:** comparação do tempo das iterações medidas com o da última preparação (critério E4).

---

## 🧪 Desenho da coleta

- **Blocos completos e aleatorizados:** cada bloco tem as 12 combinações (3 cargas × 4 configurações), em ordem
  sorteada. Total de **15 blocos = 180 processos** (15 por combinação). Cada processo é uma **JVM nova**.
- **Sessões:** os 15 blocos foram divididos em **4 sessões** (4 + 4 + 4 + 3 blocos), em dias diferentes, com códigos
  de sorteio **20261101 a 20261104**. O plano de cada sessão é gravado **antes** da execução.
- **Aquecimento da máquina:** cada sessão começa com um processo `pmd`/B que não entra na análise.
- **Pausas:** pelo menos 10 s entre processos e espera até a temperatura do pacote voltar a no máximo 8 °C acima da
  temperatura ociosa medida no início da sessão (limite de 120 s de espera).
- **Falhas:** um processo que falha é repetido uma vez no fim do mesmo bloco; a falha fica registrada. Três falhas
  seguidas interrompem a sessão. Na coleta oficial houve **0 falhas**.
- **Controles antes de cada processo:** carregador ligado, nenhuma opção Java herdada do ambiente
  (`JAVA_TOOL_OPTIONS` etc.), SHA-256 do medidor e da DaCapo iguais aos registrados, contador RAPL avançando.
- **Rastreabilidade:** cada processo guarda comando, identidade da JVM, estado do sistema antes e depois, log de GC,
  leituras do medidor e resultado. Ao fim de cada sessão, um manifesto grava o SHA-256 de todos os arquivos.

Parâmetros fixos da coleta: [`config/execucao.json`](config/execucao.json) (estado `fixado`).

---

## 💻 Ambiente da coleta original

| Item | Valor |
|---|---|
| Processador | Intel Core i7-13650HX (6 núcleos de desempenho + 8 de eficiência, 20 processadores lógicos) |
| Afinidade usada | processadores lógicos 0, 2, 4, 6, 8, 10 (um por núcleo de desempenho) |
| Memória | 16 GB |
| Sistema | Zorin OS (base Ubuntu), kernel Linux 7.0.0-38-generic, instalado direto na máquina |
| Energia | notebook ligado ao carregador; perfil de energia "balanced"; *governor* `powersave`; turbo ligado |
| Seleção de JDK | SDKMAN 5.23.0 (`sdk use` só no processo filho; Java padrão do sistema intacto) |
| Medidor | Java 17 (Maven), SHA-256 `415ddd80…26339995` |

O estado completo do sistema de cada sessão está em `dados/brutos/<sessão>/<sessão>-ambiente-inicial.json` e
`-ambiente-final.json`; o de cada processo, em `system-before.json` e `system-after.json`.

---

## 📏 Métricas

| Métrica | Unidade | Definição |
|---|---|---|
| Energia (E) | J | média das 3 iterações medidas do processo (energia do pacote em cada iteração) |
| Tempo (t) | s | média das 3 iterações medidas |
| Potência média (P) | W | soma das energias ÷ soma dos tempos das iterações medidas (P = E / t) |
| Coletas de lixo | número | pausas registradas no log de GC no processo inteiro |
| Pausas de GC | ms | soma das pausas no processo inteiro |
| Heap após coleta | MB | mediana da ocupação do heap depois de cada coleta |
| Sobrecarga do medidor | % | tempo médio das iterações medidas ÷ tempo da última preparação − 1 |

A potência ajuda a separar duas causas: uma configuração pode gastar menos energia porque termina antes (mesma
potência, menos tempo) ou porque exige menos do processador (menor potência em tempo parecido).

---

## 📊 Análise estatística, critérios e hipóteses

- **Medida de efeito:** razão das medianas entre configurações (por exemplo, D/C), com **IC 95% por bootstrap pareado
  por bloco** (10 000 reamostragens, código de sorteio 20261101). Uma razão abaixo de 1 indica valor menor na
  configuração do numerador.
- **Testes complementares** (em `razoes.csv`): Mann-Whitney U com correção de Holm e tamanho de efeito A12 de
  Vargha-Delaney.
- **Análise de sensibilidade (exploratória, fora do registro prévio):** Friedman, ANOVA em blocos sobre log,
  teste t pareado sobre log e Wilcoxon exato, com Holm.

**Critérios de avaliação do artefato (E1–E7):**

| Critério | Medida | Limite |
|---|---|---|
| E1 Repetibilidade | CV da energia por carga × configuração | ≤ 5% nas principais |
| E2 Reprodutibilidade entre sessões | maior ÷ menor mediana de energia entre sessões − 1 | ≤ 5% nas principais |
| E3 Sensibilidade | meia-largura do IC 95% da razão D/C da energia | ≤ 3 pontos percentuais |
| E4 Intrusão | sobrecarga do medidor (mediana) | ≤ 2% |
| E5 Rastreabilidade | processos com evidência completa | 100% |
| E6 Viabilidade | tempo de máquina por sessão e falhas | ≤ 1h30 por sessão; falhas ≤ 5% |
| E7 Comparação ingênua | medição sem preparação, sem núcleos fixos e sem sorteio | descritivo |

**Hipóteses (H1–H5):**

| Hipótese | Enunciado | Confirmada se | Refutada se |
|---|---|---|---|
| H1 | Energia menor em D do que em C | IC 95% de D/C da energia todo abaixo de 1 | todo acima de 1 |
| H2 | A mudança de energia D/C acompanha a de tempo (potência sem mudança relevante) | IC 95% de D/C da potência dentro de [0,98; 1,02] | IC não contém 1 |
| H3a | Menor ocupação do heap após coleta em D | IC 95% de D/C todo abaixo de 1 | – |
| H3b | Menos coletas ou menos tempo de pausa em D | IC 95% de ao menos uma razão todo abaixo de 1 | – |
| H4 | Maior redução de energia na carga com maior redução de heap | exploratória, descritiva | – |
| H5 | Em B/A e C/B a energia acompanha o tempo | IC 95% da potência dentro de [0,98; 1,02] | – |

**Termos dos vereditos:** **confirmada** (a regra de confirmação foi atendida), **refutada** (a regra de refutação
foi atendida), **inconclusiva** (nenhuma das duas regras foi atendida, quando a hipótese tem as duas) e **não
confirmada** (a regra de confirmação não foi atendida, quando a hipótese não tem regra de refutação). Explicação da
escolha dos termos: [`evidencias/base-oficial/NOTA_TERMOS_VEREDITOS.txt`](evidencias/base-oficial/NOTA_TERMOS_VEREDITOS.txt).

---

## 📈 Principais resultados

Resultados completos: [`resultados/oficial-20261101-termos/resumo.txt`](resultados/oficial-20261101-termos/resumo.txt).
Valores das cargas principais (razão das medianas e IC 95% pareado por bloco):

| Carga | Comparação | Energia | Tempo | Potência média |
|---|---|---|---|---|
| lusearch | B/A (17 → 21) | 0,9335 [0,9192; 0,9479] | 0,9468 [0,9405; 0,9519] | 0,9835 [0,9761; 0,9970] |
| lusearch | C/B (21 → 25) | 1,0202 [1,0104; 1,0271] | 1,0101 [1,0049; 1,0127] | 1,0152 [1,0070; 1,0161] |
| lusearch | D/C (compactos) | 0,9955 [0,9888; 1,0175] | 0,9962 [0,9926; 1,0059] | 0,9997 [0,9848; 1,0093] |
| pmd | B/A (17 → 21) | 0,9597 [0,9502; 0,9751] | 0,9486 [0,9423; 0,9503] | 1,0133 [1,0103; 1,0342] |
| pmd | C/B (21 → 25) | 0,9546 [0,9401; 0,9617] | 0,9352 [0,9332; 0,9391] | 1,0142 [1,0052; 1,0260] |
| pmd | D/C (compactos) | 1,0037 [0,9903; 1,0154] | 1,0048 [1,0028; 1,0085] | 1,0018 [0,9874; 1,0121] |

| Hipótese | lusearch | pmd |
|---|---|---|
| H1 energia menor em D | inconclusiva | inconclusiva |
| H2 potência D/C sem mudança | confirmada | confirmada |
| H3a heap menor em D | não confirmada | confirmada |
| H3b menos coletas/pausas em D | confirmada | confirmada |
| H5 B/A energia acompanha tempo | não confirmada | não confirmada |
| H5 C/B energia acompanha tempo | confirmada | não confirmada |

Critérios: E1, E3, E4 (mediana), E5 e E6 **atendidos**; **E2 não atendido** (maior diferença entre sessões de 6,1%,
limite de 5%, em lusearch-A, pmd-A, pmd-B e pmd-D); E7 pendente (sessão ingênua). As razões pareadas por bloco
ficaram estáveis entre as sessões, então as comparações devem ser feitas por razões dentro do bloco, e não por
energia absoluta entre dias diferentes. Todos os 180 processos são válidos.

---

## 📂 Estrutura do repositório

```text
├── README.md / README.en.md        # Esta documentação (português / inglês)
├── LICENSE                         # Licença MIT (código)
├── LICENCA-DADOS.txt               # Licença CC BY 4.0 (dados, resultados, evidências, configuração)
├── CITATION.cff                    # Dados de citação
├── Dockerfile / .dockerignore      # Imagem que refaz a análise
├── config/
│   ├── execucao.json               # Protocolo fixado da coleta (JDKs, cargas, iterações, heap, pausas, SHA-256)
│   ├── registro-previo.json        # Critérios E1–E7, hipóteses H1–H5 e regras de decisão (antes da coleta)
│   └── piloto-t12.json             # Configuração do piloto que definiu o protocolo
├── dados/
│   ├── brutos/<sessão>/            # 4 sessões oficiais; uma pasta por processo (ex.: b01-001-lusearch-A)
│   └── piloto/                     # Pilotos (fora da amostra oficial)
├── evidencias/
│   ├── manifestos/                 # SHA-256 de cada arquivo de cada sessão e dos pilotos
│   ├── conferencias/               # Conferência de cada sessão e da coleta completa
│   └── base-oficial/               # Como os resultados oficiais foram gerados, ocorrências e somas de verificação
├── resultados/
│   ├── oficial-20261101/           # Resultados oficiais (versão base-oficial-v1)
│   └── oficial-20261101-termos/    # Mesmos números com os termos atuais dos vereditos (USE ESTA)
├── analise/                        # Pacote Python pae-analise (consolidação, estatística, figuras, testes)
│   └── requisitos-travados.txt     # Versões exatas das bibliotecas
├── medidor-java/                   # Medidor de energia (callback da DaCapo, Maven, Java 17)
├── ferramentas/dacapo.json         # Endereço, versão e SHA-256 da DaCapo (a suíte não fica no repositório)
├── scripts/
│   ├── reproduzir_analise.sh       # Refaz a análise e compara com a oficial (um comando)
│   ├── conferir_dados.sh           # Confere os dados contra os manifestos
│   ├── comparar_resultados.py      # Compara duas pastas de resultados
│   ├── preparar_ambiente_coleta.sh # Prepara um Linux para repetir a coleta (JDKs, DaCapo, medidor)
│   ├── planejar_sessoes_oficiais.sh# Grava os 4 planos de sessão com os códigos de sorteio originais
│   ├── sessao.py                   # Planeja e executa uma sessão em blocos
│   ├── executar.py / executar.sh   # Prepara ou executa um processo JVM com todas as conferências
│   ├── selecionar-java.sh          # Seleção do JDK pelo SDKMAN (chamado por executar.py)
│   ├── manifesto.py                # Gera ou confere o manifesto SHA-256 de uma sessão
│   ├── conferir_sessao.py          # Confere a qualidade de uma sessão contra o protocolo
│   ├── conferir_coleta.py          # Confere várias sessões juntas (inclui E2)
│   └── tests/                      # Testes dos scripts de coleta
└── .github/workflows/analise.yml   # Conferência automática (estilo, tipos, testes, reprodução e Docker)
```

Dentro de cada pasta de processo (`dados/brutos/<sessão>/bNN-OOO-carga-config/`):

| Arquivo | Conteúdo |
|---|---|
| `resultado.json` | resultado verificado: energia e tempo de cada iteração medida, eventos, linha de base ociosa |
| `command.json` | comando exato da JVM |
| `java-preflight.json` | identidade efetiva da JVM (versão, fornecedor, `java.home`, G1, cabeçalhos compactos) |
| `sdkman.json` | JDK selecionado pelo SDKMAN |
| `artifacts.json` | SHA-256 do medidor e da DaCapo usados |
| `system-before.json` / `system-after.json` | estado do sistema (carregador, temperatura, memória, *swap*, perfil de energia) |
| `idle-baseline.json` | energia e potência ociosas antes do processo |
| `gc.log` | log de coleta de lixo |
| `medidor/` | leituras brutas do medidor |
| `stdout.log` / `stderr.log` | saídas da DaCapo |

---

## 🚀 Como reproduzir

Há dois níveis:

| Nível | O que faz | Onde roda | Tempo |
|---|---|---|---|
| **1. Refazer a análise** | confere os dados e recalcula todos os números a partir dos dados brutos do repositório | Windows, Linux ou macOS | ~5 min |
| **2. Repetir a coleta** | mede de novo em outra máquina e analisa os dados novos | Linux com Intel RAPL | ~4 h de máquina + preparação |

Todos os comandos rodam **na pasta raiz do projeto** (a pasta onde está este README), num terminal *bash*:
Linux ou macOS (Terminal) ou Windows com **Git Bash** (instalado junto com o [Git para Windows](https://git-scm.com/download/win)).
Comandos equivalentes para PowerShell estão indicados quando diferem.

---

### 🔁 Nível 1 – Refazer a análise (qualquer computador)

#### Pré-requisitos

| Programa | Versão | Como conferir | Onde obter |
|---|---|---|---|
| Git | qualquer recente | `git --version` | <https://git-scm.com/downloads> |
| Python | **3.10 ou mais novo** (oficial: 3.12 e 3.13) | `python --version` ou `python3 --version` | <https://www.python.org/downloads/> |
| Espaço em disco | ~300 MB | – | – |
| Internet | só para baixar o repositório e as bibliotecas | – | – |

No Windows, ao instalar o Python, marque **"Add python.exe to PATH"**.

#### Passo 1 – Baixar o repositório

```bash
git clone https://github.com/evertoncg10/java-energy-study.git
cd java-energy-study
```

Para usar exatamente a versão da análise publicada, troque para a marca correspondente (opcional):

```bash
git checkout analise-v1.1
```

#### Passo 2 – Conferir a integridade dos dados

```bash
bash scripts/conferir_dados.sh
```

Confere cada arquivo dos dados contra os manifestos SHA-256 gravados ao fim de cada sessão e refaz a conferência da
coleta. Resultado esperado: `CONFERE` em todas as linhas e, no fim,
`RESULTADO: todos os dados conferem com os manifestos.`

#### Passo 3 – Refazer a análise (opção A: um comando)

```bash
bash scripts/reproduzir_analise.sh
```

O script cria o ambiente virtual `analise/.venv` (só na primeira vez), instala as versões travadas das bibliotecas,
roda os testes automáticos, refaz a análise numa pasta nova `resultados/reproducao-AAAAMMDD-HHMMSS` e compara com os
resultados oficiais. Leva cerca de 1 minuto depois da instalação. Resultado esperado, no fim:

```text
idêntico: razoes.csv
idêntico: resumo.txt
...
Arquivos diferentes: 0
```

Para gerar também as figuras: `bash scripts/reproduzir_analise.sh --com-figuras`.

#### Passo 3 – Refazer a análise (opção B: comando por comando)

1. Criar o ambiente virtual (só na primeira vez):

   ```bash
   python -m venv analise/.venv        # se "python" não existir, use python3
   ```

2. Ativar o ambiente virtual (em todo terminal novo):

   | Sistema / terminal | Comando |
   |---|---|
   | Windows – Git Bash | `source analise/.venv/Scripts/activate` |
   | Windows – PowerShell | `analise\.venv\Scripts\Activate.ps1` |
   | Windows – Prompt de Comando (CMD) | `analise\.venv\Scripts\activate.bat` |
   | Linux ou macOS | `source analise/.venv/bin/activate` |

   Com o ambiente ativo, o terminal mostra `(.venv)` no começo da linha.
   No Windows, rode também `export PYTHONUTF8=1` (Git Bash) ou `$env:PYTHONUTF8=1` (PowerShell), para os acentos
   saírem certos.

3. Instalar as versões travadas e rodar os testes:

   ```bash
   cd analise
   python -m pip install -r requisitos-travados.txt -e ".[dev,figuras]"
   python -m pytest
   cd ..
   ```

   Resultado esperado: `41 passed`.

4. Refazer a análise completa (com figuras):

   ```bash
   pae-analise analisar --saida resultados/reproducao
   ```

   A pasta de saída precisa ser nova; para rodar de novo, use outro nome (por exemplo `resultados/reproducao2`).
   Opções: `--sem-figuras` (não gera figuras), `--reamostragens N` (padrão 10000) e `--semente N`
   (código de sorteio do bootstrap, padrão 20261101). Só os padrões reproduzem os números oficiais.

5. Comparar com os resultados oficiais:

   ```bash
   python scripts/comparar_resultados.py resultados/oficial-20261101-termos resultados/reproducao --ignorar-figuras
   ```

   Resultado esperado: `Arquivos diferentes: 0`. O `metadados.json` sempre muda (data, sistema e commit); nele o
   script confere só o campo `input_sha256`, que identifica os dados de entrada. As figuras ficam de fora com
   `--ignorar-figuras` porque só saem idênticas byte a byte no mesmo sistema operacional; os números (CSV, JSON e
   texto) saem idênticos em Windows, Linux e macOS.

6. Só a base consolidada (uma linha por processo), se quiser trabalhar os dados em outra ferramenta:

   ```bash
   pae-analise consolidar --saida resultados/base
   ```

#### Opção C: Docker

Com o [Docker](https://docs.docker.com/get-docker/) instalado, sem precisar de Python:

```bash
docker build -t pae-jvm-analise .
docker run --rm pae-jvm-analise
```

O contêiner refaz a análise e mostra a comparação com os resultados oficiais (esperado: `Arquivos diferentes: 0`).
Para gravar a análise completa, com figuras, em `resultados/reproducao-docker` do seu computador:

```bash
docker run --rm -v "$(pwd)/resultados:/saida" pae-jvm-analise pae-analise analisar --saida /saida/reproducao-docker
```

No PowerShell, troque `$(pwd)` por `${PWD}`.

#### Arquivos gerados pela análise

| Arquivo | Conteúdo |
|---|---|
| `resumo.txt` | resumo legível: critérios, razões, hipóteses, decomposição e sensibilidade |
| `base-oficial.csv` / `.json` | base consolidada: uma linha por processo oficial, ligada ao arquivo de origem |
| `base-pilotos.csv` | base dos pilotos (separada) |
| `descritiva.csv` | n, mediana, média, CV, mínimo e máximo por carga × configuração × métrica |
| `razoes.csv` | razões B/A, C/B e D/C com IC 95%, Mann-Whitney, Holm e A12 |
| `criterios.json` | cálculo e veredito de E1 a E6 |
| `hipoteses.csv` / `h4.json` | vereditos de H1 a H5 |
| `decomposicao.csv` | decomposição exploratória log E = log P + log t |
| `sensibilidade-*.csv` | análise de sensibilidade exploratória |
| `metadados.json` | data, sistema, versões, commit e SHA-256 dos dados de entrada |
| `figuras/` | energia, razões, sessões, decomposição, memória e fluxo do protocolo (PNG e PDF) |

#### Conferência automática

A cada alteração no repositório, o GitHub Actions ([`.github/workflows/analise.yml`](.github/workflows/analise.yml))
instala as versões travadas, roda estilo (ruff), tipos (mypy) e testes (pytest), refaz a análise e compara com os
resultados oficiais, e também constrói e roda a imagem Docker.

---

### 🔬 Nível 2 – Repetir a coleta (Linux com Intel RAPL)

Repetir a coleta mede a energia de novo, em outra máquina. Os valores absolutos dependem do equipamento; o que se
espera reproduzir é a **direção e o tamanho das razões** entre configurações, com o mesmo protocolo.

#### Pré-requisitos

| Item | Exigência | Como conferir |
|---|---|---|
| Sistema | Linux instalado direto na máquina (sem máquina virtual, WSL ou contêiner) | `uname -s` → `Linux` |
| Processador | Intel com RAPL de pacote exposto pelo kernel | `cat /sys/class/powercap/intel-rapl:0/name` → `package-0` |
| Núcleos | Intel híbrido (12ª geração ou mais nova) para a afinidade original | `cat /sys/devices/cpu_core/cpus` |
| Sensor térmico | zona `x86_pkg_temp` (usada nas pausas) | `grep -l x86_pkg_temp /sys/class/thermal/thermal_zone*/type` |
| Alimentação | notebook no carregador durante toda a sessão | `cat /sys/class/power_supply/*/online` |
| Permissão | usuário com `sudo` (só para liberar a leitura do contador RAPL) | `sudo -v` |
| Disco livre | ~25 GB (DaCapo: 6,3 GB compactada, 15,9 GB extraída) | `df -h .` |
| Programas | `git`, `python3` (3.10+), `curl`, `unzip`, `sha256sum`, Maven 3.9+ | `mvn -version` |
| SDKMAN | com um Java padrão instalado | `sdk version` |

Em Ubuntu, Debian, Zorin OS ou Mint, os programas se instalam com:

```bash
sudo apt update
sudo apt install git python3 python3-venv curl unzip zip coreutils maven
```

O SDKMAN se instala com (depois, abra um terminal novo):

```bash
curl -s "https://get.sdkman.io" | bash
source "$HOME/.sdkman/bin/sdkman-init.sh"
sdk install java 21.0.11-tem      # serve como Java padrão; não interfere na coleta
```

Sem processador Intel híbrido, a coleta ainda roda, mas a afinidade precisa ser desligada
(veja [Adaptar a outro equipamento](#adaptar-a-outro-equipamento)).

#### Passo 1 – Baixar o repositório

```bash
git clone https://github.com/evertoncg10/java-energy-study.git
cd java-energy-study
```

#### Passo 2 – Preparar o ambiente

```bash
bash scripts/preparar_ambiente_coleta.sh
```

O script confere o sistema, instala pelo SDKMAN os JDKs `17.0.19-tem`, `21.0.11-tem` e `25.0.3-tem` (sem mudar o Java
padrão), baixa a DaCapo do endereço oficial registrado em [`ferramentas/dacapo.json`](ferramentas/dacapo.json),
confere o SHA-256 oficial, extrai em `ferramentas/dacapo/`, instala o JAR da DaCapo no repositório local do Maven,
compila e testa o medidor e compara os SHA-256 com [`config/execucao.json`](config/execucao.json). Pode ser executado
de novo: o que já está pronto é só conferido. O download leva de minutos a horas, conforme a internet.

<details>
<summary>O mesmo passo, comando por comando</summary>

```bash
# JDKs (responda "n" quando perguntar se quer tornar padrão)
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

# Medidor
mvn install:install-file -Dfile=ferramentas/dacapo/dacapo-23.11-MR2-chopin.jar \
  -DgroupId=org.dacapo -DartifactId=dacapo -Dversion=23.11-MR2-chopin -Dpackaging=jar
JAVA_HOME="$HOME/.sdkman/candidates/java/17.0.19-tem" mvn -f medidor-java/pom.xml clean package
sha256sum medidor-java/target/java-energy-meter-0.1.0.jar   # original: 415ddd802fbcde66e77e2f7c1262e79680d92b8fef7a49468a1559ff26339995

# Testes dos scripts de coleta
python3 -m unittest discover -s scripts/tests
```

</details>

Se o SHA-256 do medidor sair diferente do original (outro compilador ou outra versão do Maven), o código é o mesmo,
mas o programa recusa o JAR. Nesse caso, copie a configuração e registre o novo valor, e relate isso como desvio:

```bash
cp config/execucao.json config/replicacao.json
sha256sum medidor-java/target/java-energy-meter-0.1.0.jar
# edite config/replicacao.json: troque "meter" → "sha256" pelo valor mostrado acima
```

Daí em diante, use `--config config/replicacao.json` nos comandos dos passos 4 e 6.

#### Passo 3 – Liberar a leitura do contador RAPL

Por segurança, o Linux só deixa o administrador ler o contador de energia. O comando abaixo libera a leitura só
desse contador para o seu usuário (pede a sua senha do `sudo` no próprio terminal; o programa não guarda senha):

```bash
bash scripts/executar.sh preparar --configuracao A --liberar-leitura
```

A liberação vale até o computador reiniciar; depois de reiniciar, rode de novo. Equivale a
`sudo chown $(id -u) /sys/devices/virtual/powercap/intel-rapl/intel-rapl:0/energy_uj`.

#### Passo 4 – Execução de verificação

Um processo de teste, fora da amostra (grava em `dados/verificacao/`, que não vai para o Git):

```bash
bash scripts/executar.sh executar --configuracao D --aplicacao pmd
```

Resultado esperado: uma linha JSON terminando com `"status": "success"`. Isso confirma SDKMAN, JDK, cabeçalhos
compactos, RAPL, afinidade, DaCapo e medidor.

#### Passo 5 – Preparar a máquina antes de cada sessão

Cada sessão leva cerca de 1 hora (a 4ª, cerca de 47 min). Antes de começar:

1. Ligar o carregador e mantê-lo ligado até o fim.
2. Fechar todos os outros programas (navegador, editores, sincronização de nuvem, antivírus em varredura).
3. Desligar a suspensão automática e o descanso de tela durante a sessão.
4. Não usar o computador durante a sessão.
5. Esperar alguns minutos com a máquina ociosa (a temperatura ociosa medida no início define as pausas).
6. Conferir que o contador RAPL está liberado (passo 3).

#### Passo 6 – Planejar as sessões

Grava os 4 planos com o mesmo desenho da coleta original (15 blocos em 4 + 4 + 4 + 3; códigos de sorteio 20261101 a
20261104), numa pasta fora do repositório:

```bash
bash scripts/planejar_sessoes_oficiais.sh ../planos-pae-jvm
# com configuração de replicação:
# bash scripts/planejar_sessoes_oficiais.sh ../planos-pae-jvm config/replicacao.json
```

Com os mesmos códigos de sorteio, a ordem dos processos sai **idêntica** à da coleta original (conferido contra os
`plano-antes-execucao.json` das 4 sessões). Para um plano isolado:

```bash
python3 scripts/sessao.py planejar --config config/execucao.json --categoria oficial \
  --blocos 4 --primeiro-bloco 1 --semente 20261101 --plano ../planos-pae-jvm/plano-sessao1.json
```

#### Passo 7 – Executar as sessões

Uma sessão por vez, de preferência em dias diferentes, repetindo o passo 5 antes de cada uma:

```bash
python3 scripts/sessao.py executar --plano ../planos-pae-jvm/plano-sessao1.json
```

O terminal mostra `ok` ou `FALHA` a cada processo e, no fim, `SESSAO=dados/brutos/<pasta da sessão>`. Se a sessão
for interrompida (queda de energia, por exemplo), continue sem repetir o que já passou:

```bash
python3 scripts/sessao.py executar --plano ../planos-pae-jvm/plano-sessao1.json --retomar
```

Repita para `plano-sessao2.json`, `plano-sessao3.json` e `plano-sessao4.json`.

#### Passo 8 – Congelar e conferir cada sessão

Logo depois de cada sessão (troque `PASTA` pela pasta mostrada em `SESSAO=`):

```bash
python3 scripts/manifesto.py gerar --sessao dados/brutos/PASTA \
  --saida ../manifestos-pae-jvm/sessao1.json --plano ../planos-pae-jvm/plano-sessao1.json
python3 scripts/conferir_sessao.py --sessao dados/brutos/PASTA
```

O manifesto grava o SHA-256 de todos os arquivos (o programa nunca sobrescreve um manifesto). A conferência mostra
duração, falhas, temperaturas, cobertura das leituras e CV por combinação, e termina com `CONFERE` ou
`NAO_CONFERE`. Depois das 4 sessões, confira a coleta inteira (inclui o critério E2):

```bash
python3 scripts/conferir_coleta.py \
  --sessao dados/brutos/PASTA1 --manifesto ../manifestos-pae-jvm/sessao1.json \
  --sessao dados/brutos/PASTA2 --manifesto ../manifestos-pae-jvm/sessao2.json \
  --sessao dados/brutos/PASTA3 --manifesto ../manifestos-pae-jvm/sessao3.json \
  --sessao dados/brutos/PASTA4 --manifesto ../manifestos-pae-jvm/sessao4.json
```

#### Passo 9 – Analisar os dados novos

A análise lê **todas** as sessões de `dados/brutos/` e os manifestos `evidencias/manifestos/sessao*.json`. Para
analisar só os seus dados, tire as 4 sessões originais e os manifestos originais dessas pastas (o Git guarda as
versões originais) e coloque os seus manifestos no lugar:

```bash
mkdir -p ../originais-pae-jvm
mv dados/brutos/20261022T2152* ../originais-pae-jvm/
mv evidencias/manifestos/sessao*.json ../originais-pae-jvm/
cp ../manifestos-pae-jvm/sessao*.json evidencias/manifestos/
```

O Git vai mostrar esses arquivos como removidos; é esperado. Para voltar ao estado original depois:
`git checkout -- dados/brutos evidencias/manifestos`.

Depois, ative o ambiente da análise (Nível 1, passo 3, itens 1 a 3) e rode:

```bash
pae-analise analisar --saida resultados/replicacao
```

Compare o seu `resultados/replicacao/resumo.txt` com o oficial, principalmente as razões D/C, C/B e B/A.

#### Adaptar a outro equipamento

Qualquer mudança no protocolo deve ser feita numa **cópia** da configuração (por exemplo `config/replicacao.json`)
e relatada como desvio:

| Situação | O que mudar na cópia |
|---|---|
| Processador sem núcleos híbridos (sem `/sys/devices/cpu_core`) | `"cpu_affinity": null` |
| Contador RAPL em outro caminho | `"rapl_directory"` com o caminho do domínio `package-0` |
| SHA-256 do medidor diferente | `"meter"` → `"sha256"` com o valor novo |

Os JDKs, a DaCapo, as cargas, as iterações, o heap e as pausas não devem mudar; se mudarem, o resultado deixa de ser
uma repetição deste protocolo.

---

## 🛠️ Solução de problemas

| Mensagem ou situação | Causa e solução |
|---|---|
| `python: command not found` | use `python3`; no Windows, reinstale o Python marcando "Add python.exe to PATH" |
| Acentos errados ou `UnicodeEncodeError` no Windows | `export PYTHONUTF8=1` (Git Bash) ou `$env:PYTHONUTF8=1` (PowerShell) |
| PowerShell recusa `Activate.ps1` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` ou use o Git Bash |
| `pae-analise: command not found` | o ambiente virtual não está ativo; ative (Nível 1, passo 3, item 2) |
| `A pasta de saída já existe e não será sobrescrita` | use outro nome em `--saida` |
| Instalação ou análise muito lenta no Windows | o antivírus pode estar varrendo `analise/.venv`; adicione a pasta do projeto às exceções |
| Figuras diferentes das oficiais | normal entre sistemas operacionais diferentes; compare com `--ignorar-figuras` |
| `metadados.json` diferente | normal (data, sistema e commit); o que importa é `mesmos dados de entrada: sim` |
| `Contador sem leitura. Execute preparar --liberar-leitura…` | rode o passo 3 do Nível 2 (a liberação some ao reiniciar) |
| `Notebook sem alimentação externa confirmada.` | ligue o carregador |
| `Remova opções Java herdadas antes de executar: …` | `unset JAVA_TOOL_OPTIONS JDK_JAVA_OPTIONS _JAVA_OPTIONS CLASSPATH` |
| `SDKMAN precisa ter um Java padrão instalado` | `sdk install java 21.0.11-tem` |
| `SDKMAN não selecionou o JDK` / versão não encontrada | o JDK não está instalado; se saiu da lista do SDKMAN, baixe o mesmo build em <https://adoptium.net/temurin/archive/> e use `sdk install java 17.0.19-tem <pasta do JDK extraído>` |
| `SHA-256 divergente para meter` | veja o passo 2 do Nível 2 (cópia da configuração com o novo SHA-256) |
| `SHA-256 divergente para dacapo` | o arquivo da DaCapo está corrompido ou é outra versão; baixe e confira de novo |
| `Nenhum núcleo de desempenho encontrado para a afinidade.` | processador sem núcleos híbridos; veja [Adaptar a outro equipamento](#adaptar-a-outro-equipamento) |
| `Execute como pesquisador, sem sudo no script inteiro.` | rode os scripts sem `sudo` |
| `Três falhas seguidas; interromper e investigar.` | veja `stderr.log` e `resultado.json` do processo que falhou; corrija e use `--retomar` |

---

## 🏷️ Versões marcadas

| Marca | Conteúdo |
|---|---|
| `base-oficial-v1` | base oficial fechada depois da coleta, resultados em `resultados/oficial-20261101` |
| `analise-v1.1` | mesmos números, com os vereditos nos termos confirmada, não confirmada, refutada e inconclusiva (`resultados/oficial-20261101-termos`) |

Como os resultados oficiais foram gerados, ocorrências e somas de verificação: [`evidencias/base-oficial/`](evidencias/base-oficial/).

---

## 🌍 Ciência aberta

Em linha com as práticas de **Ciência Aberta**, estão públicos e reprodutíveis:

- o protocolo fixado e o registro prévio de critérios, hipóteses e regras de decisão, gravados antes da coleta;
- os dados brutos de todos os 180 processos oficiais e dos pilotos, sem exclusões, com os manifestos SHA-256;
- o código do medidor, dos scripts de coleta e da análise, com testes automáticos;
- as versões exatas das bibliotecas, a imagem Docker e a conferência automática da reprodução;
- os resultados oficiais e o registro de ocorrências e desvios.

**Fora do repositório:** o arquivo da DaCapo (baixado do site oficial e conferido pelo SHA-256) e as pastas de
trabalho `scratch` da DaCapo de cada processo, que constam dos manifestos e dos pacotes completos das sessões. Os
pacotes completos serão publicados no Zenodo, com DOI, que será indicado aqui.

---

## ⚠️ Limitações

- A energia é a do **pacote do processador** (RAPL), não a da tomada nem só a da JVM; RAPL é uma estimativa do
  próprio processador, sem calibração externa.
- Uma única máquina (notebook) e um único sistema; os valores absolutos não se generalizam para outros equipamentos.
- O critério E2 não foi atendido (6,1% entre sessões, limite 5%): compare razões dentro do bloco, não energia
  absoluta entre dias.
- Três cargas da DaCapo, uma thread e heap fixo de 1 GB; outras cargas e configurações podem se comportar diferente.

---

## 📜 Licenças

- **Código** (`analise/`, `medidor-java/`, `scripts/`): licença MIT, em [`LICENSE`](LICENSE).
- **Dados, resultados, evidências e configuração** (`dados/`, `resultados/`, `evidencias/`, `config/`): Creative
  Commons Atribuição 4.0 Internacional (CC BY 4.0), em [`LICENCA-DADOS.txt`](LICENCA-DADOS.txt).
- A DaCapo (Apache-2.0, com as licenças próprias das aplicações) e os JDKs Eclipse Temurin mantêm as licenças próprias
  e não fazem parte deste repositório.

---

## 📝 Como citar

Os dados de citação estão em [`CITATION.cff`](CITATION.cff); o GitHub mostra a referência pronta no botão
**"Cite this repository"**. Em BibTeX:

```bibtex
@software{goncalves_pae_jvm_2026,
  author  = {Gonçalves, Everton Cezar},
  title   = {{PAE-JVM – Protocolo de Avaliação Energética de configurações da JVM: dados, análise e código}},
  year    = {2026},
  version = {1.1},
  url     = {https://github.com/evertoncg10/java-energy-study}
}
```

**Autor:** Everton Cezar Gonçalves – Universidade Tecnológica Federal do Paraná (UTFPR) –
ORCID [0009-0003-7548-2501](https://orcid.org/0009-0003-7548-2501).
