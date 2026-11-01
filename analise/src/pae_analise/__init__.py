"""Análise dos dados do protocolo PAE-JVM.

Módulos:
    gclog        leitura do log de coleta de lixo (G1);
    consolidacao uma linha por processo a partir dos dados brutos (T19);
    estatistica  medianas, razões pareadas por bloco com bootstrap, Mann–Whitney, Holm e A12;
    avaliacao    critérios E1–E6 e hipóteses H1–H5 do registro prévio;
    relatorio    gravação das tabelas e do resumo;
    figuras      gráficos (opcional, requer matplotlib);
    cli          linha de comando ``pae-analise``.
"""

__version__ = "0.1.0"
