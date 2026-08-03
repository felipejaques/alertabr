# Fontes de Dados - AlertaBR

## Plataforma de Prevenção a Desastres Naturais

---

## 1. Visão Geral das Fontes

O AlertaBR consome dados de três fontes públicas principais, todas gratuitas e sem necessidade de autenticação:

| Fonte | Tipo de Dado | Frequência de Atualização | Uso no Sistema |
|-------|-------------|---------------------------|----------------|
| **IBGE** | Geográfico + Demográfico | Sob demanda (dados estáticos) | Geometrias, população, vulnerabilidade |
| **INMET** | Meteorológico | Sob demanda (manual via endpoint) | Precipitação, temperatura, vento |
| **ANA** | Hidrológico | Sob demanda (manual via endpoint) | Nível de rios, vazão, chuva |

> **Nota:** Atualmente toda a ingestão é disparada manualmente via endpoints POST (`/api/v1/ingest/*`). O agendamento automático via APScheduler está planejado mas ainda não implementado.

---

## 2. IBGE - Instituto Brasileiro de Geografia e Estatística

### 2.1 API Localidades

**Base URL:** `https://servicodados.ibge.gov.br/api/v1/localidades/`

**Descrição:** Fornece a estrutura político-administrativa do Brasil com hierarquia completa.

#### Endpoints Utilizados

| Endpoint | Retorno | Uso |
|----------|---------|-----|
| `/estados` | Lista de 27 UFs | Popular tabela `estados` |
| `/estados/{UF}/municipios` | Municípios de um estado | Popular tabela `municipios` |

#### Exemplo de Resposta - Estados

```json
[
  {
    "id": 42,
    "sigla": "SC",
    "nome": "Santa Catarina",
    "regiao": {
      "id": 4,
      "sigla": "S",
      "nome": "Sul"
    }
  }
]
```

#### Exemplo de Resposta - Municípios

```json
[
  {
    "id": 4202404,
    "nome": "Blumenau",
    "microrregiao": {
      "id": 42010,
      "nome": "Blumenau",
      "mesorregiao": {
        "id": 4201,
        "nome": "Vale do Itajaí"
      }
    }
  }
]
```

#### Implementação

Serviço: `backend/app/services/ibge_ingest.py` → classe `IBGEIngestService`

- `ingest_estados(db)` — Insere todos os estados + busca geometrias de contorno
- `ingest_municipios_estado(uf_sigla, db)` — Insere municípios de um estado com geometrias
- `ingest_all(db)` — Executa ingestão completa (estados + municípios de todos)

#### Considerações
- **Rate limit:** Não documentado, mas recomenda-se não mais que 10 req/s
- **Disponibilidade:** Alta (serviço público consolidado)
- **Cache recomendado:** 30 dias (dados mudam apenas em anos censitários)

---

### 2.2 API Malhas (GeoJSON)

**Base URL:** `https://servicodados.ibge.gov.br/api/v3/malhas/`

**Descrição:** Fornece as geometrias (polígonos) dos limites geográficos em formato GeoJSON.

#### Endpoints Utilizados

| Endpoint | Parâmetros | Retorno |
|----------|-----------|---------|
| `/estados/{UF}` | `formato=application/vnd.geo+json&qualidade=intermediaria` | Contorno do estado |
| `/estados/{UF}` | `formato=application/vnd.geo+json&intrarregiao=municipio&qualidade=intermediaria` | Municípios do estado |

#### Parâmetros Importantes

| Parâmetro | Valores | Descrição |
|-----------|---------|-----------|
| `formato` | `application/vnd.geo+json` | Formato GeoJSON (obrigatório) |
| `qualidade` | `minima`, `intermediaria`, `maxima` | Resolução dos polígonos |
| `intrarregiao` | `municipio`, `microrregiao`, `mesorregiao` | Subdivisão interna |

