#!/usr/bin/env bash
# Refaz a análise oficial do PAE-JVM a partir dos dados do repositório e compara com os
# resultados publicados em resultados/oficial-20261101-termos.
#
# Uso (na pasta raiz do projeto; Linux, macOS ou Git Bash no Windows):
#     bash scripts/reproduzir_analise.sh                 # números (CSV, JSON e texto)
#     bash scripts/reproduzir_analise.sh --com-figuras   # também gera as figuras
#
# O que faz:
#   1. procura um Python 3.10 ou mais novo;
#   2. cria o ambiente virtual analise/.venv (só na primeira vez) e o ativa;
#   3. instala as versões travadas de analise/requisitos-travados.txt;
#   4. roda os testes automáticos do pacote de análise;
#   5. roda a análise numa pasta nova resultados/reproducao-AAAAMMDD-HHMMSS;
#   6. compara com os resultados oficiais. Resultado esperado: "Arquivos diferentes: 0";
#   7. refaz o cálculo do peso das pausas de coleta e compara com resultados/pausas-gc-20261107.
# Saída do script: 0 quando os números são idênticos; 1 quando há diferença; 2 em erro de ambiente.
set -euo pipefail

com_figuras=0
case "${1:-}" in
  "") ;;
  --com-figuras) com_figuras=1 ;;
  *) echo "Opção desconhecida: $1 (use --com-figuras ou nada)" >&2; exit 2 ;;
esac

raiz=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$raiz"
export PYTHONUTF8=1

echo "== 1/7 Procurando Python 3.10 ou mais novo"
python_base=""
for candidato in python3 python py; do
  if command -v "$candidato" > /dev/null 2>&1 \
     && "$candidato" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' > /dev/null 2>&1; then
    python_base=$candidato
    break
  fi
done
if [[ -z "$python_base" ]]; then
  echo "Python 3.10 ou mais novo não encontrado. Instale em https://www.python.org/downloads/" >&2
  exit 2
fi
"$python_base" --version

echo "== 2/7 Ambiente virtual analise/.venv"
if [[ ! -d analise/.venv ]]; then
  "$python_base" -m venv analise/.venv
fi
if [[ -f analise/.venv/Scripts/activate ]]; then
  # shellcheck disable=SC1091
  source analise/.venv/Scripts/activate   # Windows (Git Bash)
else
  # shellcheck disable=SC1091
  source analise/.venv/bin/activate       # Linux e macOS
fi
python --version

echo "== 3/7 Instalando as versões travadas"
(cd analise && python -m pip install --quiet -r requisitos-travados.txt -e ".[dev,figuras]")

echo "== 4/7 Testes automáticos"
(cd analise && python -m pytest -q)

saida="resultados/reproducao-$(date +%Y%m%d-%H%M%S)"
echo "== 5/7 Análise em $saida"
if [[ $com_figuras -eq 1 ]]; then
  pae-analise analisar --saida "$saida" > /dev/null
else
  pae-analise analisar --saida "$saida" --sem-figuras > /dev/null
fi
echo "Resumo legível: $saida/resumo.txt"

echo "== 6/7 Comparação com resultados/oficial-20261101-termos"
python scripts/comparar_resultados.py resultados/oficial-20261101-termos "$saida" --ignorar-figuras

echo "== 7/7 Peso das pausas de coleta, comparado com resultados/pausas-gc-20261107"
python scripts/analisar_pausas.py --saida "$saida/pausas" > /dev/null
python scripts/comparar_resultados.py resultados/pausas-gc-20261107 "$saida/pausas"
