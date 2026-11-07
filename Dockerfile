# Ambiente fixo para refazer a análise do PAE-JVM a partir dos dados do repositório.
# Não faz a coleta (que precisa de hardware Intel com RAPL e de Linux sem contêiner).
#
# Construir (na pasta raiz do projeto):
#     docker build -t pae-jvm-analise .
# Refazer a análise e o cálculo do peso das pausas e comparar com os resultados publicados (sem figuras):
#     docker run --rm pae-jvm-analise
# Gerar tudo, com figuras, numa pasta do computador:
#     docker run --rm -v "$(pwd)/resultados:/saida" pae-jvm-analise pae-analise analisar --saida /saida/reproducao-docker
FROM python:3.12.8-slim-bookworm

ENV PYTHONUTF8=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /pae-jvm
COPY analise/ analise/
RUN python -m pip install -r analise/requisitos-travados.txt -e "analise[dev,figuras]"

COPY config/ config/
COPY dados/ dados/
COPY evidencias/ evidencias/
COPY resultados/ resultados/
COPY scripts/comparar_resultados.py scripts/analisar_pausas.py scripts/

CMD ["sh", "-c", "pae-analise analisar --saida /tmp/reproducao --sem-figuras > /dev/null && python scripts/comparar_resultados.py resultados/oficial-20261101-termos /tmp/reproducao --ignorar-figuras && python scripts/analisar_pausas.py --saida /tmp/pausas > /dev/null && python scripts/comparar_resultados.py resultados/pausas-gc-20261107 /tmp/pausas"]
