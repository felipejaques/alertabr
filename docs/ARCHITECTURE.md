# Arquitetura - AlertaBR

## Plataforma de Prevenção a Desastres Naturais

---

## 1. Visão Geral da Arquitetura

O AlertaBR segue uma arquitetura de **três camadas** (frontend, backend, dados) com comunicação via REST API. O sistema é monorepo com deploy containerizado via Docker Compose.

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENTE (Browser)                         │
├─────────────────────────────────────────────────────────────────┤
│  Next.js 14 (CSR)                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │Dashboard │  │  Mapas   │  │ Alertas  │  │  Relatórios  │   │
│  │  (CSR)   │  │(Leaflet) │  │  (CSR)   │  │  (Recharts)  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP/REST (JSON)
┌───────────────────────────▼─────────────────────────────────────┐
│                     BACKEND (FastAPI)                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ REST API │  │ Ingestão │  │  Motor   │  │  Alertas     │   │
│  │ (Routes) │  │(Services)│  │de Regras │  │  (Service)   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘   │
└───────────┬─────────────────────────────────┬───────────────────┘
            │                                 │
┌───────────▼──────────┐        ┌─────────────▼───────────────────┐
│  PostgreSQL + PostGIS │        │           Redis                 │
│  (Dados persistentes) │        │     (Cache - planejado)         │
└──────────────────────┘        └─────────────────────────────────┘
```

> **Nota:** O Redis está configurado na infraestrutura (Docker Compose) mas a integração de cache no código backend ainda não foi implementada.

---

## 2. Componentes do Sistema

### 2.1 Frontend (Next.js 14)

**Responsabilidades:**
- Renderização do dashboard com mapas interativos (Leaflet)
- Exibição de alertas e painel de monitoramento hidrológico
- Gráficos e relatórios históricos (Recharts)
- Interface responsiva

**Estrutura interna:**

```
frontend/src/
├── app/                    # App Router (Next.js 14)
│   ├── page.tsx           # Landing → links para dashboard/reports/scenarios
│   ├── layout.tsx         # Layout global (html, body)
│   ├── globals.css        # Estilos globais (Tailwind)
│   ├── dashboard/
│   │   └── page.tsx       # Dashboard principal com mapa + sidebar
│   ├── reports/
│   │   └── page.tsx       # Relatórios e gráficos por município
│   └── scenarios/
│       └── page.tsx       # Cenários (El Niño, La Niña)
├── components/
│   ├── Map/
│   │   ├── BrazilMap.tsx          # Mapa base com estados e municípios
│   │   ├── LayerToggle.tsx        # Alternância de camadas (composite)
│   │   └── MapLegend.tsx          # Legenda de cores de risco
│   ├── Alerts/
│   │   └── AlertPanel.tsx         # Painel de alertas ativos por estado
│   ├── Hydrology/
│   │   └── RiverLevelPanel.tsx    # Painel de nível dos rios por estado
│   ├── Charts/
│   │   ├── PrecipitationChart.tsx          # Precipitação horária
│   │   ├── AccumulatedPrecipitationChart.tsx # Precipitação acumulada
│   │   ├── TemperatureChart.tsx            # Temperatura ao longo do tempo
│   │   └── RiskEvolutionChart.tsx          # Evolução do índice de risco
│   ├── Sidebar/
│   │   └── MunicipalityList.tsx   # Lista de municípios com risco
│   └── Layout/                    # (reservado para futuros componentes)
├── hooks/                         # (reservado para custom hooks)
├── services/
│   └── api.ts                     # Cliente HTTP genérico para o backend
└── types/                         # (reservado para tipos TypeScript)
```

**Bibliotecas principais:**
- `leaflet` + `react-leaflet` — Mapas interativos
- `recharts` — Gráficos de séries temporais
- `tailwindcss` — Estilização utility-first

**Padrões:**
- Client-Side Rendering em todas as páginas (`"use client"`)
- Dynamic imports para componentes Leaflet (incompatível com SSR)
- Polling (5 min) para atualização de dados de risco no dashboard

---

### 2.2 Backend (FastAPI)

**Responsabilidades:**
- API REST para o frontend
- Ingestão e processamento de dados de fontes externas (IBGE, INMET, ANA)
- Motor de regras para cálculo de risco
- Geração e gerenciamento de alertas

**Estrutura interna:**

```
backend/app/
├── main.py                 # Inicialização FastAPI + CORS + routers
├── config.py               # Configurações via pydantic-settings
├── database.py             # Engine AsyncIO SQLAlchemy + session factory
├── models/                 # Modelos SQLAlchemy (ORM)
│   ├── __init__.py         # Importa todos os models
│   ├── geographic.py       # Estado, Municipio (com geometria PostGIS)
│   ├── weather.py          # EstacaoMeteorologica, MedicaoClimatica
│   ├── demographic.py      # DadosDemograficos (vulnerabilidade)
│   ├── hydrology.py        # EstacaoHidrologica, MedicaoHidrologica
│   └── alerts.py           # Alerta (gerado pelo motor de regras)
├── schemas/                # (reservado para Pydantic schemas)
│   └── __init__.py
├── services/               # Lógica de negócio e ingestão
│   ├── ibge_ingest.py      # Ingestão IBGE (localidades + malhas GeoJSON)
│   ├── inmet_ingest.py     # Ingestão INMET (estações + medições)
│   ├── ana_ingest.py       # Ingestão ANA (estações hidrológicas + telemetria)
│   ├── demographic_ingest.py  # Ingestão dados demográficos (IBGE Agregados)
│   ├── risk_engine.py      # Motor de regras + cálculo de risco composto
│   └── alert_service.py    # Geração e lifecycle de alertas
├── api/
│   └── routes/
│       ├── health.py       # GET /health
│       ├── ingest.py       # POST /api/v1/ingest/{source}
│       ├── geographic.py   # GET /api/v1/states, /municipalities, /geojson
│       ├── weather.py      # GET /api/v1/weather/...
│       ├── hydrology.py    # GET /api/v1/hydrology/...
│       ├── risk.py         # GET /api/v1/risk/...
│       ├── alerts.py       # GET/POST /api/v1/alerts/...
│       └── scenarios.py    # GET /api/v1/scenarios/...
└── scheduler/              # (reservado para APScheduler jobs)
    └── __init__.py
