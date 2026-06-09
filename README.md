# GS 2026 — Monitoramento de Missões Espaciais com RPA

## Integrantes

| RM | Nome |
|----|------|
| 552574 | Bruno Fernandes Nascimento |
| 565260 | Edgar Lódula de Assis |
| 566325 | Júlia Aben-Athar |

---

Pipeline RPA autônomo que coleta dados de asteroides próximos à Terra via API NeoWs da NASA, armazena em SQLite, calcula um score de risco multifatorial, detecta anomalias com **IsolationForest (ML)**, exporta relatórios em JSON e XLSX, e expõe tudo via API REST com FastAPI. O robô executa automaticamente a cada 6 horas e é empacotado com Docker para facilitar a implantação.

---

## Arquitetura do Fluxo

```
┌─────────────────┐
│  NASA API NeoWs │
└────────┬────────┘
         │ HTTP GET (start_date, end_date, api_key)
         ▼
┌─────────────────┐      data/neo_YYYY-MM-DD.json
│  collector.py   │ ──► (arquivo bruto — artefato 1)
│  retry + backoff│
└────────┬────────┘
         │ JSON parseado
         ▼
┌─────────────────┐
│  database.py    │ ──► asteroides.db  (SQLite — artefato 2)
│  SQLite CRUD    │
└────────┬────────┘
         │ registros lidos
         ▼
┌─────────────────┐      data/reports/relatorio_YYYY-MM-DD.json
│  analizer.py   │ ──► (relatório consolidado — artefato 3)
│  score + desvio │
└────────┬────────┘
         │ dados enriquecidos
         ▼
┌─────────────────┐      data/reports/relatorio_YYYY-MM-DD.xlsx
│  analizer.py   │ ──► (planilha multi-aba — artefato 4)
│  IsolationForest│
└────────┬────────┘
         │ resultados
         ▼
┌─────────────────┐      data/images/  +  data/reports/apod_analytics.csv
│  vision.py      │ ──► (APOD — artefato 5)
│  Pillow         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FastAPI        │ ──► /asteroides  /perigosos  /relatorio  /relatorio.xlsx  /saude  /apod
└────────┬────────┘
         │ JSON
         ▼
┌─────────────────┐
│  frontend/      │  (interface web estática)
│  index.html     │
└─────────────────┘
```

O agendador (`scheduler.py`) executa `pipeline.py` na inicialização e repete a cada **6 horas** usando a biblioteca `schedule`.

---

## Tópicos do Semestre Integrados

| Tópico | Onde aparece |
|--------|-------------|
| **API REST (consumo)** | `collector.py` — requests com retry e backoff |
| **Leitura/Escrita de Arquivos** | JSON bruto da NASA + relatórios diários em `data/` |
| **SQLite + CRUD completo** | `database.py` — CREATE, INSERT (upsert), SELECT, UPDATE, DELETE |
| **FastAPI + Pydantic** | `api/main.py` + `api/models.py` — endpoints com validação de tipos |
| **Tasks & psutil** | `monitor.py` — decorator `@medir` + endpoint `/saude` |
| **Agendamento** | `scheduler.py` — schedule a cada 6 horas |
| **Docker** | `Dockerfile` + `docker-compose.yml` — dois serviços independentes |
| **Machine Learning (sklearn)** | `analizer.py` — IsolationForest para detecção de anomalias multidimensional |
| **DataFrames / Planilhas** | `analizer.py` — pandas + openpyxl geram XLSX com 3 abas a cada execução |
| **Visão Computacional** | `vision.py` — Pillow analisa brilho, cor dominante e dimensões da APOD |

---

## Como Rodar

### Pré-requisitos

- Python 3.12+
- Docker Desktop (para a opção Docker)
- Chave de API gratuita da NASA: https://api.nasa.gov/

### 1. Configurar o ambiente

```bash
# Copiar o template de variáveis de ambiente
cp .env.example .env

# Editar .env e inserir sua chave
# NASA_API_KEY=sua_chave_aqui
```

### Opção A — Local (sem Docker)

```bash
# Criar e ativar ambiente virtual
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/Mac

# Instalar dependências
pip install -r requirements.txt

# Rodar o pipeline (coleta + análise)
python -m src.pipeline

# Em outro terminal, subir a API
uvicorn api.main:app --reload --port 8000
```

Abra `frontend/index.html` no navegador para ver a interface.
Acesse http://localhost:8000/docs para a documentação interativa.

### Opção B — Docker (recomendado)

```bash
docker compose up --build
```

Aguarde o build. A API estará em http://localhost:8000 e o robô coleta automaticamente ao iniciar.

Para encerrar: `Ctrl+C` seguido de `docker compose down`.

### Como rodar os testes

```bash
pip install pytest
pytest tests/ -v
```

### Como gerar o ZIP de entrega

```bash
python scripts/build_entrega.py
```

