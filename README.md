# AlertaBR - Plataforma de Prevenção a Desastres Naturais

Plataforma web que cruza dados geográficos, demográficos e climáticos em tempo real para antecipar e mitigar impactos de fenômenos como El Niño, oferecendo mapas de risco interativos, alertas automáticos e relatórios preditivos para todo o território nacional.

---

## Quickstart

```bash
# 1. Clonar o repositório
git clone <url-do-repositorio>
cd alertabr

# 2. Configurar variáveis de ambiente
cp .env.example .env

# 3. Subir todos os serviços
docker-compose up -d

# 4. Criar as tabelas no banco de dados
curl -X POST http://localhost:8001/api/v1/ingest/setup-db

# 5. Carregar dados iniciais (Santa Catarina como demo)
curl -X POST "http://localhost:8001/api/v1/ingest/ibge?uf=SC"
curl -X POST http://localhost:8001/api/v1/ingest/inmet
curl -X POST "http://localhost:8001/api/v1/ingest/demographics?state=SC"
```

Após o setup:

| Serviço | URL |
|---------|-----|
| Frontend (Dashboard) | http://localhost:3000 |
| Backend API | http://localhost:8001 |
| Swagger (Docs da API) | http://localhost:8001/docs |
| PostgreSQL | localhost:5433 |
| Redis | localhost:6379 |

---

## Visão Geral

O AlertaBR monitora riscos climáticos em todos os 5.570 municípios brasileiros através de:

- **Mapa interativo** com drill-down por estado e município, colorizado por índice de risco
- **Motor de regras** configurável que avalia precipitação, temperatura, vento e vulnerabilidade social
- **Sistema de alertas** automático com classificação por severidade (baixo, moderado, alto, crítico)
- **Relatórios** com séries temporais, comparação entre períodos e linhas de limiar
- **Simulação de cenários** como El Niño e La Niña com projeção de impactos por região

### Público-Alvo

| Perfil | Uso Principal |
|--------|--------------|
| Governo / Defesa Civil | Tomada de decisão e alocação de recursos |
| Cidadãos | Informação sobre riscos na sua região |
| Pesquisadores | Dados históricos e análise de tendências |

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│                   Browser (Cliente)                       │
│   Next.js 14 · React-Leaflet · Recharts · Tailwind      │
└─────────────────────────┬───────────────────────────────┘
                          │ REST/JSON
┌─────────────────────────▼───────────────────────────────┐
│                   Backend (FastAPI)                       │
│   Ingestão · Motor de Regras · Alertas · Scheduler       │
└────────────┬────────────────────────────┬───────────────┘
             │                            │
┌────────────▼──────────┐    ┌────────────▼───────────────┐
│  PostgreSQL + PostGIS  │    │          Redis             │
│  (dados persistentes)  │    │     (cache, TTL)           │
└────────────────────────┘    └────────────────────────────┘
```

Para detalhes completos da arquitetura, consulte [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Stack Tecnológica

### Backend

| Tecnologia | Versão | Propósito |
|-----------|--------|-----------|
| Python | 3.12 | Linguagem principal |
| FastAPI | 0.115 | Framework web assíncrono |
| SQLAlchemy + GeoAlchemy2 | 2.0 | ORM com suporte geoespacial |
| Alembic | 1.13 | Migrações de banco de dados |
| APScheduler | 3.10 | Agendamento de jobs de ingestão |
| httpx | 0.27 | Cliente HTTP assíncrono |
| Shapely | 2.0 | Manipulação de geometrias |

### Frontend

| Tecnologia | Versão | Propósito |
|-----------|--------|-----------|
| Next.js | 14.2 | Framework React com SSR |
| TypeScript | 5.6 | Tipagem estática |
| React-Leaflet | 4.2 | Mapas interativos |
| Recharts | 2.12 | Gráficos e visualizações |
| Tailwind CSS | 3.4 | Estilização responsiva |

### Infraestrutura

| Tecnologia | Versão | Propósito |
|-----------|--------|-----------|
| PostgreSQL + PostGIS | 16 + 3.4 | Banco com queries geoespaciais |
| Redis | 7 (Alpine) | Cache de dados frequentes |
| Docker Compose | - | Orquestração local |

---

## Fontes de Dados

Todas as fontes são públicas e gratuitas, sem necessidade de autenticação:

| Fonte | Dados | Frequência |
|-------|-------|------------|
| [IBGE Localidades](https://servicodados.ibge.gov.br/api/v1/localidades/) | Estados, municípios, regiões | Sob demanda (estáticos) |
| [IBGE Malhas](https://servicodados.ibge.gov.br/api/v3/malhas/) | GeoJSON dos limites geográficos | Sob demanda (estáticos) |
| [IBGE Agregados](https://servicodados.ibge.gov.br/api/v3/agregados/) | População, renda, vulnerabilidade | Mensal |
| [INMET](https://apitempo.inmet.gov.br/) | Estações meteorológicas, medições horárias | Horária |
| ANA/SNIRH (HidroWeb) | Níveis de rios, vazão | A cada 2h (futuro) |

Para detalhes de cada fonte e estratégia de ingestão, consulte [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md).

---

## API - Endpoints Principais

### Infraestrutura

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/health` | Health check |
| GET | `/docs` | Swagger UI |