```

**Padrões:**
- Dependency Injection via FastAPI `Depends` (sessão de banco)
- Async/await para todo I/O (banco, APIs externas)
- Service layer para lógica de negócio (ingestão, regras, alertas)
- Retry com backoff para APIs externas (INMET, ANA)

---

### 2.3 Camada de Dados

#### PostgreSQL + PostGIS

**Responsabilidades:**
- Armazenamento persistente de todos os dados
- Queries geoespaciais nativas (ST_Contains, ST_Distance, ST_AsGeoJSON)
- Índices espaciais GiST para performance

**Modelo Entidade-Relacionamento:**

```
┌─────────────────┐       ┌─────────────────────┐
│     estados     │       │     municipios      │
├─────────────────┤       ├─────────────────────┤
│ id (PK)         │──┐    │ id (PK)             │
│ codigo_ibge     │  │    │ codigo_ibge         │
│ nome            │  │    │ nome                │
│ sigla           │  └───▶│ estado_id (FK)      │
│ regiao          │       │ geometria           │
│ geometria       │       │ (MultiPolygon)      │
│ (MultiPolygon)  │       │ area_km2            │
└─────────────────┘       │ em_vale (bool)      │
                          └────────┬────────────┘
                                   │
         ┌─────────────────────────┼────────────────────────────────┐
         │                         │                                │
         ▼                         ▼                                ▼
┌─────────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐
│ dados_demograficos  │  │     alertas      │  │  estacoes_meteorologicas │
├─────────────────────┤  ├──────────────────┤  ├──────────────────────────┤
│ id (PK)             │  │ id (PK)          │  │ id (PK)                  │
│ municipio_id (FK)   │  │ municipio_id(FK) │  │ codigo_inmet             │
│ populacao           │  │ tipo             │  │ nome                     │
│ densidade           │  │ severidade       │  │ municipio_id (FK)        │
│ pct_idosos          │  │ indice_risco     │  │ coordenada (Point)       │
│ pct_baixa_renda     │  │ descricao        │  │ altitude                 │
│ idh                 │  │ regras_ativadas  │  │ tipo                     │
│ pct_esgoto          │  │ data_inicio      │  │ ativa (bool)             │
│ indice_vulnerab     │  │ data_fim         │  └────────────┬─────────────┘
│ ano_referencia      │  │ ativo (bool)     │               │
└─────────────────────┘  │ created_at       │               ▼
                         └──────────────────┘  ┌──────────────────────────┐
                                               │   medicoes_climaticas    │
         ┌─────────────────────────────────┐   ├──────────────────────────┤
         │                                 │   │ id (PK)                  │
         ▼                                 │   │ estacao_id (FK)          │
