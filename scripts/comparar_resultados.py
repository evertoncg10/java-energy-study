#!/usr/bin/env python3
"""Compara duas pastas de resultados da análise, arquivo por arquivo.

Uso (na raiz do repositório):
    python scripts/comparar_resultados.py resultados/PASTA_A resultados/PASTA_B

Para cada arquivo, informa se é idêntico byte a byte. Dois casos têm regra própria:
- metadados.json registra data, plataforma e commit da execução, então sempre muda;
  o script compara só o campo input_sha256 (identidade dos dados de entrada).
- Os PDFs das figuras guardam a data de criação; o script compara o PDF sem esse campo.
Nos arquivos de texto diferentes, mostra as linhas que mudaram.
"""

from __future__ import annotations

import difflib
import json
import re
import sys
from pathlib import Path

PDF_DATE = re.compile(rb"/CreationDate \(D:[^)]*\)")
TEXT_SUFFIXES = {".csv", ".txt", ".json"}


def _files(folder: Path) -> set[str]:
    return {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}


def _same_pdf(a: bytes, b: bytes) -> bool:
    return PDF_DATE.sub(b"", a) == PDF_DATE.sub(b"", b)


def compare(first: Path, second: Path) -> int:
    names_a, names_b = _files(first), _files(second)
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
            print(f"metadados (data, plataforma e commit mudam); mesmos dados de entrada: {'sim' if same_input else 'NÃO'}")
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
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    compare(Path(sys.argv[1]), Path(sys.argv[2]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
