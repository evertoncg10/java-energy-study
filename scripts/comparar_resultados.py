#!/usr/bin/env python3
"""Compara duas pastas de resultados da análise, arquivo por arquivo.

Uso (na raiz do repositório):
    python scripts/comparar_resultados.py resultados/PASTA_A resultados/PASTA_B
    python scripts/comparar_resultados.py resultados/PASTA_A resultados/PASTA_B --ignorar-figuras

Para cada arquivo, informa se é idêntico byte a byte. Dois casos têm regra própria:
- metadados.json registra data, plataforma e commit da execução, então sempre muda;
  o script compara só o campo input_sha256 (identidade dos dados de entrada).
- Os PDFs das figuras guardam a data de criação; o script compara o PDF sem esse campo.
Nos arquivos de texto diferentes, mostra as linhas que mudaram.

Com --ignorar-figuras, a pasta figuras/ fica fora da comparação. Use essa opção quando uma das
pastas foi gerada com --sem-figuras ou em outro sistema operacional: as imagens só saem idênticas
byte a byte no mesmo sistema, enquanto os números (CSV, JSON e texto) saem idênticos em qualquer um.
A saída do script é 0 quando não há diferença e 1 quando há.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

PDF_DATE = re.compile(rb"/CreationDate \(D:[^)]*\)")
TEXT_SUFFIXES = {".csv", ".txt", ".json"}


def _files(folder: Path, ignore_figures: bool) -> set[str]:
    names = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}
    return {n for n in names if not n.startswith("figuras/")} if ignore_figures else names


def _same_pdf(a: bytes, b: bytes) -> bool:
    return PDF_DATE.sub(b"", a) == PDF_DATE.sub(b"", b)


def compare(first: Path, second: Path, ignore_figures: bool = False) -> int:
    names_a, names_b = _files(first, ignore_figures), _files(second, ignore_figures)
    different = 0
    for name in sorted(names_a - names_b):
        print(f"SÓ EM {first}: {name}")
        different += 1
    for name in sorted(names_b - names_a):
        print(f"SÓ EM {second}: {name}")
        different += 1
    for name in sorted(names_a & names_b):
        a, b = (first / name).read_bytes(), (second / name).read_bytes()
        if a == b:
            print(f"idêntico: {name}")
        elif name == "metadados.json":
            same_input = json.loads(a)["input_sha256"] == json.loads(b)["input_sha256"]
            answer = "sim" if same_input else "NÃO"
            print(f"metadados (data, plataforma e commit mudam); mesmos dados de entrada: {answer}")
            different += 0 if same_input else 1
        elif name.endswith(".pdf") and _same_pdf(a, b):
            print(f"idêntico, exceto a data de criação do PDF: {name}")
        else:
            print(f"DIFERENTE: {name}")
            different += 1
            if Path(name).suffix in TEXT_SUFFIXES:
                lines = difflib.unified_diff(
                    a.decode("utf-8").splitlines(),
                    b.decode("utf-8").splitlines(),
                    fromfile=f"{first.name}/{name}",
                    tofile=f"{second.name}/{name}",
                    lineterm="",
                    n=0,
                )
                for line in lines:
                    print(f"    {line}")
    print(f"\nArquivos diferentes: {different}")
    return different


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("primeira", type=Path, help="Pasta de resultados de referência.")
    parser.add_argument("segunda", type=Path, help="Pasta de resultados a comparar.")
    parser.add_argument("--ignorar-figuras", action="store_true", help="Não compara a pasta figuras/.")
    args = parser.parse_args()
    for folder in (args.primeira, args.segunda):
        if not folder.is_dir():
            parser.error(f"pasta não encontrada: {folder}")
    return 1 if compare(args.primeira, args.segunda, args.ignorar_figuras) else 0


if __name__ == "__main__":
    sys.exit(main())