┌──────────────────────────┐               │   │ data_hora                │
│  estacoes_hidrologicas   │               │   │ temperatura              │
├──────────────────────────┤               │   │ temperatura_max/min      │
│ id (PK)                  │               │   │ precipitacao             │
│ codigo_ana               │               │   │ umidade                  │
│ nome                     │               │   │ vento_velocidade         │
│ municipio_id (FK) ───────┘               │   │ vento_direcao            │
│ coordenada (Point)       │               │   │ pressao                  │
│ rio_nome                 │               │   │ radiacao                 │
│ bacia                    │               │   └──────────────────────────┘
│ sub_bacia                │
│ tipo                     │
│ ativa (bool)             │
│ nivel_atencao            │
│ nivel_alerta             │
│ nivel_emergencia         │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│  medicoes_hidrologicas   │
├──────────────────────────┤
│ id (PK)                  │
│ estacao_id (FK)          │
│ data_hora                │
│ nivel (metros)           │
│ vazao (m³/s)             │
│ chuva (mm)               │
└──────────────────────────┘
```

#### Redis

**Status:** Infraestrutura provisionada (Docker Compose) — integração de cache no código ainda não implementada.

**Estratégia de Cache planejada:**

| Chave | TTL | Conteúdo |
|-------|-----|----------|
| `weather:station:{id}:latest` | 1h | Última medição da estação |
| `risk:municipality:{id}` | 5min | Índice de risco calculado |
| `geojson:state:{uf}:municipalities` | 24h | GeoJSON dos municípios |
| `alerts:active:state:{uf}` | 2min | Alertas ativos por estado |

---

## 3. Fluxos Principais

### 3.1 Fluxo de Ingestão de Dados

```
┌────────────┐     ┌────────────┐     ┌────────────────┐     ┌──────────┐
│  Trigger   │────▶│  Serviço   │────▶│  API Externa   │────▶│ Resposta │
│  (manual)  │     │ de Ingestão│     │(INMET/IBGE/ANA)│     │ JSON/XML │
└────────────┘     └────────────┘     └────────────────┘     └────┬─────┘
                                                                   │
                   ┌────────────┐     ┌────────────┐               │
                   │   Motor    │◀────│ PostgreSQL │◀──────────────┘
                   │ de Regras  │     │  (INSERT)  │     (parse + store)
                   └─────┬──────┘     └────────────┘
                         │
                         ▼
                   ┌────────────┐
                   │  Alerta    │
                   │  Gerado?   │
                   └────────────┘
```

> **Nota:** Atualmente a ingestão é disparada manualmente via endpoints POST. O scheduler com APScheduler está planejado mas ainda não implementado.

### 3.2 Fluxo de Requisição do Frontend

```
┌────────┐     ┌────────────┐     ┌────────────┐     ┌────────────┐
│Browser │────▶│  Next.js   │────▶│  FastAPI   │────▶│ PostgreSQL │
│        │     │   (CSR)    │     │            │     │  (query)   │
└────────┘     └────────────┘     └────────────┘     └─────┬──────┘
                                                            │
                                                            ▼
                                                      ┌────────────┐
                                                      │  Resposta  │
                                                      │   JSON     │
                                                      └────────────┘
