#!/usr/bin/env bash
# Confere a integridade dos dados do repositório contra os manifestos SHA-256 gravados ao fim de
# cada sessão, e refaz a conferência da coleta (qualidade de cada sessão e critério E2).
# Só lê arquivos; não altera nada.
#
# Uso (na pasta raiz do projeto; Linux, macOS ou Git Bash no Windows):
#     bash scripts/conferir_dados.sh
#
# As pastas "scratch" da DaCapo não estão no Git (estão nos pacotes completos das sessões);
# por isso a conferência usa --sem-scratch. Resultado esperado: CONFERE em todas as linhas.
set -euo pipefail
raiz=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$raiz"
export PYTHONUTF8=1

python_cmd=""
for candidato in python3 python py; do
  if command -v "$candidato" > /dev/null 2>&1 \
     && "$candidato" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' > /dev/null 2>&1; then
    python_cmd=$candidato
    break
  fi
done
[[ -n "$python_cmd" ]] || { echo "Python 3.10 ou mais novo não encontrado." >&2; exit 2; }

falhas=0
conferir() {  # pasta manifesto
  printf '%-58s ' "$1"
  if "$python_cmd" scripts/manifesto.py conferir --sessao "$1" --manifesto "$2" --sem-scratch | tail -n 1; then
    :
  else
    falhas=$((falhas + 1))
  fi
}

echo "== Sessões oficiais"
conferir dados/brutos/20261022T215204Z evidencias/manifestos/sessao1.json
conferir dados/brutos/20261022T215207Z evidencias/manifestos/sessao2.json
conferir dados/brutos/20261022T215211Z evidencias/manifestos/sessao3.json
conferir dados/brutos/20261022T215214Z evidencias/manifestos/sessao4.json

echo "== Pilotos (fora da amostra oficial)"
conferir dados/piloto/20261020T181145Z evidencias/manifestos/piloto-20261020T181145Z.json
conferir dados/piloto/20261020T181929Z evidencias/manifestos/piloto-20261020T181929Z.json
conferir dados/piloto/complemento-20261020T185137Z evidencias/manifestos/piloto-complemento-20261020T185137Z.json
conferir dados/piloto/20261022T170707Z evidencias/manifestos/piloto-20261022T170707Z.json

echo "== Conferência da coleta completa (qualidade das sessões e E2)"
"$python_cmd" scripts/conferir_coleta.py \
  --sessao dados/brutos/20261022T215204Z --manifesto evidencias/manifestos/sessao1.json \
  --sessao dados/brutos/20261022T215207Z --manifesto evidencias/manifestos/sessao2.json \
  --sessao dados/brutos/20261022T215211Z --manifesto evidencias/manifestos/sessao3.json \
  --sessao dados/brutos/20261022T215214Z --manifesto evidencias/manifestos/sessao4.json || falhas=$((falhas + 1))

if [[ $falhas -eq 0 ]]; then
  echo "RESULTADO: todos os dados conferem com os manifestos."
else
  echo "RESULTADO: $falhas conferência(s) com diferença. Veja as linhas acima." >&2
  exit 1
fi