### Ingestão (Setup)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/v1/ingest/setup-db` | Criar tabelas no banco |
| POST | `/api/v1/ingest/ibge?uf={UF}` | Ingerir dados IBGE de um estado |
| POST | `/api/v1/ingest/inmet` | Ingerir estações meteorológicas |
| POST | `/api/v1/ingest/inmet?readings=true` | Ingerir estações + medições |
| POST | `/api/v1/ingest/demographics?state={UF}` | Ingerir dados demográficos |

### Consultas

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v1/states` | Listar estados |
| GET | `/api/v1/states/{uf}/municipalities` | Municípios de um estado |
| GET | `/api/v1/geojson/states` | GeoJSON dos estados |
| GET | `/api/v1/geojson/municipalities?state={UF}` | GeoJSON dos municípios |
| GET | `/api/v1/weather/stations?state={UF}` | Estações meteorológicas |
| GET | `/api/v1/weather/readings/{station_id}` | Medições recentes |
| GET | `/api/v1/risk/{municipio_id}` | Risco de um município |
| GET | `/api/v1/risk/map?state={UF}` | Mapa de risco por estado |
| GET | `/api/v1/alerts` | Listar alertas (filtros: state, severity, active) |
| GET | `/api/v1/alerts/active/count` | Contagem de alertas ativos |
| POST | `/api/v1/alerts/process?state={UF}` | Processar alertas de um estado |
| GET | `/api/v1/scenarios` | Listar cenários disponíveis |
| GET | `/api/v1/scenarios/el-nino` | Detalhes do cenário El Niño |
| GET | `/api/v1/scenarios/{id}/risk-map` | Mapa de risco projetado |

---

## Modelo de Risco

O índice de risco varia de 0 a 100, calculado pela combinação de:

- **Risco Climático** (peso 40%): precipitação, temperatura, umidade, vento
- **Vulnerabilidade Geográfica** (peso 30%): relevo, proximidade de rios, histórico
- **Vulnerabilidade Social** (peso 30%): densidade, faixa etária, renda, infraestrutura

### Classificação

| Faixa | Classificação | Cor no Mapa |
|-------|--------------|-------------|
| 0-25 | Baixo | Verde |
| 26-50 | Moderado | Amarelo |
| 51-75 | Alto | Laranja |
| 76-100 | Crítico | Vermelho |

### Regras Configuráveis

As regras são definidas em YAML e incluem:

- Risco de Inundação: precipitação 24h > 80mm
- Risco Crítico de Inundação: precipitação 72h > 150mm + município em vale
- Risco de Saúde (Calor): temperatura > 40°C + população idosa > 20%
- Risco de Seca: precipitação 30 dias < 10mm
- Alerta de Vendaval: vento > 20 m/s

---

## Estrutura do Projeto

```
alertabr/
├── docker-compose.yml          # Orquestração dos serviços
├── .env.example                # Template de variáveis de ambiente
├── docs/
│   ├── ARCHITECTURE.md         # Arquitetura detalhada
│   ├── DATA_SOURCES.md         # Documentação das fontes de dados
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/                # Migrações de banco
│   ├── app/
│   │   ├── main.py             # Entrada da aplicação FastAPI
│   │   ├── config.py           # Configurações (env vars)
│   │   ├── database.py         # Engine SQLAlchemy + session
│   │   ├── models/             # Modelos do banco (SQLAlchemy + GeoAlchemy2)
│   │   ├── services/           # Lógica de negócio (ingestão, risco, alertas)
│   │   ├── api/routes/         # Endpoints REST
│   │   └── scheduler/          # Jobs agendados (APScheduler)
│   └── tests/
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── app/                # App Router (Next.js 14)
│       │   ├── dashboard/      # Dashboard com mapa interativo
│       │   ├── reports/        # Relatórios e gráficos
│       │   └── scenarios/      # Simulação de cenários
│       └── components/
│           ├── Map/            # Mapa (BrazilMap, RiskHeatmap, Legend)
│           ├── Alerts/         # Painel de alertas
│           └── Charts/         # Gráficos (Precipitação, Temperatura, Risco)
└── config/
    └── scenarios/              # Cenários pré-configurados (El Niño, La Niña)
