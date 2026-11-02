#!/usr/bin/env bash
# Grava os 4 planos de sessão com o mesmo desenho da coleta original: 15 blocos divididos em
# 4 + 4 + 4 + 3, códigos de sorteio 20261101 a 20261104. Cada plano fixa a ordem dos processos
# antes da execução e registra o SHA-256 da configuração usada.
#
# Uso (na pasta raiz do projeto):
#     bash scripts/planejar_sessoes_oficiais.sh [PASTA_DOS_PLANOS] [ARQUIVO_DE_CONFIGURACAO]
# Padrões: PASTA_DOS_PLANOS = ../planos-pae-jvm (fora do repositório)
#          ARQUIVO_DE_CONFIGURACAO = config/execucao.json
# Depois, uma sessão por vez (em dias ou horários diferentes):
#     python3 scripts/sessao.py executar --plano ../planos-pae-jvm/plano-sessao1.json
set -euo pipefail
raiz=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$raiz"
planos=${1:-../planos-pae-jvm}
config=${2:-config/execucao.json}
mkdir -p "$planos"

#        sessão blocos primeiro_bloco código_de_sorteio
for linha in "1 4 1 20261101" "2 4 5 20261102" "3 4 9 20261103" "4 3 13 20261104"; do
  read -r sessao blocos primeiro codigo <<< "$linha"
  arquivo="$planos/plano-sessao$sessao.json"
  if [[ -e $arquivo ]]; then
    echo "Já existe e não será sobrescrito: $arquivo" >&2
    exit 1
  fi
  python3 scripts/sessao.py planejar --config "$config" --categoria oficial \
    --blocos "$blocos" --primeiro-bloco "$primeiro" --semente "$codigo" --plano "$arquivo"
  sleep 2   # A pasta de saída de cada sessão leva a hora do plano (resolução de 1 s).
done
echo "Planos gravados em $planos. Execute uma sessão por vez com scripts/sessao.py executar."