#### Exemplo de Resposta - GeoJSON

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "codarea": "4202404",
        "centroide": [-49.0661, -26.9194]
      },
      "geometry": {
        "type": "MultiPolygon",
        "coordinates": [[[[...]]]]
      }
    }
  ]
}
```

#### Estratégia de Ingestão (implementada)

```
1. Buscar lista de estados via API Localidades
2. Para cada estado:
   a. Buscar contorno do estado (sem intrarregiao)
   b. Buscar GeoJSON com intrarregiao=municipio e qualidade=intermediaria
   c. Parsear FeatureCollection
   d. Para cada Feature:
      - Extrair codarea (código IBGE do município)
      - Converter geometry GeoJSON → EWKT (PostGIS)
      - Inserir/atualizar no banco
```

#### Considerações
- **Tamanho:** GeoJSON de todos os municípios de um estado pode ter 5-20 MB
- **Qualidade:** Usar `intermediaria` para balance entre precisão e tamanho
- **Cache recomendado:** 90 dias (fronteiras mudam raramente)
- **Conversão:** GeoJSON → WKT/EWKT feita localmente em Python (sem Shapely para essa operação)

---

### 2.3 API Agregados (Dados Demográficos)

**Base URL:** `https://servicodados.ibge.gov.br/api/v3/agregados/`

**Descrição:** Fornece dados estatísticos de pesquisas e censos do IBGE.

#### Endpoint Utilizado

```
GET /agregados/4714/periodos/2021/variaveis/93
    ?localidades=N6[N3[{codigo_estado}]]
```

Retorna estimativa populacional de todos os municípios de um estado.

#### Exemplo de Resposta

```json
[
  {
    "id": "93",
    "variavel": "População residente estimada",
    "resultados": [
      {
        "series": [
          {
            "localidade": {
              "id": "4202404",
              "nome": "Blumenau"
            },
            "serie": { "2021": "361855" }
          }
        ]
      }
    ]
  }
]
```

#### Implementação

Serviço: `backend/app/services/demographic_ingest.py` → classe `DemographicIngestService`

- `ingest_populacao_estado(uf_sigla, db)` — Ingere dados populacionais + calcula vulnerabilidade
- `_seed_empty_demographics(estado_id, db)` — Cria registros vazios quando a API está indisponível
- `_calculate_vulnerability(demo)` — Calcula índice de vulnerabilidade (0-100)

#### Cálculo do Índice de Vulnerabilidade (implementado)

```python
def _calculate_vulnerability(demo):
    """
    Índice de 0 a 100, onde 100 = máxima vulnerabilidade.
    """
    # Normalizar cada indicador para 0-1
    densidade_norm = min((demo.densidade_demografica or 0) / 10000, 1.0)
    idosos_norm = min((demo.pct_idosos or 0) / 40, 1.0)
    renda_norm = (demo.pct_baixa_renda or 50) / 100  # % abaixo de 1/2 SM
    infra_norm = 1 - (demo.pct_esgoto or 0.5)        # sem esgoto = mais vulnerável

    # Pesos
    indice = (
        densidade_norm * 0.20 +
        idosos_norm * 0.30 +
        renda_norm * 0.30 +
        infra_norm * 0.20
    ) * 100

    return round(min(max(indice, 0), 100), 1)
```

#### Dados Demográficos no Banco

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `populacao` | int | População total estimada |
| `densidade_demografica` | float | hab/km² |
| `pct_idosos` | float | % da população com 60+ anos |
| `pct_baixa_renda` | float | % da população abaixo de 1/2 SM |
| `idh` | float | IDH Municipal |
| `pct_esgoto` | float | % domicílios com rede de esgoto |
| `indice_vulnerabilidade` | float | Calculado (0-100) |
| `ano_referencia` | int | Ano base dos dados |

> **Nota:** Atualmente apenas `populacao` é ingerido via API. Os demais campos (`pct_idosos`, `pct_baixa_renda`, `idh`, `pct_esgoto`) estão no modelo mas precisam de fontes adicionais para preenchimento (Censo 2022, PNUD).

