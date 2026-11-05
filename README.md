# PAE-JVM: Eficiência Energética de JVMs – Temurin 17 vs 21 vs 25 e cabeçalhos compactos

[![Java Support](https://img.shields.io/badge/Java-17%20%7C%2021%20%7C%2025-orange?logo=openjdk)](#-configurações-comparadas)
[![Python Analysis](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](#-nível-1--refazer-a-análise-qualquer-computador)
[![Open Science](https://img.shields.io/badge/Open%20Science-Compliant-success)](#-ciência-aberta)
[![DaCapo](https://img.shields.io/badge/DaCapo-23.11--MR2--chopin-informational)](#-cargas-de-trabalho-dacapo)
[![Energia](https://img.shields.io/badge/Energia-Intel%20RAPL-lightgrey)](#-como-a-energia-é-medida)
[![Docker](https://img.shields.io/badge/Docker-an%C3%A1lise-2496ED?logo=docker&logoColor=white)](#opção-c-docker)
[![Código: MIT](https://img.shields.io/badge/C%C3%B3digo-MIT-yellow)](LICENSE)
[![Dados: CC BY 4.0](https://img.shields.io/badge/Dados-CC%20BY%204.0-lightgrey)](LICENCA-DADOS.txt)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23982640.svg)](https://doi.org/10.5281/zenodo.23982640)

🇧🇷 Português | 🇺🇸 [English](README.en.md)

Este repositório armazena tudo o que foi usado em uma pesquisa de mestrado sobre **Software Verde**, na área de
Engenharia de Software, incluindo o protocolo de medição, o código, os dados brutos, as evidências e a análise
estatística.

A motivação inicial é uma dúvida prática e simples de declarar. Quando trocamos a versão do Java, o programa passa a
gastar mais ou menos energia? Para responder a essa dúvida com segurança, porém, é preciso antes saber medir bem, e é
nisso que a pesquisa se concentra.

O foco, portanto, é **como medir**, de forma confiável e reprodutível, o efeito de versões e opções da máquina virtual
Java (**JVM**) sobre a energia e o tempo de execução, usando apenas um computador pessoal. Para avaliar o protocolo
criado com esse fim, ele foi aplicado a um caso real, no qual comparamos o consumo de energia do processador e o tempo de
execução de três versões da distribuição **Eclipse Temurin**, os **JDKs 17, 21 e 25**, e também o JDK 25 **com e sem os
cabeçalhos compactos de objeto** (*Compact Object Headers*, JEP 519), uma novidade que promete reduzir o uso de
memória. As perguntas formais da pesquisa estão na seção [Perguntas da pesquisa](#-perguntas-da-pesquisa).

A pesquisa segue o método **Design Science Research (DSR)**. Isso quer dizer que, além de medir, construímos e
avaliamos um artefato, o **PAE-JVM – Protocolo de Avaliação Energética de configurações da JVM**. Ele junta um medidor
de energia integrado à suíte de testes DaCapo, a seleção conferida do JDK em cada execução, um orquestrador que
organiza as sessões de medição e um conjunto de regras para lidar com ruído, falhas e análise. A coleta de dados
serviu justamente para avaliar esse protocolo. Os critérios de avaliação (E1 a E7) e as hipóteses (H1 a H5) foram
registrados **antes** da coleta, no arquivo [`config/registro-previo.json`](config/registro-previo.json), para que os
resultados não pudessem influenciar as regras.

Quem quiser conferir os dados, refazer a análise ou até repetir a medição em outro computador encontra aqui o
caminho completo, explicado passo a passo na seção [Como reproduzir](#-como-reproduzir).

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
- [Uso de inteligência artificial](#-uso-de-inteligência-artificial)
- [Licenças](#-licenças)
- [Como citar](#-como-citar)

---

## ❓ Perguntas da pesquisa

A pergunta principal, do ponto de vista do DSR, é sobre o método, ou seja, **como avaliar, de forma confiável e reprodutível,
o efeito de versões e opções da JVM sobre a energia e o tempo de execução em um computador pessoal, sem um medidor
externo de energia?** Muitos desenvolvedores e pesquisadores só têm o próprio notebook à disposição, e o PAE-JVM foi
pensado para esse cenário.

Para testar o protocolo na prática, ele foi aplicado a duas perguntas concretas:

- **QC1.** Ao ligar os cabeçalhos compactos no Eclipse Temurin 25, o que muda na energia do processador e no tempo de
  execução da mesma tarefa? E essa mudança acontece pelo motivo esperado, ou seja, menos memória ocupada e menos
  trabalho do coletor de lixo?
- **QC2.** Quando passamos do Temurin 17 para o 21, e do 21 para o 25, a energia muda na mesma proporção que o tempo?

---

## ☕ Configurações comparadas

Comparamos quatro configurações, sempre com a distribuição Eclipse Temurin instalada pelo SDKMAN:

| Configuração | JDK (Eclipse Temurin) | Identificador no SDKMAN | Opção específica |
|---|---|---|---|
| **A** | 17.0.19+10 | `17.0.19-tem` | – |
| **B** | 21.0.11+10-LTS | `21.0.11-tem` | – |
| **C** | 25.0.3+9-LTS | `25.0.3-tem` | `-XX:-UseCompactObjectHeaders` (desligado) |
| **D** | 25.0.3+9-LTS | `25.0.3-tem` | `-XX:+UseCompactObjectHeaders` (ligado) |

Para que a comparação fosse justa, tudo o mais ficou igual nas quatro configurações, com o coletor de lixo **G1** (`-XX:+UseG1GC`), o
heap fixo de **1 GB** (`-Xms1g -Xmx1g`), o log de coleta de lixo ligado (`-Xlog:gc`), a carga rodando com **1 thread**
e o processo preso aos núcleos de desempenho do processador (um processador lógico por núcleo físico).

Um cuidado importante é que, antes de cada execução, o programa pergunta à própria JVM qual versão, fornecedor e pasta de
instalação ela está usando, se o G1 está ativo e se os cabeçalhos compactos estão ligados ou desligados. Se qualquer
resposta for diferente do esperado, a execução nem começa. Assim temos certeza de que cada medida corresponde à
configuração certa.

Fizemos três comparações, **B/A** (do 17 para o 21), **C/B** (do 21 para o 25) e **D/C** (cabeçalhos compactos
ligados contra desligados, no mesmo JDK 25).

---

## 📦 Cargas de trabalho (DaCapo)

Como carga de trabalho, usamos a suíte **DaCapo 23.11-MR2-chopin** ([site oficial](https://www.dacapobench.org/)),
um conjunto de aplicações Java reais muito usado em pesquisas sobre a JVM. Escolhemos três aplicações, todas com a
entrada `default` e 1 thread:

| Carga | Papel | O que faz | Iterações de preparação | Iterações medidas |
|---|---|---|---|---|
| **lusearch** | principal | busca de texto com Apache Lucene | 1 | 3 |
| **pmd** | principal | análise estática de código Java | 7 | 3 |
| **avrora** | exploratória | simulação de microcontroladores AVR | 12 | 3 |

A JVM precisa de algumas rodadas até "aquecer", isto é, até o compilador JIT otimizar o código e o tempo de cada
rodada se estabilizar. Por isso cada aplicação roda primeiro algumas iterações de preparação (*warm-up*), que não
entram na medida, e só depois as 3 iterações medidas. O número de preparações de cada aplicação foi definido nos
pilotos, cujos dados estão em `dados/piloto/`.

As duas cargas principais, lusearch e pmd, são as que respondem às hipóteses. A avrora roda nos mesmos blocos, mas
ficou fora das conclusões porque variou muito nos pilotos. Ela usa pouco o processador e fica mais sensível ao que
acontece em segundo plano.

---

## ⚡ Como a energia é medida

Os processadores Intel trazem um contador interno de energia chamado **RAPL** (*Running Average Power Limit*), que o
Linux disponibiliza no arquivo `/sys/class/powercap/intel-rapl:0/energy_uj`. Usamos o contador do **pacote do
processador**, que cobre o processador inteiro, com todos os núcleos, a memória cache e o controlador de memória
integrado. É importante ter isso em mente ao ler os resultados, porque o valor não é a energia só da JVM, nem a
energia medida na tomada.

Quem lê esse contador é um pequeno medidor escrito em Java, na pasta [`medidor-java/`](medidor-java/). Ele roda como
*callback* da própria DaCapo, dentro da JVM que está sendo medida, e por isso sabe exatamente quando cada iteração
começa e termina. Durante a execução, o medidor consulta o contador a cada **100 ms** e trata o momento em que o
contador "dá a volta" e recomeça do zero.

Antes de cada processo, o programa também mede a energia com a máquina parada durante 10 segundos, o que registra a
potência ociosa daquele momento. E, para saber se o próprio medidor atrapalha a medição, comparamos o tempo das
iterações medidas com o da última iteração de preparação (é o critério E4).

---

## 🧪 Desenho da coleta

A medição de energia é sensível a muita coisa, como a temperatura, as tarefas do sistema e até a ordem em que as execuções
acontecem. O desenho da coleta foi pensado para controlar esses efeitos.

As execuções foram organizadas em **blocos completos**. Cada bloco contém as 12 combinações possíveis (3 cargas × 4
configurações), em uma ordem sorteada. Foram **15 blocos, totalizando 180 processos**, ou seja, 15 medidas para cada
combinação. Cada processo é uma **JVM nova**, iniciada do zero, para que uma execução não herde o estado da anterior.

Os 15 blocos foram divididos em **4 sessões**, feitas em dias diferentes, com 4, 4, 4 e 3 blocos. Cada sessão usou um
código de sorteio próprio, de **20261101 a 20261104**, e o plano de cada sessão, com a ordem exata dos processos, foi
gravado **antes** de a sessão começar. Toda sessão começa com uma execução de aquecimento da máquina (`pmd` na
configuração B), que não entra na análise.

Entre um processo e outro, o programa espera pelo menos 10 segundos e, depois, aguarda o processador esfriar até no
máximo 8 °C acima da temperatura medida com a máquina parada no início da sessão, com uma espera máxima de 120
segundos. Se um processo falha, ele é repetido uma vez no fim do mesmo bloco, e a falha continua registrada. Se
houver três falhas seguidas, a sessão para, para que o problema seja investigado. Na coleta oficial não houve nenhuma
falha.

Antes de cada processo, o programa ainda confere se o carregador está ligado, se não há opções Java "escondidas" em
variáveis de ambiente (como `JAVA_TOOL_OPTIONS`), se o medidor e a DaCapo são exatamente os mesmos arquivos registrados
(pelo SHA-256) e se o contador RAPL está avançando.

Por fim, tudo fica guardado. Cada processo deixa registrados o comando usado, a identidade da JVM, o estado do sistema
antes e depois, o log de coleta de lixo, as leituras do medidor e o resultado. Ao fim de cada sessão, um manifesto
grava o SHA-256 de todos os arquivos, o que permite provar mais tarde que nada foi alterado.

Todos esses parâmetros estão fixados no arquivo [`config/execucao.json`](config/execucao.json).

---

## 💻 Ambiente da coleta original

As medições foram feitas em um notebook pessoal, com a seguinte configuração:

| Item | Valor |
|---|---|
| Processador | Intel Core i7-13650HX (6 núcleos de desempenho + 8 de eficiência, 20 processadores lógicos) |
| Afinidade usada | processadores lógicos 0, 2, 4, 6, 8, 10 (um por núcleo de desempenho) |
| Memória | 16 GB |
| Sistema | Zorin OS (base Ubuntu), kernel Linux 7.0.0-38-generic, instalado direto na máquina |
| Energia | notebook ligado ao carregador; perfil de energia "balanced"; *governor* `powersave`; turbo ligado |
| Seleção de JDK | SDKMAN 5.23.0 (`sdk use` só no processo filho; Java padrão do sistema intacto) |
| Medidor | Java 17 (Maven, compilado com o Temurin 25.0.3), SHA-256 `415ddd80…26339995` |

Se precisar de mais detalhes, o estado completo do sistema no início e no fim de cada sessão está em
`dados/brutos/<sessão>/<sessão>-ambiente-inicial.json` e `-ambiente-final.json`. Para cada processo, os arquivos
`system-before.json` e `system-after.json` mostram o estado da máquina antes e depois da execução.

---

## 📏 Métricas

Para cada processo, calculamos as seguintes medidas:

| Métrica | Unidade | Definição |
|---|---|---|
| Energia (E) | J | média das 3 iterações medidas do processo (energia do pacote em cada iteração) |
| Tempo (t) | s | média das 3 iterações medidas |
| Potência média (P) | W | soma das energias ÷ soma dos tempos das iterações medidas (P = E / t) |
| Coletas de lixo | número | pausas registradas no log de GC no processo inteiro |
| Pausas de GC | ms | soma das pausas no processo inteiro |
| Heap após coleta | MB | mediana da ocupação do heap depois de cada coleta |
| Sobrecarga do medidor | % | tempo médio das iterações medidas ÷ tempo da última preparação − 1 |

A potência média ajuda a entender o porquê de uma diferença de energia. Uma configuração pode gastar menos energia
porque termina mais rápido, com a mesma potência, ou porque exige menos do processador, com menor potência em um
tempo parecido. São explicações diferentes, e a potência separa uma da outra.

---

## 📊 Análise estatística, critérios e hipóteses

Para comparar duas configurações, usamos a **razão entre as medianas**. Por exemplo, uma razão D/C de 0,98 na energia
significa que a configuração D gastou 2% menos energia que a C. A incerteza dessa razão é dada por um **intervalo de
confiança de 95%** calculado por *bootstrap* pareado por bloco, com 10 000 reamostragens e código de sorteio
20261101. "Pareado por bloco" quer dizer que cada comparação é feita entre execuções do mesmo bloco, que rodaram
próximas no tempo e nas mesmas condições da máquina.

O arquivo `razoes.csv` traz também testes complementares, como o Mann-Whitney U com correção de Holm e o tamanho de efeito
A12 de Vargha-Delaney. Além disso, fizemos uma análise de sensibilidade exploratória, que não estava no registro
prévio, com os testes de Friedman, ANOVA em blocos sobre o logaritmo, teste t pareado sobre o logaritmo e Wilcoxon
exato, todos com correção de Holm. Ela serve para verificar se as conclusões mudariam com outros métodos.

O protocolo foi avaliado por sete critérios, definidos antes da coleta:

| Critério | Medida | Limite |
|---|---|---|
| E1 Repetibilidade | CV da energia por carga × configuração | ≤ 5% nas principais |
| E2 Reprodutibilidade entre sessões | maior ÷ menor mediana de energia entre sessões − 1 | ≤ 5% nas principais |
| E3 Sensibilidade | meia-largura do IC 95% da razão D/C da energia | ≤ 3 pontos percentuais |
| E4 Intrusão | sobrecarga do medidor (mediana) | ≤ 2% |
| E5 Rastreabilidade | processos com evidência completa | 100% |
| E6 Viabilidade | tempo de máquina por sessão e falhas | ≤ 1h30 por sessão; falhas ≤ 5% |
| E7 Comparação ingênua | medição sem preparação, sem núcleos fixos e sem sorteio | descritivo |

E as hipóteses, também registradas antes, com a regra que decide cada uma:

| Hipótese | Enunciado | Confirmada se | Refutada se |
|---|---|---|---|
| H1 | Energia menor em D do que em C | IC 95% de D/C da energia todo abaixo de 1 | todo acima de 1 |
| H2 | A mudança de energia D/C acompanha a de tempo (potência sem mudança relevante) | IC 95% de D/C da potência dentro de [0,98; 1,02] | IC não contém 1 |
| H3a | Menor ocupação do heap após coleta em D | IC 95% de D/C todo abaixo de 1 | – |
| H3b | Menos coletas ou menos tempo de pausa em D | IC 95% de ao menos uma razão todo abaixo de 1 | – |
| H4 | Maior redução de energia na carga com maior redução de heap | exploratória, descritiva | – |
| H5 | Em B/A e C/B a energia acompanha o tempo | IC 95% da potência dentro de [0,98; 1,02] | – |

Os vereditos usam quatro termos, comuns em estudos confirmatórios de Engenharia de Software. Uma hipótese é
**confirmada** quando a regra de confirmação é atendida e **refutada** quando a regra de refutação é atendida. Quando
a hipótese tem as duas regras e nenhuma é atendida, ela é **inconclusiva**. Quando a hipótese só tem regra de
confirmação e essa regra não é atendida, ela é **não confirmada**. A explicação completa da escolha desses termos
está em [`evidencias/base-oficial/NOTA_TERMOS_VEREDITOS.txt`](evidencias/base-oficial/NOTA_TERMOS_VEREDITOS.txt).

---

## 📈 Principais resultados

A tabela abaixo resume as cargas principais. Cada célula mostra a razão das medianas e, entre colchetes, o intervalo
de confiança de 95%. O resultado completo, com todas as cargas e medidas, está em
[`resultados/oficial-20261101-termos/resumo.txt`](resultados/oficial-20261101-termos/resumo.txt).

| Carga | Comparação | Energia | Tempo | Potência média |
|---|---|---|---|---|
| lusearch | B/A (17 → 21) | 0,9335 [0,9192; 0,9479] | 0,9468 [0,9405; 0,9519] | 0,9835 [0,9761; 0,9970] |
| lusearch | C/B (21 → 25) | 1,0202 [1,0104; 1,0271] | 1,0101 [1,0049; 1,0127] | 1,0152 [1,0070; 1,0161] |
| lusearch | D/C (compactos) | 0,9955 [0,9888; 1,0175] | 0,9962 [0,9926; 1,0059] | 0,9997 [0,9848; 1,0093] |
| pmd | B/A (17 → 21) | 0,9597 [0,9502; 0,9751] | 0,9486 [0,9423; 0,9503] | 1,0133 [1,0103; 1,0342] |
| pmd | C/B (21 → 25) | 0,9546 [0,9401; 0,9617] | 0,9352 [0,9332; 0,9391] | 1,0142 [1,0052; 1,0260] |
| pmd | D/C (compactos) | 1,0037 [0,9903; 1,0154] | 1,0048 [1,0028; 1,0085] | 1,0018 [0,9874; 1,0121] |

Em resumo, a passagem do Java 17 para o 21 reduziu a energia nas duas cargas principais (cerca de 7% no lusearch e
4% no pmd). Do 21 para o 25, o pmd economizou mais 4,5%, enquanto o lusearch gastou 2% a mais. Já os cabeçalhos
compactos não trouxeram mudança de energia que se pudesse detectar, apesar de terem reduzido o trabalho do coletor
de lixo.

Os vereditos das hipóteses ficaram assim:

| Hipótese | lusearch | pmd |
|---|---|---|
| H1 energia menor em D | inconclusiva | inconclusiva |
| H2 potência D/C sem mudança | confirmada | confirmada |
| H3a heap menor em D | não confirmada | confirmada |
| H3b menos coletas/pausas em D | confirmada | confirmada |
| H5 B/A energia acompanha tempo | não confirmada | não confirmada |
| H5 C/B energia acompanha tempo | confirmada | não confirmada |

Quanto ao protocolo, os critérios E1, E3, E4 (pela mediana), E5 e E6 foram atendidos. O critério **E2 não foi
atendido**, pois a maior diferença de energia entre sessões foi de 6,1%, acima do limite de 5%, nas combinações
lusearch-A, pmd-A, pmd-B e pmd-D. Esse resultado do E2 é, ele mesmo,
uma lição importante. A energia absoluta muda de um dia para outro, mas as razões entre configurações dentro de cada
bloco ficaram estáveis entre as sessões. Por isso a recomendação é comparar configurações pelas razões dentro do
bloco, e não pela energia absoluta medida em dias diferentes. Todos os 180 processos foram considerados válidos.

O critério E7 foi avaliado numa sessão à parte, fora da amostra oficial, com 120 processos medidos do jeito
"ingênuo", isto é, em ordem fixa, sem núcleos fixos, sem pausas e com uma única iteração medida. Nas cargas
principais, 11 das 18 conclusões ficaram iguais às da coleta oficial e 7 mudariam, quase todas sobre a potência
média. Dois exemplos mostram o risco. No pmd, a medição ingênua indicaria que os cabeçalhos compactos reduzem a
potência em cerca de 7%, efeito que a coleta oficial não confirma. No lusearch, o aumento de 2% de energia do Java 21
para o 25 desapareceria. Além disso, o intervalo de confiança da energia ficou duas vezes mais largo (2,59 contra
1,25 pontos percentuais) e o CV passou de 5% em 5 das 8 combinações principais. Como o medidor exige ao menos uma
iteração de preparação, a sessão usou essa preparação mínima, o que está registrado como desvio. Os detalhes estão em
[`evidencias/ingenua-e7/LEIAME.txt`](evidencias/ingenua-e7/LEIAME.txt) e o resumo em
[`resultados/ingenua-e7-20261103/resumo-e7.txt`](resultados/ingenua-e7-20261103/resumo-e7.txt).

---

## 📂 Estrutura do repositório

O repositório está organizado assim:

```text
├── README.md / README.en.md        # Esta documentação (português / inglês)
├── LICENSE                         # Licença MIT (código)
├── LICENCA-DADOS.txt               # Licença CC BY 4.0 (dados, resultados, evidências, configuração)
├── CITATION.cff                    # Dados de citação
├── DATA-DICTIONARY.md              # Dicionário de dados (em inglês), com as colunas e campos de todos os arquivos
├── Dockerfile / .dockerignore      # Imagem que refaz a análise
├── config/
│   ├── execucao.json               # Protocolo fixado da coleta (JDKs, cargas, iterações, heap, pausas, SHA-256)
│   ├── registro-previo.json        # Critérios E1–E7, hipóteses H1–H5 e regras de decisão (antes da coleta)
│   ├── piloto-t12.json             # Configuração do piloto que definiu o protocolo
│   └── ingenua-e7.json             # Configuração da sessão ingênua do critério E7
├── dados/
│   ├── brutos/<sessão>/            # 4 sessões oficiais; uma pasta por processo (ex.: b01-001-lusearch-A)
│   ├── piloto/                     # Pilotos (fora da amostra oficial)
│   └── ingenua/                    # Sessão ingênua do critério E7 (fora da amostra oficial)
├── evidencias/
│   ├── manifestos/                 # SHA-256 de cada arquivo de cada sessão, dos pilotos e da sessão ingênua
│   ├── conferencias/               # Conferência de cada sessão e da coleta completa
│   ├── base-oficial/               # Como os resultados oficiais foram gerados, ocorrências e somas de verificação
│   ├── ingenua-e7/                 # Método, desvio e limitações da sessão ingênua
│   └── reproducao-windows/         # Reprodução limpa no Windows, a partir de um clone novo
├── resultados/
│   ├── oficial-20261101/           # Resultados oficiais (versão base-oficial-v1)
│   ├── oficial-20261101-termos/    # Mesmos números com os termos atuais dos vereditos (USE ESTA)
│   └── ingenua-e7-20261103/        # Comparação da sessão ingênua com a coleta oficial (critério E7)
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
│   ├── sessao_ingenua.sh           # Executa a sessão ingênua do critério E7
│   ├── analisar_ingenua.py         # Compara a sessão ingênua com a coleta oficial
│   └── tests/                      # Testes dos scripts de coleta
└── .github/workflows/analise.yml   # Conferência automática (estilo, tipos, testes, reprodução e Docker)
```

Cada processo medido tem a sua própria pasta, com um nome como `b01-001-lusearch-A` (bloco 1, primeiro processo da
sessão, carga lusearch, configuração A). Dentro dela ficam:

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

Existem duas formas de reproduzir este trabalho, e cada uma exige um nível diferente de preparação.

A primeira é **refazer a análise**. Você usa os dados que já estão no repositório, confere que eles não foram
alterados e recalcula todos os números a partir dos dados brutos. Funciona em qualquer computador (Windows, Linux ou
macOS) e leva uns 5 minutos.

A segunda é **repetir a coleta**, ou seja, medir tudo de novo em outra máquina e analisar os dados novos. Essa exige
um computador com Linux e processador Intel com RAPL, além de cerca de 4 horas de máquina, fora a preparação.

| Nível | O que faz | Onde roda | Tempo |
|---|---|---|---|
| **1. Refazer a análise** | confere os dados e recalcula todos os números a partir dos dados brutos do repositório | Windows, Linux ou macOS | ~5 min |
| **2. Repetir a coleta** | mede de novo em outra máquina e analisa os dados novos | Linux com Intel RAPL | ~4 h de máquina + preparação |

Em ambos os casos, os comandos devem ser executados **na pasta raiz do projeto**, que é a pasta onde está este
README, usando um terminal *bash*. No Linux e no macOS, basta abrir o Terminal. No Windows, use o **Git Bash**, que vem
junto com o [Git para Windows](https://git-scm.com/download/win). Quando algum comando for diferente no PowerShell,
isso está indicado no texto.

#### Sistemas operacionais

A tabela abaixo mostra em quais sistemas cada nível já foi conferido e o que muda em cada um.

| Sistema | Nível 1 (análise) | Nível 2 (coleta) | Observações |
|---|---|---|---|
| **Linux** | conferido | conferido | sistema da coleta original (Zorin OS, baseado no Ubuntu). A conferência automática do GitHub roda a cada mudança num Ubuntu 24.04 |
| **Windows** | conferido | não funciona | reprodução limpa feita no Windows com Git Bash e Python 3.13, registrada em [`evidencias/reproducao-windows/`](evidencias/reproducao-windows/LEIAME.txt). Use o Git Bash, ou o Docker |
| **macOS** | esperado, ainda não conferido | não funciona | os scripts usam só recursos presentes no macOS. O macOS não traz Python 3.10+, então instale-o pelo [site oficial](https://www.python.org/downloads/macos/) ou pelo Homebrew. O Docker também é uma opção |

A coleta não funciona no Windows nem no macOS porque o contador de energia RAPL só é lido pelo Linux. Os Macs com chip
Apple, além disso, não têm esse contador. Para refazer a análise, qualquer um dos três sistemas serve, e os números
saem idênticos byte a byte. Só as figuras podem ter pequenas diferenças de imagem entre sistemas.

---

### 🔁 Nível 1 – Refazer a análise (qualquer computador)

#### Pré-requisitos

Você vai precisar apenas do Git e do Python:

| Programa | Versão | Como conferir | Onde obter |
|---|---|---|---|
| Git | qualquer recente | `git --version` | <https://git-scm.com/downloads> |
| Python | **3.10 ou mais novo** (oficial: 3.12 e 3.13) | `python --version` ou `python3 --version` | <https://www.python.org/downloads/> |
| Espaço em disco | ~300 MB | – | – |
| Internet | só para baixar o repositório e as bibliotecas | – | – |

No Windows, durante a instalação do Python, lembre de marcar a opção **"Add python.exe to PATH"**. Sem ela, o
terminal não encontra o Python.

#### Passo 1 – Baixar o repositório

Comece baixando o repositório e entrando na pasta dele:

```bash
git clone https://github.com/evertoncg10/java-energy-study.git
cd java-energy-study
```

Se quiser trabalhar exatamente com a versão usada na análise publicada, troque para a marca correspondente. Esse
passo é opcional:

```bash
git checkout analise-v1.1
```

#### Passo 2 – Conferir a integridade dos dados

Antes de analisar, vale confirmar que os dados que você baixou são os mesmos que foram medidos. Ao fim de cada
sessão, gravamos um manifesto com o SHA-256 de cada arquivo, e o script abaixo compara os arquivos atuais com esses
manifestos:

```bash
bash scripts/conferir_dados.sh
```

Se estiver tudo certo, cada linha mostra `CONFERE` e a última diz
`RESULTADO: todos os dados conferem com os manifestos.` O script também refaz a conferência da coleta completa, com o
resumo de cada sessão.

#### Passo 3 – Refazer a análise (opção A: um comando)

A forma mais simples é deixar um script fazer tudo:

```bash
bash scripts/reproduzir_analise.sh
```

Na primeira vez, ele cria um ambiente virtual do Python em `analise/.venv` e instala as bibliotecas exatamente nas
versões usadas na análise oficial. Depois roda os testes automáticos, refaz a análise em uma pasta nova
(`resultados/reproducao-AAAAMMDD-HHMMSS`) e compara o resultado com os números oficiais. Depois da instalação, o
processo todo leva cerca de 1 minuto. No final, você deve ver algo assim:

```text
idêntico: razoes.csv
idêntico: resumo.txt
...
Arquivos diferentes: 0
```

Se quiser gerar também as figuras, rode `bash scripts/reproduzir_analise.sh --com-figuras`.

#### Passo 3 – Refazer a análise (opção B: comando por comando)

Se preferir entender cada etapa, ou se estiver usando o PowerShell ou o Prompt de Comando, siga os comandos abaixo.

1. Crie o ambiente virtual. Isso só é necessário na primeira vez:

   ```bash
   python -m venv analise/.venv        # se "python" não existir, use python3
   ```

2. Ative o ambiente virtual. Isso precisa ser feito em todo terminal novo, e o comando depende do sistema:

   | Sistema / terminal | Comando |
   |---|---|
   | Windows – Git Bash | `source analise/.venv/Scripts/activate` |
   | Windows – PowerShell | `analise\.venv\Scripts\Activate.ps1` |
   | Windows – Prompt de Comando (CMD) | `analise\.venv\Scripts\activate.bat` |
   | Linux ou macOS | `source analise/.venv/bin/activate` |

   Você sabe que deu certo quando o terminal passa a mostrar `(.venv)` no começo da linha. No Windows, rode também
   `export PYTHONUTF8=1` (Git Bash) ou `$env:PYTHONUTF8=1` (PowerShell), para que os acentos apareçam corretamente.

3. Instale as bibliotecas nas versões travadas e rode os testes:

   ```bash
   cd analise
   python -m pip install -r requisitos-travados.txt -e ".[dev,figuras]"
   python -m pytest
   cd ..
   ```

   Os testes devem terminar com `41 passed`.

4. Agora rode a análise completa, com as figuras:

   ```bash
   pae-analise analisar --saida resultados/reproducao
   ```

   A pasta de saída precisa ser nova, porque o programa nunca sobrescreve resultados. Para rodar de novo, use outro
   nome, como `resultados/reproducao2`. O comando aceita algumas opções, como `--sem-figuras` (não gera as figuras),
   `--reamostragens N` (padrão 10000) e `--semente N` (código de sorteio do *bootstrap*, padrão 20261101). Só os
   valores padrão reproduzem os números oficiais.

5. Por fim, compare o seu resultado com o oficial:

   ```bash
   python scripts/comparar_resultados.py resultados/oficial-20261101-termos resultados/reproducao --ignorar-figuras
   ```

   O esperado é `Arquivos diferentes: 0`. Dois detalhes ajudam a interpretar a saída. O arquivo `metadados.json`
   sempre muda, porque registra a data, o sistema e o commit de cada execução; por isso o script confere nele só o
   campo `input_sha256`, que identifica os dados de entrada. Já as figuras ficam de fora com `--ignorar-figuras`
   porque só saem idênticas byte a byte no mesmo sistema operacional. Os números, nos arquivos CSV, JSON e texto,
   saem idênticos no Windows, no Linux e no macOS.

6. Se você só quiser a base consolidada, com uma linha por processo, para trabalhar os dados em outra ferramenta
   (uma planilha, o R etc.), use:

   ```bash
   pae-analise consolidar --saida resultados/base
   ```

#### Opção C: Docker

Se você tem o [Docker](https://docs.docker.com/get-docker/) instalado, nem precisa do Python. Basta construir a imagem
e rodá-la:

```bash
docker build -t pae-jvm-analise .
docker run --rm pae-jvm-analise
```

O contêiner refaz a análise e mostra a comparação com os resultados oficiais. Também aqui, o esperado é
`Arquivos diferentes: 0`. Se quiser guardar a análise completa, com as figuras, na pasta `resultados/reproducao-docker`
do seu computador, use:

```bash
docker run --rm -v "$(pwd)/resultados:/saida" pae-jvm-analise pae-analise analisar --saida /saida/reproducao-docker
```

No PowerShell, troque `$(pwd)` por `${PWD}`.

#### Arquivos gerados pela análise

A pasta de saída da análise contém os seguintes arquivos:

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

A comparação do critério E7 tem um script próprio, pois usa outra sessão. Para refazê-la, use uma pasta de saída nova:

```bash
python3 scripts/analisar_ingenua.py --sessao dados/ingenua/ingenua-20261103T194354Z --saida resultados/e7-reproducao
```

O melhor ponto de partida é o `resumo.txt`, que reúne os principais números em texto corrido. O significado de cada coluna desses
arquivos, e de cada campo dos dados brutos, está no [dicionário de dados](DATA-DICTIONARY.md), escrito em inglês para
atender também pesquisadores de outros países.

#### Conferência automática

Você não precisa confiar só na nossa palavra. A cada alteração no repositório, o GitHub Actions
([`.github/workflows/analise.yml`](.github/workflows/analise.yml)) instala as versões travadas, verifica o estilo
(ruff), os tipos (mypy) e os testes (pytest), confere a integridade dos dados, refaz a análise e compara o resultado
com o oficial. Ele também constrói e roda a imagem Docker.

---

### 🔬 Nível 2 – Repetir a coleta (Linux com Intel RAPL)

Repetir a coleta significa medir tudo de novo, em outro computador. Vale alinhar a expectativa desde já. Os valores
absolutos de energia dependem do equipamento, então não vão bater com os nossos. O que se espera reproduzir é a
**direção e o tamanho das razões** entre as configurações, usando o mesmo protocolo.

#### Pré-requisitos

A coleta tem exigências bem mais específicas que a análise, porque depende do contador de energia do processador:

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

Para instalar os programas no Ubuntu, Debian, Zorin OS ou Mint, use:

```bash
sudo apt update
sudo apt install git python3 python3-venv curl unzip zip coreutils maven
```

Para instalar o SDKMAN, use os comandos abaixo (depois, abra um terminal novo):

```bash
curl -s "https://get.sdkman.io" | bash
source "$HOME/.sdkman/bin/sdkman-init.sh"
sdk install java 21.0.11-tem      # serve como Java padrão; não interfere na coleta
```

Se o seu processador não for Intel híbrido, a coleta ainda funciona, mas é preciso desligar a afinidade de núcleos.
A seção [Adaptar a outro equipamento](#adaptar-a-outro-equipamento) explica como.

#### Passo 1 – Baixar o repositório

```bash
git clone https://github.com/evertoncg10/java-energy-study.git
cd java-energy-study
```

#### Passo 2 – Preparar o ambiente

Deixamos um script que prepara a máquina de uma vez:

```bash
bash scripts/preparar_ambiente_coleta.sh
```

Ele começa conferindo o sistema. Depois instala pelo SDKMAN os JDKs `17.0.19-tem`, `21.0.11-tem` e `25.0.3-tem`, sem
mexer no Java padrão do seu computador. Em seguida, baixa a DaCapo do endereço oficial registrado em
[`ferramentas/dacapo.json`](ferramentas/dacapo.json), confere o SHA-256 oficial do arquivo e o extrai em
`ferramentas/dacapo/`. Por fim, instala o JAR da DaCapo no repositório local do Maven, compila e testa o medidor e
compara os SHA-256 com os registrados em [`config/execucao.json`](config/execucao.json).

Cada linha da saída mostra `[ok]`, `[aviso]` ou `[erro]`, para você saber o que aconteceu. O script pode ser
executado quantas vezes for preciso, porque o que já estiver pronto é apenas conferido. O download da DaCapo pode levar de
alguns minutos a algumas horas, dependendo da sua internet.

<details>
<summary>Prefere fazer à mão? Veja o mesmo passo, comando por comando</summary>

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
JAVA_HOME="$HOME/.sdkman/candidates/java/25.0.3-tem" mvn -f medidor-java/pom.xml clean package
sha256sum medidor-java/target/java-energy-meter-0.1.0.jar   # original: 415ddd802fbcde66e77e2f7c1262e79680d92b8fef7a49468a1559ff26339995

# Testes dos scripts de coleta
python3 -m unittest discover -s scripts/tests
```

</details>

O medidor original foi compilado com o Temurin 25.0.3, e o projeto fixa a data gravada dentro do JAR. Por isso,
compilando com esse mesmo JDK, o resultado sai idêntico ao original, byte a byte (isso foi conferido no notebook do
estudo em 03/11/2026). Se mesmo assim o SHA-256 do seu medidor sair diferente, a causa é outro JDK ou outra versão do
Maven. O código é idêntico, mas, por segurança, o programa recusa um JAR que não confere. Nesse caso, faça uma cópia da configuração, registre nela o novo valor e anote isso
como um desvio do protocolo:

```bash
cp config/execucao.json config/replicacao.json
sha256sum medidor-java/target/java-energy-meter-0.1.0.jar
# edite config/replicacao.json: troque "meter" → "sha256" pelo valor mostrado acima
```

A partir daí, acrescente `--config config/replicacao.json` aos comandos dos passos 4 e 6.

#### Passo 3 – Liberar a leitura do contador RAPL

Por segurança, o Linux só deixa o administrador ler o contador de energia. O comando abaixo libera a leitura apenas
desse contador para o seu usuário. Ele vai pedir a sua senha do `sudo` no próprio terminal; o programa não vê nem
guarda a senha.

```bash
bash scripts/executar.sh preparar --configuracao A --liberar-leitura
```

Essa liberação dura até o computador ser reiniciado. Depois de reiniciar, basta rodar o comando de novo. Para quem
tiver curiosidade, ele equivale a
`sudo chown $(id -u) /sys/devices/virtual/powercap/intel-rapl/intel-rapl:0/energy_uj`.

#### Passo 4 – Execução de verificação

Antes da coleta de verdade, faça uma execução de teste. Ela fica fora da amostra e é gravada em `dados/verificacao/`,
uma pasta que não vai para o Git:

```bash
bash scripts/executar.sh executar --configuracao D --aplicacao pmd
```

Se tudo estiver certo, aparece uma linha em JSON terminando com `"status": "success"`. Esse único teste já confirma
que o SDKMAN, o JDK, os cabeçalhos compactos, o RAPL, a afinidade de núcleos, a DaCapo e o medidor estão funcionando.

#### Passo 5 – Preparar a máquina antes de cada sessão

Cada sessão leva cerca de 1 hora (a quarta, que é menor, leva uns 47 minutos). Como qualquer atividade paralela
interfere na energia medida, prepare a máquina antes de começar:

1. Ligue o carregador e mantenha-o ligado até o fim.
2. Feche todos os outros programas, inclusive navegador, editores, sincronização de nuvem e antivírus em varredura.
3. Desligue a suspensão automática e o descanso de tela durante a sessão.
4. Não use o computador enquanto a sessão estiver rodando.
5. Deixe a máquina parada por alguns minutos antes de começar, porque a temperatura medida no início define as
   pausas da sessão.
6. Confira se o contador RAPL está liberado (passo 3).

#### Passo 6 – Planejar as sessões

O próximo passo é gravar os planos das sessões. O script abaixo cria os 4 planos com o mesmo desenho da coleta
original (15 blocos divididos em 4 + 4 + 4 + 3, com os códigos de sorteio 20261101 a 20261104) e os guarda em uma
pasta fora do repositório:

```bash
bash scripts/planejar_sessoes_oficiais.sh ../planos-pae-jvm
# se você criou uma configuração de replicação:
# bash scripts/planejar_sessoes_oficiais.sh ../planos-pae-jvm config/replicacao.json
```

Como os códigos de sorteio são os mesmos, a ordem dos processos sai **idêntica** à da coleta original. Conferimos
isso comparando os planos gerados com os arquivos `plano-antes-execucao.json` das 4 sessões. Se quiser criar um plano
de cada vez, o comando é este:

```bash
python3 scripts/sessao.py planejar --config config/execucao.json --categoria oficial \
  --blocos 4 --primeiro-bloco 1 --semente 20261101 --plano ../planos-pae-jvm/plano-sessao1.json
```

#### Passo 7 – Executar as sessões

Rode uma sessão de cada vez, de preferência em dias diferentes, e repita o passo 5 antes de cada uma:

```bash
python3 scripts/sessao.py executar --plano ../planos-pae-jvm/plano-sessao1.json
```

Durante a sessão, o terminal mostra `ok` ou `FALHA` a cada processo. No final aparece
`SESSAO=dados/brutos/<pasta da sessão>`, com o nome da pasta onde os dados foram gravados. Se a sessão for
interrompida, por uma queda de energia por exemplo, é possível continuar de onde parou, sem repetir o que já foi
feito:

```bash
python3 scripts/sessao.py executar --plano ../planos-pae-jvm/plano-sessao1.json --retomar
```

Depois, faça o mesmo com `plano-sessao2.json`, `plano-sessao3.json` e `plano-sessao4.json`.

#### Passo 8 – Congelar e conferir cada sessão

Assim que cada sessão terminar, gere o manifesto e confira a qualidade dos dados. Troque `PASTA` pelo nome que
apareceu em `SESSAO=`:

```bash
python3 scripts/manifesto.py gerar --sessao dados/brutos/PASTA \
  --saida ../manifestos-pae-jvm/sessao1.json --plano ../planos-pae-jvm/plano-sessao1.json
python3 scripts/conferir_sessao.py --sessao dados/brutos/PASTA
```

O manifesto registra o SHA-256 de todos os arquivos da sessão, e o programa nunca sobrescreve um manifesto já
existente. A conferência mostra a duração, as falhas, as temperaturas, a cobertura das leituras e o CV de cada
combinação, e termina com `CONFERE` (tudo certo) ou `NAO_CONFERE` (há algum problema). Quando as 4 sessões estiverem
prontas, confira a coleta inteira, o que inclui o critério E2:

```bash
python3 scripts/conferir_coleta.py \
  --sessao dados/brutos/PASTA1 --manifesto ../manifestos-pae-jvm/sessao1.json \
  --sessao dados/brutos/PASTA2 --manifesto ../manifestos-pae-jvm/sessao2.json \
  --sessao dados/brutos/PASTA3 --manifesto ../manifestos-pae-jvm/sessao3.json \
  --sessao dados/brutos/PASTA4 --manifesto ../manifestos-pae-jvm/sessao4.json
```

#### Passo 9 – Analisar os dados novos

A análise lê **todas** as sessões que estiverem em `dados/brutos/` e todos os manifestos
`evidencias/manifestos/sessao*.json`. Para analisar só os seus dados, tire dessas pastas as 4 sessões e os manifestos
originais e coloque os seus manifestos no lugar. Não se preocupe com os originais, pois o Git guarda todos eles.

```bash
mkdir -p ../originais-pae-jvm
mv dados/brutos/20261022T2152* ../originais-pae-jvm/
mv evidencias/manifestos/sessao*.json ../originais-pae-jvm/
cp ../manifestos-pae-jvm/sessao*.json evidencias/manifestos/
```

O Git vai mostrar esses arquivos como removidos, o que é esperado. Para voltar ao estado original depois, use
`git checkout -- dados/brutos evidencias/manifestos`.

Em seguida, ative o ambiente da análise (Nível 1, passo 3, itens 1 a 3) e rode:

```bash
pae-analise analisar --saida resultados/replicacao
```

Para avaliar a replicação, compare o seu `resultados/replicacao/resumo.txt` com o oficial, principalmente as razões
D/C, C/B e B/A.

#### Adaptar a outro equipamento

Nem todo computador é igual ao que usamos. Se for preciso mudar alguma coisa no protocolo, faça a mudança em uma
**cópia** da configuração (por exemplo, `config/replicacao.json`) e registre a mudança como desvio. As situações mais
comuns são estas:

| Situação | O que mudar na cópia |
|---|---|
| Processador sem núcleos híbridos (sem `/sys/devices/cpu_core`) | `"cpu_affinity": null` |
| Contador RAPL em outro caminho | `"rapl_directory"` com o caminho do domínio `package-0` |
| SHA-256 do medidor diferente | `"meter"` → `"sha256"` com o valor novo |

Os JDKs, a DaCapo, as cargas, as iterações, o heap e as pausas não devem mudar. Se mudarem, o que você terá é um
novo experimento, e não uma repetição deste protocolo.

---

## 🛠️ Solução de problemas

Reunimos aqui os problemas mais comuns e o que fazer em cada caso. As mensagens aparecem em português porque é a
língua do programa.

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

Três versões do repositório estão marcadas com etiquetas do Git, para que possam ser recuperadas a qualquer momento:

| Marca | Conteúdo |
|---|---|
| `base-oficial-v1` | base oficial fechada depois da coleta, resultados em `resultados/oficial-20261101` |
| `analise-v1.1` | mesmos números, com os vereditos nos termos confirmada, não confirmada, refutada e inconclusiva (`resultados/oficial-20261101-termos`) |
| `v1.0` | pacote de artefatos completo, com a sessão ingênua do critério E7, o dicionário de dados e o medidor reproduzível; é a versão depositada no Zenodo |

A pasta [`evidencias/base-oficial/`](evidencias/base-oficial/) explica como os resultados oficiais foram gerados e
traz o registro de ocorrências e as somas de verificação.

---

## 🌍 Ciência aberta

Este trabalho segue as práticas de **Ciência Aberta**, e tudo o que sustenta os resultados está disponível para quem
quiser conferir. Isso inclui o protocolo fixado e o registro prévio de critérios, hipóteses e regras de decisão,
gravados antes da coleta; os dados brutos de todos os 180 processos oficiais e dos pilotos, sem nenhuma exclusão, com
os manifestos SHA-256; o código do medidor, dos scripts de coleta e da análise, com testes automáticos; as versões
exatas das bibliotecas, a imagem Docker e a conferência automática da reprodução; e, por fim, os resultados oficiais
junto com o registro de ocorrências e desvios.

Apenas duas coisas ficam fora do repositório, por causa do tamanho. A primeira é o arquivo da DaCapo, que pode ser
baixado do site oficial e conferido pelo SHA-256. A segunda são as pastas de trabalho (`scratch`) que a DaCapo cria em
cada processo. Elas constam dos manifestos e fazem parte dos pacotes completos das sessões, publicados no Zenodo junto
com a versão v1.0 deste repositório, com o DOI [10.5281/zenodo.23982640](https://doi.org/10.5281/zenodo.23982640).

---

## ⚠️ Limitações

Como toda pesquisa, esta tem limites que precisam ser considerados na leitura dos resultados. A energia medida é a do
**pacote do processador**, pelo RAPL. Não é a energia da tomada, nem a energia só da JVM, e o RAPL é uma estimativa
do próprio processador, sem calibração externa. Todas as medidas vieram de uma única máquina, um notebook, com um
único sistema operacional, então os valores absolutos não valem para outros equipamentos. O critério E2 não foi
atendido (6,1% de diferença entre sessões, para um limite de 5%), o que reforça a recomendação de comparar razões
dentro do bloco, e não energia absoluta entre dias diferentes. Por fim, usamos três cargas da DaCapo, com uma thread
e heap fixo de 1 GB; outras cargas e outras configurações podem se comportar de forma diferente.

---

## 🤖 Uso de inteligência artificial

Este repositório teve o apoio do assistente Claude (Anthropic) na escrita da documentação (README e dicionário de
dados) e como auxílio na implementação dos scripts e do código em Python da análise estatística, desenvolvidos sob a
condução do autor. As decisões de método, a coleta dos dados e a interpretação dos resultados são do autor, que revisou
todo o material e é o responsável pelo trabalho.

---

## 📜 Licenças

O **código** (pastas `analise/`, `medidor-java/` e `scripts/`) está sob a licença MIT, descrita em
[`LICENSE`](LICENSE). Os **dados, resultados, evidências e configurações** (pastas `dados/`, `resultados/`,
`evidencias/` e `config/`) estão sob a licença Creative Commons Atribuição 4.0 Internacional (CC BY 4.0), descrita em
[`LICENCA-DADOS.txt`](LICENCA-DADOS.txt). A DaCapo (Apache-2.0, com as licenças próprias de cada aplicação) e os JDKs
Eclipse Temurin mantêm as suas próprias licenças e não fazem parte deste repositório.

---

## 📝 Como citar

Se este trabalho for útil para você, por favor cite-o. Os dados de citação estão em [`CITATION.cff`](CITATION.cff), e
o GitHub mostra a referência pronta no botão **"Cite this repository"**. O registro no Zenodo tem o DOI
[10.5281/zenodo.23982640](https://doi.org/10.5281/zenodo.23982640). Em BibTeX:

```bibtex
@software{goncalves_pae_jvm_2026,
  author  = {Gonçalves, Everton Cezar},
  title   = {{PAE-JVM – Protocolo de Avaliação Energética de configurações da JVM: dados, análise e código}},
  year    = {2026},
  version = {1.0},
  doi     = {10.5281/zenodo.23982640},
  url     = {https://github.com/evertoncg10/java-energy-study}
}
```

**Autor:** Everton Cezar Gonçalves – Universidade Tecnológica Federal do Paraná (UTFPR) –
ORCID [0009-0003-7648-2501](https://orcid.org/0009-0003-7648-2501).
