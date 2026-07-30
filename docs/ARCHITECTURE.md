# Arquitetura - AlertaBR

## Plataforma de Prevenção a Desastres Naturais

---

## 1. Visão Geral da Arquitetura

O AlertaBR segue uma arquitetura de **três camadas** (frontend, backend, dados) com comunicação via REST API. O sistema é monorepo com deploy containerizado via Docker Compose.

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENTE (Browser)                         │
├─────────────────────────────────────────────────────────────────┤
│  Next.js 14 (SSR + CSR)                                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │Dashboard │  │  Mapas   │  │ Alertas  │  │  Relatórios  │   │
│  │  (SSR)   │  │(Leaflet) │  │  (SSR)   │  │  (Charts)    │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP/REST (JSON)
┌───────────────────────────▼─────────────────────────────────────┐
│                     BACKEND (FastAPI)                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ REST API │  │ Ingestão │  │  Motor   │  │  Scheduler   │   │
│  │ (Routes) │  │(Services)│  │de Regras │  │ (APScheduler)│   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘   │
└───────────┬─────────────────────────────────┬───────────────────┘
            │                                 │
┌───────────▼──────────┐        ┌─────────────▼───────────────────┐
│  PostgreSQL + PostGIS │        │           Redis                 │
│  (Dados persistentes) │        │     (Cache, TTL 1h)            │
└──────────────────────┘        └─────────────────────────────────┘
```

---

## 2. Componentes do Sistema

### 2.1 Frontend (Next.js 14)

**Responsabilidades:**
- Renderização do dashboard com mapas interativos
- Exibição de alertas em tempo real
- Gráficos e relatórios históricos
- Interface responsiva (mobile-first)

**Estrutura interna:**

```
frontend/src/
├── app/                    # App Router (Next.js 14)
│   ├── page.tsx           # Landing → redireciona ao dashboard
│   ├── layout.tsx         # Layout global (header, nav)
│   ├── dashboard/
│   │   └── page.tsx       # Dashboard principal com mapa
│   ├── reports/
│   │   └── page.tsx       # Relatórios e gráficos
│   └── scenarios/
│       └── page.tsx       # Cenários (El Niño)
├── components/
│   ├── Map/
│   │   ├── BrazilMap.tsx          # Mapa base com estados
│   │   ├── MunicipalityLayer.tsx  # Camada de municípios
│   │   ├── RiskHeatmap.tsx        # Colorização por risco
│   │   └── MapLegend.tsx          # Legenda de cores
│   ├── Alerts/
│   │   ├── AlertPanel.tsx         # Painel lateral de alertas
│   │   ├── AlertCard.tsx          # Card individual de alerta
│   │   └── AlertFilters.tsx       # Filtros de severidade/região
│   ├── Charts/
│   │   ├── TimeSeriesChart.tsx    # Gráfico de séries temporais
│   │   ├── RiskEvolution.tsx      # Evolução do índice de risco
│   │   └── PeriodComparison.tsx   # Comparação entre períodos
│   └── Layout/
│       ├── Header.tsx             # Cabeçalho com navegação
│       ├── Sidebar.tsx            # Menu lateral
│       └── ProfileSelector.tsx    # Seletor governo/cidadão/pesquisador
├── hooks/
│   ├── useRiskData.ts             # Hook para dados de risco
│   ├── useAlerts.ts               # Hook para alertas (polling)
│   └── useWeatherData.ts          # Hook para dados climáticos
├── services/
│   └── api.ts                     # Cliente HTTP para o backend
└── types/
    ├── geographic.ts              # Tipos geográficos
    ├── weather.ts                 # Tipos meteorológicos
    └── risk.ts                    # Tipos de risco e alertas
