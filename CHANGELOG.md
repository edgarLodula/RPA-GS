# CHANGELOG — GS 2026 Melhorias

## 2026-06-05

- **[Fase 1] Higiene do entregável** — `.gitignore` ampliado para cobrir `data/neo_*.json` e `data/images/` (arquivos gerados em runtime que não devem entrar no ZIP de entrega). Removida a pasta vazia `data/arquivo_bruto/` (não utilizada pelo código). Criado `scripts/build_entrega.py`: script Python puro (`zipfile`, `pathlib`, `fnmatch`) que gera `gs_entrega_AAAA-MM-DD.zip` excluindo todos os artefatos listados no `.gitignore` mais extras de runtime. README atualizado com seção "Como gerar o ZIP de entrega".

- **[Fase 2] Exportação XLSX multi-aba** — `src/analizer.py` passa a gerar `data/reports/relatorio_YYYY-MM-DD.xlsx` com três abas (**Asteroides**, **Top 5 Risco**, **Métricas**) ao final de cada execução do pipeline. Cabeçalhos em negrito, freeze pane na primeira linha, colunas com nomes em pt-BR. Usa `pandas` + `openpyxl`. Falha na geração do XLSX loga warning e não aborta o pipeline — o JSON continua sendo o artefato canônico. Adicionado endpoint `GET /relatorio.xlsx` no FastAPI (`FileResponse`, 404 se inexistente). Link "Baixar XLSX" adicionado no `frontend/index.html`. Novo arquivo `tests/test_xlsx.py` com 2 testes (existência do arquivo + 3 abas + cabeçalho em negrito).

- **[Fase 3] Detecção de anomalias com IsolationForest** — A detecção estatística (média + 1σ) foi mantida como `_detectar_anomalias_legado()` e é usada como fallback quando há < 10 amostras. A nova `detectar_anomalias()` usa `IsolationForest(contamination=0.15, random_state=42, n_estimators=100)` com 4 features normalizadas por `StandardScaler`. Adiciona campo `anomaly_score` (saída de `decision_function`) em cada asteroide. `database.py` recebeu coluna `anomaly_score REAL` no schema e função `atualizar_anomaly_score()`; `_migrar_anomaly_score()` garante compatibilidade com bancos legados via tratamento de `OperationalError`. `api/models.py` recebeu campo opcional `anomaly_score: float | None = None`. Dois novos testes em `test_analizer.py` (fallback + detecção de outliers sintéticos). README atualizado com explicação do modelo e nova linha na tabela de tópicos.

- **[Fase 4] Visão computacional com NASA APOD** — Criado `src/vision.py`: coleta metadados e imagem da APOD (`coletar_apod()`), analisa com Pillow (`analisar_imagem()` — dimensões, brilho médio, cor dominante) e persiste em CSV diário (`apod_analytics.csv`). `src/pipeline.py` integra `coletar_e_analisar()` ao final do pipeline (falha = warning, nunca erro). `api/main.py` recebeu dois novos endpoints: `GET /apod` (JSON estruturado via schema `APODAnalise`) e `GET /apod/imagem` (serve a imagem localmente via `FileResponse`). README atualizado com novos endpoints e artefatos.

## 2026-06-05 (Correções pós-análise técnica)

- **[C-01] Credencial fora do controle de versão** — Criado `.dockerignore` excluindo `.env`, artefatos de runtime (`data/`, `logs/`, `__pycache__/`) e arquivos de entrega (`gs_entrega_*.zip`, `ANALISE_TECNICA.md`). A pasta `tests/` foi mantida na imagem intencionalmente para permitir `docker compose exec api pytest tests/ -v`. **Ação manual obrigatória**: o usuário deve revogar a chave `NASA_API_KEY` atual em `https://api.nasa.gov/` e gerar uma nova.

- **[I-01/I-02] Higiene de controle de versão** — `.gitignore` ampliado com `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.claude/`, `gs_entrega_*.zip`, `ANALISE_TECNICA.md`, `data/reports/*.xlsx` e `data/reports/*.csv`.

- **[I-02] restart policy Docker** — `docker-compose.yml` recebeu `restart: unless-stopped` em ambos os serviços (`api` e `robo`), garantindo recuperação automática após reinício do host.

