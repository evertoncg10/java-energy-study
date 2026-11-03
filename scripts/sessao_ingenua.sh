#!/usr/bin/env bash
# Sessão ingênua do critério E7 (T45), fora da amostra oficial.
#
# Repete a medição do jeito que muita gente faria sem um protocolo: ordem fixa (A, B, C, D, sem sorteio),
# sem núcleos fixos, sem pausas entre os processos e com a preparação mínima que o medidor aceita
# (1 iteração). Usa config/ingenua-e7.json. Os dados vão para dados/verificacao/ingenua-<data>/.
#
# Uso: bash scripts/sessao_ingenua.sh [repetições]   (padrão: 10)
set -uo pipefail

raiz=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$raiz" || exit 1
repeticoes=${1:-10}
config=config/ingenua-e7.json
aplicacoes=(lusearch pmd avrora)
configuracoes=(A B C D)
sessao="ingenua-$(date -u +%Y%m%dT%H%M%SZ)"
pasta="dados/verificacao/$sessao"

if [[ ! -f "$config" ]]; then
  echo "Configuração não encontrada: $config" >&2
  exit 1
fi
mkdir -p "$pasta"

# Plano gravado antes da execução: a ordem é fixa e fica registrada.
plano="$pasta/plano-antes-execucao.txt"
{
  echo "sessao=$sessao"
  echo "inicio_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "config=$config sha256=$(sha256sum "$config" | cut -d' ' -f1)"
  echo "repeticoes=$repeticoes"
  echo "commit=$(git rev-parse HEAD 2>/dev/null || echo desconhecido)"
} > "$plano"
ordem=0
for r in $(seq 1 "$repeticoes"); do
  for app in "${aplicacoes[@]}"; do
    for c in "${configuracoes[@]}"; do
      ordem=$((ordem + 1))
      printf 'r%02d-%03d-%s-%s\n' "$r" "$ordem" "$app" "$c" >> "$plano"
    done
  done
done
total=$ordem
echo "Plano gravado em $plano ($total processos)."

progresso="$pasta/progresso.txt"
inicio=$(date +%s)
ordem=0
falhas=0
for r in $(seq 1 "$repeticoes"); do
  for app in "${aplicacoes[@]}"; do
    for c in "${configuracoes[@]}"; do
      ordem=$((ordem + 1))
      nome=$(printf 'r%02d-%03d-%s-%s' "$r" "$ordem" "$app" "$c")
      t0=$(date +%s)
      if bash scripts/executar.sh executar --configuracao "$c" --aplicacao "$app" --config "$config" \
          --sessao "$sessao" --bloco "r$r" --ordem "$ordem" --saida "$pasta/$nome" > "$pasta/$nome.saida.log" 2>&1; then
        estado=ok
      else
        estado=FALHA
        falhas=$((falhas + 1))
      fi
      t1=$(date +%s)
      echo "$nome $estado $((t1 - t0))s" | tee -a "$progresso"
      echo "[$ordem/$total] $nome $estado ($((t1 - t0)) s)"
    done
  done
done
fim=$(date +%s)
{
  echo "fim_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "duracao_minutos=$(( (fim - inicio) / 60 ))"
  echo "falhas=$falhas"
} >> "$plano"
echo "SESSAO=$pasta"
echo "Duração: $(( (fim - inicio) / 60 )) min. Falhas: $falhas de $total."
