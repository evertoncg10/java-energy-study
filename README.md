# PAE-JVM – Protocolo de Avaliação Energética de configurações da JVM

Repositório da pesquisa sobre o consumo de energia de versões e configurações da máquina virtual Java (JVM),
feita na Universidade Tecnológica Federal do Paraná (UTFPR) dentro da linha de software verde.

O artefato da pesquisa é o **PAE-JVM**, um protocolo para medir e comparar a energia de configurações da JVM
com dados que outra pessoa consegue conferir e refazer. O experimento descrito aqui é a avaliação desse
protocolo, com critérios (E1 a E7) e hipóteses (H1 a H5) fixados antes da coleta em
[`config/registro-previo.json`](config/registro-previo.json).

## O que foi comparado

| Configuração | JDK (Eclipse Temurin) | Observação |
|---|---|---|
| A | 17.0.19 | |
| B | 21.0.11 | |
| C | 25.0.3 | cabeçalhos compactos desligados (`-XX:-UseCompactObjectHeaders`) |
| D | 25.0.3 | cabeçalhos compactos ligados (`-XX:+UseCompactObjectHeaders`) |

Cargas da suíte DaCapo 23.11-MR2-chopin: **lusearch** e **pmd** (principais) e **avrora** (exploratória).
Energia lida pelo RAPL do processador (pacote), com uma JVM nova por processo.

Coleta oficial: 4 sessões, 15 blocos completos, 180 processos (todos válidos, nenhuma falha).
Os parâmetros fixos da coleta estão em [`config/execucao.json`](config/execucao.json).

## Pastas

| Pasta | Conteúdo |
|---|---|
| `config/` | parâmetros da coleta e registro prévio (critérios, hipóteses e regras de decisão) |
| `dados/brutos/` | dados brutos das 4 sessões oficiais, um subdiretório por processo |
| `dados/piloto/` | dados dos pilotos que definiram o protocolo (fora da amostra oficial) |
| `evidencias/manifestos/` | SHA-256 de cada arquivo de cada sessão, gerados ao fim da sessão |
| `evidencias/conferencias/` | conferência de cada sessão e da coleta completa contra o protocolo |
| `evidencias/base-oficial/` | como os resultados oficiais foram gerados, ocorrências e somas de verificação |
| `resultados/` | resultados oficiais da análise (use `oficial-20261101-termos`) |
| `analise/` | pacote Python `pae-analise`, que consolida os dados e faz toda a análise |
| `medidor-java/` | medidor de energia que roda junto da carga DaCapo |
| `scripts/` | execução das sessões, manifestos, conferências e comparação de resultados |
| `ferramentas/` | versão, endereço e SHA-256 da suíte DaCapo (o arquivo da suíte não fica no repositório) |

## Refazer a análise

A análise usa só os dados do repositório e leva menos de um minuto. Os números (arquivos CSV, JSON e texto)
saem idênticos byte a byte em Windows e Linux. As figuras só saem idênticas no mesmo sistema operacional.

Todos os comandos abaixo rodam **na pasta raiz do projeto** (a pasta onde está este README).

### Com Python (3.10 ou mais novo; a análise oficial usou 3.12 e 3.13)

Criar o ambiente virtual e instalar as versões travadas (só na primeira vez):

```bash
python -m venv analise/.venv
source analise/.venv/Scripts/activate      # Windows (Git Bash)
# source analise/.venv/bin/activate        # Linux ou macOS
cd analise
python -m pip install -r requisitos-travados.txt -e ".[dev,figuras]"
pytest
cd ..
```

Nas próximas vezes, basta ativar o ambiente com a linha `source` do seu sistema. No Windows, rode também
`export PYTHONUTF8=1` antes da análise.

Refazer a análise e comparar com os resultados oficiais:

```bash
pae-analise analisar --saida resultados/reproducao
python scripts/comparar_resultados.py resultados/oficial-20261101-termos resultados/reproducao
```

Em outro sistema operacional, ou sem figuras (`--sem-figuras`), compare só os números:

```bash
python scripts/comparar_resultados.py resultados/oficial-20261101-termos resultados/reproducao --ignorar-figuras
```

O resultado esperado é `Arquivos diferentes: 0`. O arquivo `metadados.json` sempre muda (data, sistema e
commit); o script confere nele apenas o campo `input_sha256`, que identifica os dados de entrada.