O script lê o `.gitignore` e aplica exclusões adicionais (`__pycache__`, `.venv`, `*.db`, logs, JSONs brutos da NASA, imagens APOD). Gera `gs_entrega_AAAA-MM-DD.zip` na raiz do projeto e imprime o que foi incluído e o que foi pulado.

---

## Estrutura de Pastas

```
gs/
├── api/
│   ├── main.py          # Endpoints FastAPI + CORSMiddleware
│   └── models.py        # Schemas Pydantic (Asteroide, StatusSaude)
├── src/
│   ├── config.py        # Constantes e paths centralizados (carrega .env)
│   ├── collector.py     # Coleta NASA com retry + backoff
│   ├── database.py      # SQLite: criação da tabela, CRUD, parse do JSON
│   ├── analizer.py     # Score de risco multifatorial, IsolationForest e exportação XLSX
│   ├── vision.py        # Coleta e análise de imagens APOD (Pillow)
│   ├── monitor.py       # Decorator @medir e snapshot de recursos do sistema
│   ├── pipeline.py      # Orquestra: coleta → armazena → analisa → limpa
│   └── scheduler.py     # Agendamento a cada 6 horas
├── frontend/
│   ├── index.html       # Interface web estática (HTML + CSS + JS puro)
│   ├── css/
│   │   └── style.css    # Estilos da interface
│   └── js/
│       └── app.js       # Lógica de consumo da API
├── scripts/
│   └── build_entrega.py # Gera ZIP limpo de entrega (sem .env, __pycache__, DBs, logs)
├── tests/
│   ├── test_analizer.py  # Testes do módulo de análise + IsolationForest
│   ├── test_api.py       # Testes dos endpoints FastAPI
│   ├── test_collector.py # Testes da coleta com retry/backoff
│   ├── test_database.py  # Testes do CRUD SQLite
│   └── test_xlsx.py      # Testes de geração do relatório XLSX
├── data/                # Criado automaticamente na primeira execução
│   ├── asteroides.db    # Banco SQLite principal
│   ├── neo_*.json       # JSONs brutos da NASA (um por dia)
│   └── reports/         # Relatórios consolidados diários
├── logs/                # Criado automaticamente
│   └── robo.log         # Log completo de execução do robô
├── .env                 # Chave da NASA (NÃO versionar)
├── .env.example         # Template do .env
├── .gitignore
├── docker-compose.yml   # Serviços: api + robo
├── Dockerfile
├── requirements.txt
└── CHANGELOG.md
```

---

## Endpoints da API

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/` | Redireciona para `/ui/` |
| GET | `/asteroides` | Todos os asteroides do banco, ordenados por distância |
| GET | `/perigosos?score_minimo=50` | Asteroides acima do score mínimo de risco |
| GET | `/relatorio` | Último relatório consolidado (total, perigosos, anomalias) |
| GET | `/relatorio.xlsx` | Download do relatório XLSX mais recente (3 abas) |
| GET | `/saude` | CPU, memória e disco do servidor em tempo real |
| GET | `/apod` | Análise da Astronomy Picture of the Day mais recente |
| GET | `/apod/imagem` | Download da imagem APOD mais recente |
| GET | `/docs` | Documentação interativa Swagger UI |

---

## Artefatos Gerados

| Artefato | Localização | Conteúdo |
|----------|------------|----------|
| JSON bruto | `data/neo_YYYY-MM-DD.json` | Resposta completa da NASA |
| Banco de dados | `data/asteroides.db` | Tabela `asteroides` com todos os campos (inclui `anomaly_score`) |
| Relatório JSON | `data/reports/relatorio_YYYY-MM-DD.json` | Métricas consolidadas + top 5 de risco + lista de anomalias |
| Relatório XLSX | `data/reports/relatorio_YYYY-MM-DD.xlsx` | 3 abas: Asteroides · Top 5 Risco · Métricas |
| Imagem APOD | `data/images/apod_YYYY-MM-DD.jpg` | Astronomy Picture of the Day baixada da NASA |
| Análise APOD CSV | `data/reports/apod_analytics.csv` | Histórico diário: brilho, cor dominante, dimensões |
| Log de execução | `logs/robo.log` | Timestamps, erros e métricas de performance |

---

## Como funciona o score de risco e a detecção de anomalias

O **score de risco** (0–100) combina três fatores ponderados:
- Tamanho (40%): `min(diametro_max_m / 1000, 1.0)`
- Proximidade (40%): `1 - min(distancia_km / 7 500 000, 1.0)`
- Velocidade (20%): `min(velocidade_kmh / 150 000, 1.0)`
- Bônus de +15 para asteroides marcados como `potentially_hazardous` pela NASA.

A **detecção de anomalias** usa **IsolationForest** (scikit-learn) com 4 features simultâneas (`diametro_max_m`, `velocidade_kmh`, `distancia_km`, `score_risco`), normalizado com `StandardScaler`. O modelo é treinado a cada execução e classifica ~15% dos asteroides como anômalos (`contamination=0.15`). Para sessões com menos de 10 asteroides (ex: testes), faz fallback para o método estatístico clássico (média + 1σ).