```

---

## Desenvolvimento Local

### Pré-requisitos

- Docker e Docker Compose
- (Opcional) Node.js 18+ para desenvolvimento frontend sem Docker
- (Opcional) Python 3.12+ para desenvolvimento backend sem Docker

### Comandos Úteis

```bash
# Subir todos os serviços
docker-compose up -d

# Ver logs de um serviço específico
docker-compose logs -f api

# Reconstruir após mudanças no código
docker compose build --no-cache

# Parar todos os serviços
docker-compose down

# Parar e remover volumes (reset completo do banco)
docker-compose down -v

# Acessar o banco diretamente
docker-compose exec db psql -U alertabr -d alertabr

# Rodar testes do backend
docker-compose exec api pytest

# Verificar saúde dos serviços
docker-compose ps
```

### Desenvolvimento Frontend (sem Docker)

```bash
cd frontend
npm install
npm run dev
# Acesse http://localhost:3000
```

### Desenvolvimento Backend (sem Docker)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# Acesse http://localhost:8000/docs
```

---

## Configuração de Portas

| Serviço | Porta Interna | Porta Externa | Nota |
|---------|--------------|---------------|------|
| API (FastAPI) | 8000 | **8001** | Mapeada para 8001 para evitar conflito local |
| Frontend (Next.js) | 3000 | 3000 | - |
| PostgreSQL | 5432 | **5433** | Mapeada para 5433 para evitar conflito local |
| Redis | 6379 | 6379 | - |

---

## Cenários de Simulação

O sistema suporta simulação de cenários climáticos pré-configurados:

### El Niño

| Região | Impacto Projetado | Risco Principal |
|--------|-------------------|-----------------|
| Sul | Chuvas 60% acima da média | Inundação (alto a crítico) |
| Sudeste | Chuvas 30% acima + calor | Inundação (moderado a alto) |
| Nordeste | Precipitação 60% abaixo | Seca (alto a crítico) |
| Norte | Redução de chuvas | Seca / Incêndios (moderado a alto) |
| Centro-Oeste | Chuvas levemente abaixo | Seca (moderado) |

---

## Decisões Técnicas

- **FastAPI** ao invés de Django: suporte nativo a async, performance superior para I/O com APIs externas
- **PostGIS** ao invés de MongoDB: queries geoespaciais otimizadas com índices GiST, joins complexos
- **Motor de regras** ao invés de ML: interpretabilidade (explicar por que um alerta foi gerado), simplicidade
- **Leaflet** ao invés de Mapbox: open-source, sem custo de API, suporte completo a GeoJSON
- **Redis** para cache: persistência entre restarts, TTL nativo, compartilhável entre instâncias

---

## Documentação Adicional

- [Arquitetura Detalhada](docs/ARCHITECTURE.md) - Diagramas, fluxos, ADRs
- [Fontes de Dados](docs/DATA_SOURCES.md) - APIs, formatos, estratégias de ingestão
- [Plano de Implementação](docs/IMPLEMENTATION_PLAN.md) - Requisitos, cronograma, riscos
- [Tasks](docs/TASKS.md) - Detalhamento de cada task de implementação

---

## Licença

Projeto acadêmico / demonstrativo. Dados consumidos são de fontes públicas brasileiras (IBGE, INMET, ANA).