- **[I-03] Cobertura de testes** — Três novos arquivos de testes cobrindo camadas previamente sem cobertura: `tests/test_database.py` (5 testes: criação idempotente de tabela, parse sem close_approach, insert+list, upsert preserva score, remoção de antigos), `tests/test_collector.py` (3 testes: sucesso, retry em falha temporária, erro após todas as tentativas), `tests/test_api.py` (5 testes: /saude, /asteroides 404, /perigosos filtro, /relatorio.xlsx com arquivo, /relatorio.xlsx 404). Adicionado `httpx>=0.27,<1` a `requirements.txt` (requerido pelo `TestClient` do FastAPI). Total: 20 testes, todos passando.

- **[I-04] Caminho absoluto no CSV do APOD** — `src/vision.py` agora persiste `caminho_imagem` como path relativo a `config.BASE_DIR` (via `Path.relative_to()`), com fallback para o valor original se já for relativo. Elimina caminhos `/app/data/...` específicos do Docker que quebravam portabilidade.

- **[M-01] functools.wraps no decorator** — `src/monitor.py` adicionou `import functools` e `@functools.wraps(funcao)` ao decorator `medir`, preservando `__name__`, `__doc__` e `__wrapped__` da função decorada.

- **[M-03] import csv no topo do módulo** — `api/main.py`: `import csv` movido para o bloco de imports do topo; import inline removido do corpo de `get_apod()`.

- **[M-04] Scheduler robusto na inicialização** — `src/scheduler.py`: primeira chamada a `executar_pipeline()` envolta em `try/except Exception`, garantindo que o schedule de 6 horas seja registrado mesmo quando a API NASA está indisponível no boot.

## 2026-05-28

- **Item 1** — Criado `README.md` com diagrama ASCII da arquitetura, tabela de tópicos do semestre, instruções de execução (local e Docker), estrutura de pastas comentada e tabela de endpoints.
- **Item 2** — Criados `.gitignore` (protege `.env`, `.venv/`, `data/`, `logs/`, `__pycache__`) e `.env.example` (template com link para obter a chave da NASA).
- **Item 3** — `src/monitor.py`: `psutil.disk_usage("/")` substituído por `psutil.disk_usage(str(BASE_DIR))`, tornando o monitoramento de disco portátil no Windows.
- **Item 4** — Cada módulo `src/*.py` agora usa `logging.getLogger(__name__)` local; `logger` global removido de `config.py`, que agora só contém constantes e paths.
- **Item 5** — Criado `frontend/index.html` com tabela de asteroides, cards de métricas, saúde do sistema e botão de atualização (HTML + CSS + JS puro). Adicionado `CORSMiddleware` em `api/main.py` para permitir que o frontend consuma a API.
- **Item 6** — `src/database.py`: context manager `conectar()` agora relança a exceção após logar, evitando que erros de banco sejam engolidos silenciosamente.
- **Item 7** — `src/collector.py`: adicionado backoff progressivo (`time.sleep(2 * tentativa)`) entre tentativas de coleta, exceto na última.
- **Item 8** — `src/database.py`: `parse_feed()` agora ignora asteroides sem `close_approach_data` com `continue`, logando quantos foram pulados.
- **Item 9** — `src/analizer.py`: divisor de velocidade ajustado de `10_000` para `150_000`, distribuindo melhor o fator entre 0 e 1 para velocidades típicas dos dados da NASA.
- **Item 10** — `requirements.txt` migrado de versões pinadas (geradas por `pip freeze`) para ranges compatíveis (`>=x.y,<z`), garantindo instalação reproduzível em qualquer ambiente.
- **Item 11** — Confirmado: `.gitignore` criado no Item 2 já cobre `__pycache__/` e `*.pyc`. Nenhuma ação adicional necessária.
- **Item 12** — `src/pipeline.py`: `database.remover_antigos()` agora é chamado ao final do pipeline, removendo registros com mais de 60 dias e completando o ciclo CRUD.
- **Item 13** — `api/main.py`: adicionado endpoint `GET /relatorio` que lê e devolve o relatório JSON mais recente de `data/reports/`.
- **Item 14** — Criada pasta `tests/` com `test_analizer.py` cobrindo três casos: score dentro do intervalo 0–100, bônus de perigo eleva o score, e desvio zero não gera anomalias.