```

**Padrões:**
- Server-Side Rendering (SSR) para SEO e performance inicial
- Client-Side Rendering para interações com mapa
- Polling (5 min) para atualização de dados de risco
- Push API para notificações de alertas críticos

---

### 2.2 Backend (FastAPI)

**Responsabilidades:**
- API REST para o frontend
- Ingestão e processamento de dados de fontes externas
- Motor de regras para cálculo de risco
- Geração e gerenciamento de alertas
- Agendamento de jobs periódicos

**Estrutura interna:**

```
backend/app/
├── main.py                 # Inicialização FastAPI + lifecycle
├── config.py               # Configurações via env vars
├── database.py             # Engine SQLAlchemy + session
├── models/                 # Modelos SQLAlchemy
│   ├── __init__.py
│   ├── geographic.py       # Estado, Municipio (com geometria)
│   ├── weather.py          # EstacaoMeteorologica, MedicaoClimatica
│   ├── demographic.py      # DadosDemograficos, Vulnerabilidade
│   └── alerts.py           # Alerta
├── schemas/                # Pydantic schemas (request/response)
│   ├── geographic.py
│   ├── weather.py
│   ├── risk.py
│   └── alerts.py
├── services/               # Lógica de negócio
│   ├── ibge_ingest.py      # Ingestão IBGE (localidades + malhas)
│   ├── inmet_ingest.py     # Ingestão INMET (estações + medições)
│   ├── ana_ingest.py       # Ingestão ANA (hidrologia)
│   ├── demographic_ingest.py  # Ingestão dados demográficos
│   ├── risk_engine.py      # Motor de regras + cálculo de risco
│   └── alert_service.py    # Gerenciamento de alertas
├── api/
│   ├── deps.py             # Dependências (DB session, etc.)
│   └── routes/
│       ├── health.py       # GET /health
│       ├── ingest.py       # POST /api/v1/ingest/{source}
│       ├── geographic.py   # GET /api/v1/states, /municipalities
│       ├── weather.py      # GET /api/v1/weather/...
│       ├── risk.py         # GET /api/v1/risk/...
│       ├── alerts.py       # GET /api/v1/alerts/...
│       └── scenarios.py    # GET /api/v1/scenarios/...
└── scheduler/
    └── jobs.py             # Definição de jobs APScheduler
```

**Padrões:**
- Dependency Injection via FastAPI Depends
- Async/await para I/O (banco, APIs externas)
- Repository pattern para acesso a dados
- Service layer para lógica de negócio

---

### 2.3 Camada de Dados

#### PostgreSQL + PostGIS

**Responsabilidades:**
- Armazenamento persistente de todos os dados
- Queries geoespaciais nativas (ST_Contains, ST_Distance, ST_Within)
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
│ geometria       │       │ geometria           │
│ (MultiPolygon)  │       │ (MultiPolygon)      │
└─────────────────┘       │ area_km2            │
                          │ em_vale (bool)      │
                          └────────┬────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
              ▼                    ▼                    ▼
┌─────────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ dados_demograficos  │  │    alertas      │  │   estacoes_     │
├─────────────────────┤  ├─────────────────┤  │ meteorologicas  │
│ id (PK)             │  │ id (PK)         │  ├─────────────────┤
│ municipio_id (FK)   │  │ municipio_id(FK)│  │ id (PK)         │
│ populacao           │  │ tipo            │  │ codigo_inmet    │
│ densidade           │  │ severidade      │  │ nome            │
│ pct_idosos          │  │ descricao       │  │ municipio_id(FK)│
│ pct_baixa_renda     │  │ indice_risco    │  │ coordenada      │
│ idh                 │  │ regras_ativadas │  │ (Point)         │
│ indice_vulnerab     │  │ data_inicio     │  └────────┬────────┘
│ ano_referencia      │  │ data_fim        │           │
└─────────────────────┘  │ ativo (bool)    │           ▼
                         └─────────────────┘  ┌─────────────────┐
                                              │   medicoes_     │
                                              │   climaticas    │
                                              ├─────────────────┤
                                              │ id (PK)         │
                                              │ estacao_id (FK) │
                                              │ data_hora       │
                                              │ temperatura     │
                                              │ precipitacao    │
                                              │ umidade         │
                                              │ vento_velocidade│
                                              │ vento_direcao   │
                                              └─────────────────┘
```

#### Redis

**Responsabilidades:**
- Cache de respostas de APIs externas (TTL: 1 hora)
- Cache de cálculos de risco recentes (TTL: 5 minutos)
- Cache de GeoJSON simplificado para o frontend

