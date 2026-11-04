#!/usr/bin/env bash
# Prepara um computador Linux para repetir a coleta do PAE-JVM e confere cada peça contra o que
# foi usado na coleta original (versões e SHA-256 registrados em config/execucao.json e
# ferramentas/dacapo.json). Pode ser executado de novo: o que já está pronto é só conferido.
#
# Uso (na pasta raiz do projeto, como usuário comum, SEM sudo):
#     bash scripts/preparar_ambiente_coleta.sh
#
# Etapas:
#   1. confere o sistema (Linux, RAPL de pacote, núcleos de desempenho, alimentação externa);
#   2. confere as ferramentas (python3, curl, unzip, sha256sum, Maven, SDKMAN);
#   3. instala pelo SDKMAN os JDKs Temurin 17.0.19, 21.0.11 e 25.0.3 (sem mudar o Java padrão);
#   4. baixa a DaCapo 23.11-MR2-chopin (cerca de 6,3 GB; precisa de ~23 GB livres), confere o
#      SHA-256 oficial e extrai em ferramentas/dacapo/;
#   5. se o medidor ainda não existe (ou não confere), instala o JAR da DaCapo no repositório local
#      do Maven e compila o medidor com os testes usando o Temurin 25.0.3, o mesmo da coleta original;
#      um medidor que já confere não é recompilado;
#   6. compara o SHA-256 do medidor e da DaCapo com config/execucao.json.
# Não pede senha e não altera configurações do sistema. A liberação de leitura do RAPL é feita
# depois, à parte, com: bash scripts/executar.sh preparar --configuracao A --liberar-leitura
set -euo pipefail
raiz=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$raiz"

ok()    { printf '  [ok]    %s\n' "$*"; }
aviso() { printf '  [aviso] %s\n' "$*"; }
erro()  { printf '  [erro]  %s\n' "$*" >&2; exit 1; }
valor() { python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); [d:=d[k] for k in sys.argv[2:]]; print(d)' "$@"; }

[[ $(id -u) -ne 0 ]] || erro "Execute como usuário comum, sem sudo."

echo "== 1/6 Sistema"
[[ $(uname -s) == Linux ]] || erro "A coleta exige Linux instalado direto na máquina."
ok "Linux $(uname -r)"
if command -v systemd-detect-virt > /dev/null 2>&1 && systemd-detect-virt -q; then
  aviso "Máquina virtual ou contêiner detectado ($(systemd-detect-virt)); o RAPL costuma não existir ou não ser confiável aqui."
fi
rapl=$(valor config/execucao.json rapl_directory)
[[ -r $rapl/name ]] || erro "RAPL não encontrado em $rapl (processador ou kernel sem powercap RAPL)."
ok "RAPL: $rapl ($(cat "$rapl/name"))"
if [[ -r /sys/devices/cpu_core/cpus ]]; then
  ok "Núcleos de desempenho (P-cores): $(cat /sys/devices/cpu_core/cpus)"
else
  aviso "Processador sem núcleos híbridos (cpu_core). A política de afinidade da coleta original não se aplica;"
  aviso "use uma cópia de config/execucao.json com \"cpu_affinity\": null e relate isso como desvio."