---

## 3. INMET - Instituto Nacional de Meteorologia

### 3.1 API de Dados Meteorológicos

**Base URL:** `https://apitempo.inmet.gov.br/`

**Descrição:** Dados de estações meteorológicas automáticas em todo o Brasil.

#### Endpoints Utilizados

| Endpoint | Descrição |
|----------|-----------|
| `/estacoes/T` | Lista todas as estações automáticas |
| `/estacao/dados/{data_inicio}/{data_fim}/{codigo}` | Dados horários de uma estação no período |

#### Exemplo de Resposta - Lista de Estações

```json
[
  {
    "CD_ESTACAO": "A803",
    "DC_NOME": "BLUMENAU",
    "SG_ESTADO": "SC",
    "VL_LATITUDE": "-26.909722",
    "VL_LONGITUDE": "-49.071389",
    "VL_ALTITUDE": "21.08",
    "DT_INICIO_OPERACAO": "2001-03-21",
    "CD_SITUACAO": "Operante",
    "TP_ESTACAO": "Automatica"
  }
]
```

#### Exemplo de Resposta - Dados Horários

```json
[
  {
    "CD_ESTACAO": "A803",
    "DT_MEDICAO": "2024-01-15",
    "HR_MEDICAO": "1200 UTC",
    "TEM_INS": "28.4",
    "TEM_MAX": "29.1",
    "TEM_MIN": "27.8",
    "UMD_INS": "72",
    "CHUVA": "2.4",
    "VEN_VEL": "3.2",
    "VEN_DIR": "180",
    "PRE_INS": "1012.3",
    "RAD_GLO": "850"
  }
]
```

#### Variáveis Meteorológicas

| Campo API | Campo no Banco | Unidade | Uso no Sistema |
|-----------|---------------|---------|----------------|
| `TEM_INS` | `temperatura` | °C | Monitoramento |
| `TEM_MAX` | `temperatura_max` | °C | Regra de calor extremo |
| `TEM_MIN` | `temperatura_min` | °C | Monitoramento |
| `CHUVA` | `precipitacao` | mm | Regra de inundação / seca |
| `UMD_INS` | `umidade` | % | Monitoramento |
| `VEN_VEL` | `vento_velocidade` | m/s | Regra de vendaval |
| `VEN_DIR` | `vento_direcao` | graus | Contexto |
| `PRE_INS` | `pressao` | hPa | Monitoramento |
| `RAD_GLO` | `radiacao` | W/m² | Monitoramento |

#### Implementação

Serviço: `backend/app/services/inmet_ingest.py` → classe `INMETIngestService`

- `ingest_estacoes(db)` — Ingere lista de estações automáticas operantes
- `ingest_medicoes_recentes(db, horas=24)` — Ingere medições das últimas N horas

**Associação Estação → Município:** Feita por proximidade geoespacial usando `ST_Distance` no PostGIS (encontra o município com geometria mais próxima da coordenada da estação).

#### Considerações
- **Rate limit:** Não documentado oficialmente; implementado retry com backoff (3 tentativas)
- **Disponibilidade:** Média (pode ter instabilidades — erros RemoteProtocolError são comuns)
- **Dados faltantes:** Estações podem não reportar em certas horas
- **Timezone:** Dados em UTC
- **Deduplicação:** Verificação por `(estacao_id, data_hora)` antes de inserir

---

## 4. ANA - Agência Nacional de Águas e Saneamento Básico

### 4.1 Web Service SOAP (Telemetria)

**URL:** `http://telemetriaws1.ana.gov.br/ServiceANA.asmx`

**Descrição:** Dados hidrológicos de estações fluviométricas em tempo real via protocolo SOAP.

#### Operações Utilizadas

| Operação SOAP | SOAPAction | Descrição |
|---------------|------------|-----------|
| `HidroInventario` | `http://ana.gov.br/HidroInventario` | Lista estações com metadados e limiares |
| `DadosHidroTelemetria` | `http://ana.gov.br/DadosHidroTelemetria` | Dados em tempo real (nível, vazão, chuva) |

