#!/usr/bin/env bash
# Called by executar.py. Selection affects only this child shell.
set -e
sdk_dir=$1
jdk_id=$2
selection_file=$3
export SDKMAN_DIR="$sdk_dir"
if [[ ! -f "$SDKMAN_DIR/bin/sdkman-init.sh" ]]; then
  echo 'SDKMAN não encontrado.' >&2
  exit 2
fi
# sdk use may create a default if current is absent. Require an existing default.
if [[ ! -e "$SDKMAN_DIR/candidates/java/current" ]]; then
  echo 'SDKMAN precisa ter um Java padrão instalado; nada será instalado ou alterado aqui.' >&2
  exit 2
fi
# SDKMAN does not support nounset. Do not modify its files or global settings.
source "$SDKMAN_DIR/bin/sdkman-init.sh"
if ! sdkman_healthcheck_enable=false sdk use java "$jdk_id"; then
  echo 'Falha em sdk use; não haverá execução por outro Java.' >&2
  exit 2
fi
hash -r
sdkman_healthcheck_enable=false sdk version
selected_java=$(command -v java)
printf 'Java resolvido após sdk use: %s\n' "$selected_java"
python3 - "$jdk_id" "$SDKMAN_CANDIDATES_DIR/java/$jdk_id" "$selected_java" "$JAVA_HOME" "$selection_file" <<'PY'
import json, pathlib, sys
from datetime import datetime, timezone
jdk, expected, command, home, output = sys.argv[1:]
expected = pathlib.Path(expected).resolve(strict=True)
actual = pathlib.Path(command).resolve(strict=True)
home = pathlib.Path(home).resolve(strict=True)
if home != expected or actual != (expected/'bin/java').resolve(strict=True):
    raise SystemExit('JAVA_HOME ou Java do PATH diverge do JDK selecionado pelo SDKMAN.')
with open(output, 'x') as stream:
    json.dump({'selected_at_utc':datetime.now(timezone.utc).isoformat(), 'sdkman_id':jdk,
               'expected_java_home':str(expected), 'java_home':str(home),
               'java_executable':str(actual), 'method':'sdk use java'}, stream, indent=2)
    stream.write('\n')
PY