```

### 3.3 Fluxo de Cálculo de Risco

```
┌──────────────────────────────────────────────────────────────────┐
│                    MOTOR DE REGRAS (Python)                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Dados Climáticos ──┐                                            │
│  (INMET: precip,    │     ┌──────────────┐     ┌─────────────┐  │
│   temperatura,      ├────▶│  Avaliação   │────▶│   Índice    │  │
│   vento)            │     │  de Regras   │     │  Composto   │  │
│                     │     │  (RISK_RULES)│     │  (0-100)    │  │
│  Dados Hidrológicos─┤     └──────────────┘     └──────┬──────┘  │
│  (ANA: nível rio,   │                                  │         │
│   vazão, variação)  │                                  ▼         │
│                     │                          ┌─────────────┐   │
│  Dados Geográficos ─┤                          │Classificação│   │
│  (em_vale)          │                          │baixo/mod/   │   │
│                     │                          │alto/crítico │   │
│  Dados Demográficos─┘                          └──────┬──────┘   │
│  (vulnerabilidade)                                    │          │
└───────────────────────────────────────────────────────┼──────────┘
                                                        │
                                          ┌─────────────▼──────────┐
                                          │  Classificação >= alto?│
                                          │  SIM → Gerar Alerta   │
                                          │  NÃO → Desativar alert│
                                          └────────────────────────┘
```

**Regras implementadas:**

| ID | Nome | Métrica | Limiar | Severidade |
|----|------|---------|--------|------------|
| `flood_24h` | Inundação 24h | Precipitação acumulada 24h | > 80mm | alto |
| `flood_72h_critical` | Inundação Crítica 72h | Precip. 72h + em_vale | > 150mm | critico |
| `heat_health` | Calor Extremo | Temperatura max + pct_idosos > 20% | > 40°C | alto |
| `drought_30d` | Seca | Precipitação acumulada 30d | < 10mm | alto |
| `wind_alert` | Vendaval | Velocidade máx. do vento | > 20 m/s | moderado |
| `river_level_attention` | Rio - Atenção | Nível vs cota de atenção | >= 100% | moderado |
| `river_level_alert` | Rio - Alerta | Nível vs cota de alerta | >= 100% | alto |
| `river_level_emergency` | Rio - Emergência | Nível vs cota de emergência | >= 100% | critico |
| `river_level_rising_fast` | Rio - Subida Rápida | Variação nível em 6h | > 0.5m | alto |

---

## 4. API REST - Endpoints

### 4.1 Infraestrutura

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/` | Info da API (nome, versão, link docs) |
| GET | `/health` | Health check |
| GET | `/docs` | Swagger UI (OpenAPI) |
| GET | `/redoc` | ReDoc |

### 4.2 Geografia

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v1/states` | Lista todos os estados |
| GET | `/api/v1/states/{uf}/municipalities` | Municípios de um estado |
| GET | `/api/v1/geojson/states` | GeoJSON dos estados |
| GET | `/api/v1/geojson/municipalities?state={uf}` | GeoJSON dos municípios de um estado |

### 4.3 Meteorologia

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v1/weather/stations` | Lista estações (filtro: state) |
| GET | `/api/v1/weather/readings/{station_id}` | Medições recentes de uma estação |
| GET | `/api/v1/weather/municipality/{id}/readings` | Medições de todas as estações de um município |

### 4.4 Hidrologia (ANA)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v1/hydrology/stations` | Lista estações hidrológicas (filtros: state, rio) |
| GET | `/api/v1/hydrology/stations/{id}` | Detalhes + última medição + status do nível |
| GET | `/api/v1/hydrology/readings/{station_id}` | Medições hidrológicas recentes |
| GET | `/api/v1/hydrology/municipality/{id}` | Estações e medições de um município |
| GET | `/api/v1/hydrology/status` | Resumo: estações em alerta/emergência (filtro: state) |

### 4.5 Risco

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v1/risk/{municipio_id}` | Risco calculado de um município |
| GET | `/api/v1/risk/map?state={uf}` | Mapa de risco por estado |

### 4.6 Alertas

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v1/alerts` | Lista alertas (filtros: state, municipality_id, severity, active) |
| GET | `/api/v1/alerts/active/count` | Contagem de alertas ativos por severidade |
| GET | `/api/v1/alerts/{id}` | Detalhes de um alerta |
| POST | `/api/v1/alerts/process?state={uf}` | Dispara processamento de alertas para um estado |