#### Request - HidroInventario

```xml
<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <HidroInventario xmlns="http://ana.gov.br/">
      <codEstDE></codEstDE>
      <codEstATE></codEstATE>
      <tpEst>1</tpEst>           <!-- 1=Fluviométrica, 2=Pluviométrica -->
      <nmEst></nmEst>
      <nmRio></nmRio>
      <codSubBacia></codSubBacia>
      <codBacia></codBacia>
      <nmMunicipio></nmMunicipio>
      <nmEstado>Santa Catarina</nmEstado>
      <sgResp></sgResp>
      <sgOper></sgOper>
      <telession>1</telession>   <!-- 1=apenas estações com telemetria -->
    </HidroInventario>
  </soap:Body>
</soap:Envelope>
```

#### Request - DadosHidroTelemetria

```xml
<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <DadosHidroTelemetria xmlns="http://ana.gov.br/">
      <codEstacao>83680000</codEstacao>
      <dataInicio>15/01/2024</dataInicio>  <!-- formato DD/MM/YYYY -->
      <dataFim>15/01/2024</dataFim>
    </DadosHidroTelemetria>
  </soap:Body>
</soap:Envelope>
```

#### Campos do Inventário (utilizados)

| Campo XML | Campo no Banco | Descrição |
|-----------|---------------|-----------|
| `Codigo` / `CodEstacao` | `codigo_ana` | Código único da estação |
| `Nome` / `NomeEstacao` | `nome` | Nome da estação |
| `Latitude` | coordenada | Latitude |
| `Longitude` | coordenada | Longitude |
| `RioNome` / `NomeRio` | `rio_nome` | Nome do rio |
| `BaciaCodigo` | `bacia` | Código da bacia hidrográfica |
| `SubBaciaCodigo` | `sub_bacia` | Código da sub-bacia |
| `NivelAtencao` | `nivel_atencao` | Cota de atenção (metros) |
| `NivelAlerta` | `nivel_alerta` | Cota de alerta (metros) |
| `NivelEmergencia` / `NivelInundacao` | `nivel_emergencia` | Cota de emergência (metros) |
| `StatusEstacao` | `ativa` | Status (1=ativa) |

#### Campos da Telemetria (utilizados)

| Campo XML | Campo no Banco | Unidade | Uso no Motor de Regras |
|-----------|---------------|---------|------------------------|
| `DataHora` | `data_hora` | timestamp | Referência temporal |
| `Nivel` | `nivel` | metros (cota) | Comparação com limiares |
| `Vazao` | `vazao` | m³/s | Monitoramento |
| `Chuva` | `chuva` | mm | Complemento ao INMET |

#### Implementação

Serviço: `backend/app/services/ana_ingest.py` → classes `ANAClient` + `ANAIngestService`

- `ingest_estacoes(db, estado, tipo)` — Ingere inventário de estações (filtro por estado/tipo)
- `ingest_telemetria_recente(db, horas=6)` — Ingere telemetria das últimas N horas de estações ativas

**Parsing:** Usa `xmltodict` para converter XML SOAP → dicionário Python (mais simples que bibliotecas SOAP completas como `zeep`).

**Rate limiting:** Delay de 0.5s entre requests de telemetria para não sobrecarregar o serviço.

#### Limiares de Alerta (por estação)

Cada estação hidrológica possui limiares definidos pela ANA:

| Nível | Significado | Ação no Sistema |
|-------|-------------|-----------------|
| **Atenção** | Nível do rio atingiu cota de vigilância | Regra `river_level_attention` → severidade moderado |
| **Alerta** | Nível do rio em cota de risco | Regra `river_level_alert` → severidade alto |
| **Emergência** | Nível do rio em cota de transbordamento | Regra `river_level_emergency` → severidade critico |

O motor de regras também detecta **subida rápida** (variação > 0.5m em 6h) como indicador de risco alto.