fi
if grep -qs '^1$' /sys/class/power_supply/*/online 2> /dev/null; then ok "Alimentação externa ligada"; else aviso "Alimentação externa não confirmada; a coleta exige o carregador ligado."; fi

echo "== 2/6 Ferramentas"
for programa in python3 curl unzip sha256sum mvn java; do
  if command -v "$programa" > /dev/null 2>&1; then ok "$programa"; else
    [[ $programa == java ]] && erro "Nenhum Java padrão no PATH. Instale um JDK padrão pelo SDKMAN antes (ex.: sdk install java 21.0.11-tem)."
    erro "$programa não encontrado. Ubuntu/Debian: sudo apt install python3 curl unzip coreutils maven"
  fi
done
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' || erro "python3 precisa ser 3.10 ou mais novo."
export SDKMAN_DIR=${SDKMAN_DIR:-$HOME/.sdkman}
[[ -f $SDKMAN_DIR/bin/sdkman-init.sh ]] || erro "SDKMAN não encontrado. Instale: curl -s \"https://get.sdkman.io\" | bash  (depois abra um terminal novo)"
set +u
# shellcheck disable=SC1091
source "$SDKMAN_DIR/bin/sdkman-init.sh"
set -u
[[ -e $SDKMAN_DIR/candidates/java/current ]] || erro "O SDKMAN precisa de um Java padrão instalado (ex.: sdk install java 21.0.11-tem)."
ok "SDKMAN em $SDKMAN_DIR (Java padrão: $(readlink "$SDKMAN_DIR/candidates/java/current" | xargs basename))"

echo "== 3/6 JDKs Eclipse Temurin"
for jdk in 17.0.19-tem 21.0.11-tem 25.0.3-tem; do
  if [[ -d $SDKMAN_DIR/candidates/java/$jdk ]]; then
    ok "$jdk já instalado"
  else
    echo "  instalando $jdk (o Java padrão não é alterado)"
    set +u
    echo n | sdk install java "$jdk" || erro "Falha ao instalar $jdk. Se a versão saiu da lista do SDKMAN, baixe em https://adoptium.net/temurin/archive/ e use: sdk install java $jdk <pasta do JDK>"
    set -u
    ok "$jdk instalado"
  fi
done

echo "== 4/6 DaCapo 23.11-MR2-chopin"
zip_url=$(valor ferramentas/dacapo.json canonical_download_url)
zip_sha=$(valor ferramentas/dacapo.json archive_sha256)
jar=$(valor config/execucao.json dacapo path)
jar_sha=$(valor config/execucao.json dacapo sha256)
zip_local=ferramentas/dacapo-23.11-MR2-chopin.zip
if [[ -f $jar ]]; then
  ok "DaCapo já extraída em $jar"
else
  if [[ ! -f $zip_local ]]; then
    livre_gb=$(df -Pk ferramentas | awk 'NR==2 {print int($4/1024/1024)}')
    [[ $livre_gb -ge 23 ]] || erro "Espaço livre insuficiente: ${livre_gb} GB (precisa de ~23 GB)."
    echo "  baixando $zip_url (cerca de 6,3 GB; pode levar bastante tempo)"
    curl -fL --retry 3 -C - -o "$zip_local.parcial" "$zip_url"
    mv "$zip_local.parcial" "$zip_local"
  fi
  echo "  conferindo o SHA-256 do arquivo baixado"
  echo "$zip_sha  $zip_local" | sha256sum -c --quiet - || erro "SHA-256 do ZIP diferente do oficial. Apague $zip_local e baixe de novo."
  ok "SHA-256 do ZIP confere com o oficial"
  mkdir -p ferramentas/dacapo
  unzip -q -n "$zip_local" -d ferramentas/dacapo
  [[ -f $jar ]] || erro "Depois de extrair, $jar não apareceu. Confira o conteúdo de ferramentas/dacapo/."
  ok "DaCapo extraída em ferramentas/dacapo/ (o ZIP pode ser apagado depois)"
fi
echo "$jar_sha  $jar" | sha256sum -c --quiet - || erro "SHA-256 de $jar diferente do registrado em config/execucao.json."
ok "SHA-256 do JAR da DaCapo confere"

echo "== 5/6 Medidor (Maven)"
medidor=$(valor config/execucao.json meter path)
medidor_sha=$(valor config/execucao.json meter sha256)
if [[ -f $medidor ]] && echo "$medidor_sha  $medidor" | sha256sum -c --quiet - 2> /dev/null; then
  # Um medidor que já confere não é recompilado, para não trocar o JAR usado nas coletas.
  ok "Medidor já compilado e igual ao da coleta original; nada a fazer"
else
  mvn -q install:install-file -Dfile="$jar" -DgroupId=org.dacapo -DartifactId=dacapo \
      -Dversion=23.11-MR2-chopin -Dpackaging=jar
  ok "DaCapo instalada no repositório local do Maven"
  # O medidor original foi compilado com o Temurin 25.0.3. Com esse mesmo JDK, o JAR sai idêntico byte a byte,
  # porque o pom.xml fixa a data gravada nos arquivos (project.build.outputTimestamp).
  JAVA_HOME=$SDKMAN_DIR/candidates/java/25.0.3-tem mvn -q -f medidor-java/pom.xml clean package
  ok "Medidor compilado e testado com o Temurin 25.0.3"
fi

echo "== 6/6 Conferência final"
if echo "$medidor_sha  $medidor" | sha256sum -c --quiet - 2> /dev/null; then
  ok "SHA-256 do medidor igual ao da coleta original"
else
  aviso "SHA-256 do medidor diferente do registrado ($(sha256sum "$medidor" | cut -c1-16)…)."
  aviso "O código é o mesmo; a diferença vem do JDK ou do Maven usados na compilação. Para coletar, copie"
  aviso "config/execucao.json para config/replicacao.json, troque meter.sha256 pelo valor completo"
  aviso "(sha256sum $medidor), use --config config/replicacao.json e relate isso como desvio."
fi
python3 -m unittest discover -s scripts/tests > /dev/null 2>&1 && ok "Testes dos scripts de coleta" || erro "Testes dos scripts de coleta falharam: python3 -m unittest discover -s scripts/tests"
echo
echo "Ambiente pronto. Próximos passos (README, seção \"Repetir a coleta\"):"
echo "  bash scripts/executar.sh preparar --configuracao A --liberar-leitura"
echo "  bash scripts/executar.sh executar --configuracao D --aplicacao pmd"