### Com Docker

```bash
docker build -t pae-jvm-analise .
docker run --rm pae-jvm-analise
```

O contêiner refaz a análise e mostra a comparação com os resultados oficiais. Para gravar a análise
completa, com figuras, numa pasta do computador:

```bash
docker run --rm -v "$(pwd)/resultados:/saida" pae-jvm-analise pae-analise analisar --saida /saida/reproducao-docker
```

### Conferência automática

A cada alteração, o GitHub Actions roda estilo, tipos, testes, a reprodução dos resultados oficiais e a
imagem Docker ([`.github/workflows/analise.yml`](.github/workflows/analise.yml)).

## Refazer a coleta

A coleta precisa de um computador com Linux instalado direto na máquina (sem máquina virtual nem contêiner)
e processador que exponha o RAPL em `/sys/class/powercap/intel-rapl:0`. Os valores medidos dependem do
equipamento; o que se espera reproduzir são as razões entre configurações, não a energia absoluta.

1. Instalar o SDKMAN e os JDKs `17.0.19-tem`, `21.0.11-tem` e `25.0.3-tem`.
2. Baixar a DaCapo 23.11-MR2-chopin do endereço em [`ferramentas/dacapo.json`](ferramentas/dacapo.json),
   conferir o SHA-256 e extrair em `ferramentas/dacapo/`.
3. Instalar o JAR da DaCapo no repositório local do Maven e compilar o medidor
   (`mvn -f medidor-java/pom.xml package`). O SHA-256 do JAR usado está em `config/execucao.json`.
4. Planejar e executar cada sessão. O plano é gravado antes da execução e a ordem dos processos sai do
   código de sorteio:

   ```bash
   python3 scripts/sessao.py planejar --config config/execucao.json --categoria oficial \
       --blocos 4 --primeiro-bloco 1 --semente 20261101 --plano plano-sessao1.json
   python3 scripts/sessao.py executar --plano plano-sessao1.json
   ```

5. Gerar o manifesto da sessão e conferir a sessão e a coleta:

   ```bash
   python3 scripts/manifesto.py gerar --sessao dados/brutos/PASTA_DA_SESSAO --saida evidencias/manifestos/sessao1.json
   python3 scripts/conferir_sessao.py --sessao dados/brutos/PASTA_DA_SESSAO
   python3 scripts/conferir_coleta.py --sessao dados/brutos/PASTA_1 --manifesto evidencias/manifestos/sessao1.json  # repetir por sessão
   ```

As sessões oficiais usaram os códigos de sorteio 20261101 a 20261104, com 4, 4, 4 e 3 blocos
(primeiros blocos 1, 5, 9 e 13). Os planos usados estão dentro de cada pasta de sessão
(`plano-antes-execucao.json`).

## Versões marcadas

| Marca | Conteúdo |
|---|---|
| `base-oficial-v1` | base oficial fechada após a coleta, com os resultados `resultados/oficial-20261101` |
| `analise-v1.1` | mesmos números, com os vereditos nos termos confirmada, não confirmada, refutada e inconclusiva (`resultados/oficial-20261101-termos`) |

A mudança de termos está explicada em `evidencias/base-oficial/NOTA_TERMOS_VEREDITOS.txt`.

## O que não está no repositório

- O arquivo da suíte DaCapo (cerca de 6 GB), que se baixa do site oficial e se confere pelo SHA-256.
- As pastas de trabalho da DaCapo (`scratch`) de cada processo. Elas entram nos manifestos e nos pacotes
  completos das sessões, que serão publicados junto com os dados.

## Licenças

- Código (`analise/`, `medidor-java/`, `scripts/`): licença MIT, em [`LICENSE`](LICENSE).
- Dados, resultados e evidências (`dados/`, `resultados/`, `evidencias/`, `config/`): Creative Commons
  Atribuição 4.0 Internacional (CC BY 4.0), em [`LICENCA-DADOS.txt`](LICENCA-DADOS.txt).
- A suíte DaCapo e os JDKs mantêm as licenças próprias.

## Como citar

Os dados de citação estão em [`CITATION.cff`](CITATION.cff); o GitHub mostra a referência pronta no botão
"Cite this repository".