#### Considerações
- **Disponibilidade:** Variável (web service legado pode ter instabilidades)
- **Retry:** 3 tentativas com backoff (3s, 6s, 9s)
- **Cobertura:** Nem todos os rios/bacias têm telemetria ativa
- **Limiares:** Vêm do próprio inventário da ANA (campos `NivelAtencao`, `NivelAlerta`, `NivelEmergencia`)
- **Formato de data:** DD/MM/YYYY para telemetria (diferente do padrão ISO)

---

## 5. Estratégia de Ingestão

### 5.1 Fluxo Atual (Manual)

Toda ingestão é disparada via endpoints REST:

```
POST /api/v1/ingest/setup-db              → Cria tabelas (setup inicial)
POST /api/v1/ingest/ibge?uf={UF}          → Dados geográficos
POST /api/v1/ingest/inmet?readings=true   → Estações + medições INMET
POST /api/v1/ingest/demographics?state={UF} → Dados demográficos
POST /api/v1/ingest/ana?readings=true&estado={nome} → Estações + telemetria ANA
POST /api/v1/alerts/process?state={UF}    → Recalcula risco e gera alertas
```

**Ordem recomendada para setup inicial:**
1. `setup-db` — Criar tabelas
2. `ibge` — Carregar estados e municípios (sem param = todos)
3. `inmet` — Carregar estações meteorológicas
4. `ana` — Carregar estações hidrológicas
5. `demographics?state=SC` — Dados demográficos por estado
6. `inmet?readings=true` — Carregar medições recentes
7. `ana?readings=true` — Carregar telemetria recente
8. `alerts/process?state=SC` — Gerar alertas

### 5.2 Frequências Planejadas (futuro com APScheduler)

| Fonte | Frequência | Descrição |
|-------|-----------|-----------|
| IBGE Localidades | Sob demanda | Seed inicial, dados estáticos |
| IBGE Demográficos | Mensal | Dados mudam raramente |
| INMET Estações | Diária | Atualizar lista de estações |
| INMET Medições | Horária | Dados meteorológicos |
| ANA Estações | Semanal | Atualizar inventário |
| ANA Telemetria | A cada 2h | Dados hidrológicos (configurável via `ANA_INGEST_INTERVAL_HOURS`) |
| Recálculo de Risco | Após cada ingestão | Disparar processamento de alertas |

### 5.3 Tratamento de Erros

| Cenário | Comportamento Implementado |
|---------|---------------------------|
| API indisponível | Retry com backoff (3 tentativas) |
| API IBGE Agregados indisponível | Cria registros demográficos vazios (graceful fallback) |
| Dados inválidos | Rejeitar registro individual, continuar processamento |
| Timeout | Configurável por serviço (30-120s) |
| Rate limit (INMET/ANA) | Delay entre requests |
| Estação sem coordenadas | Skip (não inserir) |
| Município não encontrado | Skip (log warning) |

---

## 6. Mapeamento de Dados para o Modelo

### 6.1 IBGE → Tabelas Geográficas

```
API Localidades /estados       →  tabela: estados (codigo_ibge, nome, sigla, regiao)
API Localidades /municipios    →  tabela: municipios (codigo_ibge, nome, estado_id)
API Malhas /estados/{UF}       →  tabela: estados.geometria (MultiPolygon EWKT)
API Malhas /estados/{UF}?intra →  tabela: municipios.geometria (MultiPolygon EWKT)
API Agregados /4714            →  tabela: dados_demograficos.populacao
```

### 6.2 INMET → Tabelas Meteorológicas