**Estratégia de Cache:**

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
┌────────────┐     ┌────────────┐     ┌────────────┐     ┌────────────┐
│ APScheduler│────▶│  Serviço   │────▶│ API Externa│────▶│  Resposta  │
│ (cron 1h)  │     │ de Ingestão│     │(INMET/IBGE)│     │   JSON     │
└────────────┘     └────────────┘     └────────────┘     └─────┬──────┘
                                                                │
                   ┌────────────┐     ┌────────────┐            │
                   │   Motor    │◀────│ PostgreSQL │◀───────────┘
                   │ de Regras  │     │  (INSERT)  │     (parse + store)
                   └─────┬──────┘     └────────────┘
                         │
                         ▼
                   ┌────────────┐     ┌────────────┐
                   │  Alerta    │────▶│   Redis    │
                   │  Gerado?   │     │  (invalidar│
                   └────────────┘     │   cache)   │
                                      └────────────┘
```

### 3.2 Fluxo de Requisição do Frontend

```
┌────────┐     ┌────────────┐     ┌────────────┐     ┌────────────┐
│Browser │────▶│  Next.js   │────▶│  FastAPI   │────▶│   Redis    │
│        │     │   (SSR)    │     │            │     │  (cache?)  │
└────────┘     └────────────┘     └────────────┘     └─────┬──────┘
                                                            │
                                       ┌────────────┐      │ miss
                                       │ PostgreSQL │◀─────┘
                                       │  (query)   │
                                       └─────┬──────┘
                                             │
                                             ▼
                                       ┌────────────┐
                                       │  Resposta  │──▶ Cache no Redis
                                       │   JSON     │──▶ Retorna ao client
                                       └────────────┘
```

### 3.3 Fluxo de Cálculo de Risco

```
┌──────────────────────────────────────────────────────────────────┐
│                    MOTOR DE REGRAS                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Dados Climáticos ──┐                                            │
│  (precipitação,     │     ┌──────────────┐     ┌─────────────┐  │
│   temperatura,      ├────▶│  Avaliação   │────▶│   Índice    │  │
│   umidade)          │     │  de Regras   │     │  Composto   │  │
│                     │     │  (YAML)      │     │  (0-100)    │  │
│  Dados Geográficos ─┤     └──────────────┘     └──────┬──────┘  │
│  (relevo, vale,     │                                  │         │
│   proximidade rio)  │                                  ▼         │
│                     │                          ┌─────────────┐   │
│  Dados Demográficos─┘                          │Classificação│   │
│  (vulnerabilidade)                             │baixo/mod/   │   │
│                                                │alto/crítico │   │
│                                                └──────┬──────┘   │
└───────────────────────────────────────────────────────┼──────────┘
                                                        │
                                          ┌─────────────▼──────────┐
                                          │  Limiar ultrapassado?  │
                                          │  SIM → Gerar Alerta   │
                                          │  NÃO → Apenas armazenar│
                                          └────────────────────────┘
```

---

## 4. API REST - Endpoints Principais

### 4.1 Infraestrutura

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/health` | Health check |
| GET | `/api/v1/info` | Informações da API |

### 4.2 Geografia

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v1/states` | Lista estados |
| GET | `/api/v1/states/{uf}/municipalities` | Municípios de um estado |
| GET | `/api/v1/municipalities/{id}` | Detalhes de um município |
| GET | `/api/v1/geojson/states` | GeoJSON dos estados |
| GET | `/api/v1/geojson/municipalities?state={uf}` | GeoJSON dos municípios |

### 4.3 Meteorologia

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v1/weather/stations` | Lista estações |
| GET | `/api/v1/weather/stations/{id}` | Detalhes da estação |
| GET | `/api/v1/weather/readings/{station_id}` | Medições recentes |
| GET | `/api/v1/weather/readings/{station_id}/history` | Histórico |

### 4.4 Risco

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v1/risk/{municipio_id}` | Risco de um município |
| GET | `/api/v1/risk/map?state={uf}` | Mapa de risco por estado |
| GET | `/api/v1/risk/summary` | Resumo nacional |

### 4.5 Alertas

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v1/alerts` | Lista alertas (filtros: state, severity, active) |
| GET | `/api/v1/alerts/{id}` | Detalhes de um alerta |
| GET | `/api/v1/alerts/active/count` | Contagem de alertas ativos |