### 4.7 Cenários

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v1/scenarios` | Lista cenários disponíveis (El Niño, La Niña) |
| GET | `/api/v1/scenarios/{id}` | Detalhes e impactos de um cenário |
| GET | `/api/v1/scenarios/{id}/risk-map` | Mapa de risco projetado (filtro: state) |

### 4.8 Ingestão (Admin)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/v1/ingest/setup-db` | Cria extensão PostGIS + todas as tabelas |
| POST | `/api/v1/ingest/ibge` | Ingestão IBGE (estados + municípios + geometrias) |
| POST | `/api/v1/ingest/inmet` | Ingestão INMET (estações; readings=true para medições) |
| POST | `/api/v1/ingest/demographics` | Ingestão demográfica (requer param `state`) |
| POST | `/api/v1/ingest/ana` | Ingestão ANA (estações hidrológicas; readings=true para telemetria) |

---

## 5. Deploy e Infraestrutura

### 5.1 Docker Compose

```yaml
services:
  # Backend API - FastAPI
  api:
    build: ./backend
    ports: ["8001:8000"]        # Exposto na porta 8001 do host
    depends_on: [db, redis]
    environment:
      - DATABASE_URL=postgresql+asyncpg://alertabr:alertabr@db:5432/alertabr
      - REDIS_URL=redis://redis:6379/0
    healthcheck: python urllib (GET /health)

  # Frontend - Next.js
  web:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [api]
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000  # acesso interno

  # Database - PostgreSQL 16 + PostGIS 3.4
  db:
    image: postgis/postgis:16-3.4
    ports: ["5433:5432"]       # Exposto na porta 5433 do host
    healthcheck: pg_isready

  # Cache - Redis 7
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    healthcheck: redis-cli ping

volumes:
  pgdata:                       # Persistência do PostgreSQL
```

### 5.2 Variáveis de Ambiente

| Variável | Default | Descrição |
|----------|---------|-----------|
| `DB_NAME` | alertabr | Nome do banco PostgreSQL |
| `DB_USER` | alertabr | Usuário do banco |
| `DB_PASSWORD` | alertabr | Senha do banco |
| `DEBUG` | false | Modo debug (echo SQL) |
| `DATABASE_URL` | postgresql+asyncpg://... | URL completa do banco |
| `REDIS_URL` | redis://redis:6379/0 | URL do Redis |
| `NEXT_PUBLIC_API_URL` | http://localhost:8001 | URL da API para o frontend |
| `INMET_BASE_URL` | https://apitempo.inmet.gov.br | Base URL do INMET |
| `IBGE_BASE_URL` | https://servicodados.ibge.gov.br | Base URL do IBGE |
| `ANA_TELEMETRIA_URL` | http://telemetriaws1.ana.gov.br/ServiceANA.asmx | Web service SOAP da ANA |

### 5.3 Migrações (Alembic)

| Revisão | Descrição |
|---------|-----------|
| 001 | Schema inicial: estados, municípios, estações meteorológicas, medições climáticas, dados demográficos, alertas + índices GiST |
| 002 | Tabelas hidrológicas (ANA): estações hidrológicas, medições hidrológicas + índices |

---

## 6. Tecnologias

### Backend
- **Python 3.11+**
- **FastAPI** 0.115 — Framework web async
- **SQLAlchemy** 2.0 (async) — ORM
- **asyncpg** — Driver PostgreSQL async
- **GeoAlchemy2** — Extensão geoespacial para SQLAlchemy
- **Alembic** — Migrações de banco
- **httpx** — HTTP client async
- **xmltodict** — Parsing XML (web service SOAP da ANA)
- **pydantic-settings** — Configuração via variáveis de ambiente
- **Shapely** — Operações geométricas
- **APScheduler** — Agendamento (dependência instalada, implementação pendente)

### Frontend
- **Next.js** 14.2 — Framework React
- **React** 18.3
- **TypeScript** 5.6
- **Leaflet** 1.9 + **react-leaflet** 4.2 — Mapas interativos
- **Recharts** 2.12 — Gráficos
- **Tailwind CSS** 3.4 — Estilização

### Infraestrutura
- **PostgreSQL** 16 + **PostGIS** 3.4 — Banco geoespacial
- **Redis** 7 — Cache (provisionado)
- **Docker Compose** — Orquestração local