```
/estacoes/T                    →  tabela: estacoes_meteorologicas
  CD_ESTACAO                   →  codigo_inmet
  DC_NOME                      →  nome
  VL_LATITUDE + VL_LONGITUDE   →  coordenada (SRID=4326;POINT(lon lat))
  VL_ALTITUDE                  →  altitude
  TP_ESTACAO                   →  tipo
  CD_SITUACAO == "Operante"    →  ativa = true
  municipio mais próximo       →  municipio_id (via ST_Distance)

/estacao/dados/{inicio}/{fim}  →  tabela: medicoes_climaticas
  DT_MEDICAO + HR_MEDICAO     →  data_hora (UTC)
  TEM_INS                      →  temperatura
  TEM_MAX                      →  temperatura_max
  TEM_MIN                      →  temperatura_min
  CHUVA                        →  precipitacao
  UMD_INS                      →  umidade
  VEN_VEL                      →  vento_velocidade
  VEN_DIR                      →  vento_direcao
  PRE_INS                      →  pressao
  RAD_GLO                      →  radiacao
```

### 6.3 ANA → Tabelas Hidrológicas

```
HidroInventario                →  tabela: estacoes_hidrologicas
  Codigo/CodEstacao            →  codigo_ana
  Nome/NomeEstacao             →  nome
  Latitude + Longitude         →  coordenada (SRID=4326;POINT(lon lat))
  RioNome/NomeRio              →  rio_nome
  BaciaCodigo                  →  bacia
  SubBaciaCodigo               →  sub_bacia
  NivelAtencao                 →  nivel_atencao
  NivelAlerta                  →  nivel_alerta
  NivelEmergencia/NivelInundacao → nivel_emergencia
  StatusEstacao == "1"         →  ativa = true
  municipio mais próximo       →  municipio_id (via ST_Distance)

DadosHidroTelemetria           →  tabela: medicoes_hidrologicas
  DataHora                     →  data_hora (parsed de string)
  Nivel                        →  nivel (metros)
  Vazao                        →  vazao (m³/s)
  Chuva                        →  chuva (mm)
```

---

## 7. Limitações Conhecidas

| Fonte | Limitação | Impacto | Mitigação |
|-------|-----------|---------|-----------|
| IBGE | Dados censitários antigos | Vulnerabilidade baseada em estimativas 2021 | Atualizar quando Censo 2022 estiver completo |
| IBGE Agregados | API pode estar indisponível | Dados demográficos ficam vazios | Fallback com registros vazios (continua operacional) |
| INMET | ~600 estações para 5.570 municípios | Muitos municípios sem estação própria | Usa estação mais próxima (via geoespacial) |
| INMET | Dados faltantes em estações | Gaps nas séries temporais | Dedup por (estacao, data_hora); usa última medição válida |
| INMET | Instabilidades na API | Erros de protocolo/timeout | Retry com backoff (3 tentativas) |
| ANA | Web service SOAP legado | Parsing XML mais complexo | Usa `xmltodict` (leve, sem dependências SOAP pesadas) |
| ANA | Limiares nem sempre disponíveis | Sem limiares = sem detecção de nível | Motor de regras verifica `nivel > 0` antes de calcular % |
| ANA | Nem todas as estações têm telemetria | Cobertura limitada em alguns rios | Filtro `telession=1` no inventário |
| Todas | Sem SLA garantido (serviços públicos) | Possível indisponibilidade | Graceful degradation + logs informativos |
| Geral | Scheduler não implementado | Ingestão precisa ser manual | Endpoints POST disponíveis; APScheduler planejado |

---

## 8. Configuração

Variáveis de ambiente relevantes para ingestão:

| Variável | Default | Descrição |
|----------|---------|-----------|
| `INMET_BASE_URL` | `https://apitempo.inmet.gov.br` | Base URL da API INMET |
| `IBGE_BASE_URL` | `https://servicodados.ibge.gov.br` | Base URL da API IBGE |
| `ANA_TELEMETRIA_URL` | `http://telemetriaws1.ana.gov.br/ServiceANA.asmx` | Web service SOAP da ANA |
| `ANA_INGEST_INTERVAL_HOURS` | `2` | Intervalo planejado para ingestão automática ANA |

---

*Documento atualizado em: Agosto 2026*
*Versão: 2.0*