### 4.6 Cenários

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v1/scenarios` | Lista cenários disponíveis |
| GET | `/api/v1/scenarios/el-nino` | Projeção El Niño |
| GET | `/api/v1/scenarios/{id}/risk-map` | Mapa de risco projetado |

### 4.7 Ingestão (Admin)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/v1/ingest/ibge` | Trigger ingestão IBGE |
| POST | `/api/v1/ingest/inmet` | Trigger ingestão INMET |
| POST | `/api/v1/ingest/demographics` | Trigger ingestão demográfica |

---

## 5. Deploy e Infraestrutura

### 5.1 Docker Compose

```yaml
services:
  # Backend API
  api:
    build: ./backend
    ports: ["8000:8000"]
    depends_on: [db, redis]
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/alertabr
      - REDIS_URL=redis://redis:6379
    
  # Frontend
  web:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [api]
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    
  # Banco de dados
  db:
    image: postgis/postgis:16-3.4
    ports: ["5432:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]
    environment:
      - POSTGRES_DB=alertabr
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    
  # Cache
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

volumes:
  pgdata:
```

### 5.2 Rede de Comunicação

```
┌─────────────────────────────────────────────────────────┐
│                   Docker Network                         │
│                                                         │
│  ┌─────┐    ┌─────┐    ┌──────────┐    ┌─────────┐    │
│  │ web │───▶│ api │───▶│    db    │    │  redis  │    │
│  │:3000│    │:8000│───▶│   :5432  │    │  :6379  │    │
│  └─────┘    └──┬──┘    └──────────┘    └────▲────┘    │
│               │                              │         │
│               └──────────────────────────────┘         │
└─────────────────────────────────────────────────────────┘
      ▲              ▲
      │              │
   localhost:3000  localhost:8000
   (browser)      (API direta)
```

---

## 6. Segurança e Resiliência

### 6.1 Segurança (v1 - Acesso Público)
- CORS configurado para origens conhecidas
- Rate limiting na API (ex: 100 req/min por IP)
- Input validation via Pydantic
- SQL injection prevenido por ORM (SQLAlchemy)
- Sem dados sensíveis expostos (dados públicos)

### 6.2 Resiliência
- **Circuit breaker** para APIs externas (retry com backoff)
- **Cache como fallback** quando API externa está indisponível
- **Graceful degradation**: dashboard funciona com dados em cache mesmo sem conexão com fontes
- **Health checks** em todos os serviços Docker
- **Logs estruturados** para diagnóstico

### 6.3 Performance
- Índices GiST para queries geoespaciais (<100ms)
- Redis cache para dados frequentes
- GeoJSON simplificado para renderização no frontend
- Paginação em todas as listagens
- Lazy loading de dados detalhados

---

## 7. Decisões Arquiteturais (ADRs)

### ADR-001: Monorepo com Docker Compose
**Decisão:** Monorepo (`/backend`, `/frontend`) com orquestração via Docker Compose.  
**Motivo:** Simplicidade para v1, deploy local sem cloud. Facilita desenvolvimento e testing.

### ADR-002: FastAPI ao invés de Django
**Decisão:** FastAPI para o backend.  
**Motivo:** Suporte nativo a async (crucial para I/O com APIs externas), performance superior, tipagem forte com Pydantic, excelente para APIs REST.

### ADR-003: PostGIS ao invés de MongoDB com GeoJSON
**Decisão:** PostgreSQL + PostGIS para dados geoespaciais.  
**Motivo:** Queries geoespaciais otimizadas (índices GiST), SQL para joins complexos, maturidade do ecossistema, integração com SQLAlchemy.

### ADR-004: Motor de regras em código ao invés de ML
**Decisão:** Regras configuráveis (YAML) para v1, sem machine learning.  
**Motivo:** Interpretabilidade (explicar por que um alerta foi gerado), simplicidade, sem necessidade de dados de treinamento. ML pode ser adicionado em versões futuras.

### ADR-005: Leaflet ao invés de Mapbox/Google Maps
**Decisão:** Leaflet + React-Leaflet para mapas.  
**Motivo:** Open-source (sem custo de API), leve, suporte completo a GeoJSON, customização de camadas, comunidade ativa.

### ADR-006: Redis para cache ao invés de in-memory
**Decisão:** Redis externo para caching.  
**Motivo:** Persistência entre restarts, compartilhável entre instâncias (futuro scale-out), TTL nativo, estruturas de dados avançadas.

---

*Documento gerado em: Julho 2026*  
*Versão: 1.0*
