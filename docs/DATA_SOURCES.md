# Fontes de Dados - AlertaBR

## Plataforma de Prevenção a Desastres Naturais

---

## 1. Visão Geral das Fontes

O AlertaBR consome dados de três fontes públicas principais, todas gratuitas e sem necessidade de autenticação:

| Fonte | Tipo de Dado | Frequência de Atualização | Uso no Sistema |
|-------|-------------|---------------------------|----------------|
| **IBGE** | Geográfico + Demográfico | Sob demanda (dados estáticos) | Geometrias, população, vulnerabilidade |
| **INMET** | Meteorológico | Horária (estações automáticas) | Precipitação, temperatura, umidade |
| **ANA** | Hidrológico | Horária a diária | Nível de rios, vazão |

---

## 2. IBGE - Instituto Brasileiro de Geografia e Estatística

### 2.1 API Localidades

**Base URL:** `https://servicodados.ibge.gov.br/api/v1/localidades/`

**Descrição:** Fornece a estrutura político-administrativa do Brasil com hierarquia completa.

#### Endpoints Utilizados

| Endpoint | Retorno | Uso |
|----------|---------|-----|
| `/estados` | Lista de 27 UFs | Popular tabela `estados` |
| `/estados/{UF}` | Detalhes de um estado | Dados complementares |
| `/estados/{UF}/municipios` | Municípios de um estado | Popular tabela `municipios` |
| `/municipios` | Todos os 5.570 municípios | Carga completa |
| `/mesorregioes` | Mesorregiões | Agrupamento regional |
| `/microrregioes` | Microrregiões | Agrupamento sub-regional |

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
| `/paises/BR` | `formato=application/vnd.geo+json` | Contorno do Brasil |
| `/estados/{UF}` | `formato=application/vnd.geo+json&qualidade=minima` | Contorno do estado |
| `/estados/{UF}` | `formato=application/vnd.geo+json&intrarregiao=municipio` | Municípios do estado |
| `/municipios/{codigo}` | `formato=application/vnd.geo+json` | Contorno de um município |

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

#### Estratégia de Ingestão

```
1. Buscar lista de estados via API Localidades
2. Para cada estado:
   a. Buscar GeoJSON com intrarregiao=municipio e qualidade=intermediaria
   b. Parsear FeatureCollection
   c. Para cada Feature:
      - Extrair codarea (código IBGE do município)
      - Extrair geometry (MultiPolygon)
      - Inserir/atualizar no PostGIS
3. Criar índice GiST na coluna de geometria
```

#### Considerações
- **Tamanho:** GeoJSON de todos os municípios de um estado pode ter 5-20 MB
- **Qualidade:** Usar `intermediaria` para balance entre precisão e tamanho
- **Cache recomendado:** 90 dias (fronteiras mudam raramente)
- **Simplificação:** Para renderização no frontend, aplicar ST_Simplify no PostGIS

---

### 2.3 API Agregados (Dados Demográficos)

**Base URL:** `https://servicodados.ibge.gov.br/api/v3/agregados/`

**Descrição:** Fornece dados estatísticos de pesquisas e censos do IBGE.

#### Agregados Utilizados

| Código | Pesquisa | Variáveis Relevantes |
|--------|----------|---------------------|
| `4714` | Estimativa de População | População total por município |
| `1301` | Censo Demográfico | Faixa etária, renda |
| `3548` | PIB Municipal | PIB per capita |
| `5938` | Censo - Características | Domicílios, saneamento |

#### Endpoints

```
GET /agregados/{agregado}/periodos/{periodo}/variaveis/{variavel}
    ?localidades=N6[{codigo_municipio}]
    &classificacao={classificacao}[{categoria}]
```

#### Exemplo - População por Município

```
GET /agregados/4714/periodos/2021/variaveis/93?localidades=N6[4202404]
```

```json
[
  {
    "id": "93",
    "variavel": "População residente estimada",
    "resultados": [
      {
        "classificacoes": [],
        "series": [
          {
            "localidade": {
              "id": "4202404",
              "nome": "Blumenau",
              "nivel": { "id": "N6", "nome": "Município" }
            },
            "serie": { "2021": "361855" }
          }
        ]
      }
    ]
  }
]
```

#### Dados Demográficos para Vulnerabilidade

| Dado | Agregado | Variável | Uso no Índice |
|------|----------|----------|---------------|
| População total | 4714 | 93 | Densidade demográfica |
| % idosos (60+) | 1301 | 93 + classificação | Vulnerabilidade etária |
| Renda domiciliar | 1301 | 842 | Vulnerabilidade econômica |
| Domicílios com esgoto | 5938 | 220 | Infraestrutura |
| IDH Municipal | - | - | Via PNUD (fonte complementar) |

#### Cálculo do Índice de Vulnerabilidade

```python
def calcular_vulnerabilidade(municipio_data):
    """
    Índice de 0 a 100, onde 100 = máxima vulnerabilidade
    """
    # Normalizar cada indicador para 0-1
    densidade_norm = min(municipio_data.densidade / 10000, 1.0)  # > 10k hab/km² = 1
    idosos_norm = municipio_data.pct_idosos / 40  # > 40% idosos = 1
    renda_norm = 1 - min(municipio_data.renda_per_capita / 3000, 1.0)  # < R$0 = 1
    infra_norm = 1 - municipio_data.pct_esgoto  # sem esgoto = 1
    
    # Pesos
    indice = (
        densidade_norm * 0.20 +
        idosos_norm * 0.30 +
        renda_norm * 0.30 +
        infra_norm * 0.20
    ) * 100
    
    return round(indice, 1)
```

---

## 3. INMET - Instituto Nacional de Meteorologia

### 3.1 API de Dados Meteorológicos

**Base URL:** `https://apitempo.inmet.gov.br/`

**Descrição:** Dados de estações meteorológicas automáticas e convencionais em todo o Brasil.

#### Endpoints Utilizados

| Endpoint | Descrição | Frequência |
|----------|-----------|------------|
| `/estacoes/T` | Lista estações automáticas | Sob demanda |
| `/estacoes/M` | Lista estações convencionais | Sob demanda |
| `/estacao/dados/{data_inicio}/{data_fim}/{codigo}` | Dados horários de uma estação | Horária |
| `/estacao/{frequencia}/{data_inicio}/{data_fim}/{codigo}` | Dados por frequência | Configurável |

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
    "UMD_MAX": "78",
    "UMD_MIN": "68",
    "CHUVA": "2.4",
    "VEN_VEL": "3.2",
    "VEN_DIR": "180",
    "PRE_INS": "1012.3",
    "RAD_GLO": "850"
  }
]
```

#### Variáveis Meteorológicas

| Campo | Unidade | Descrição | Uso no Sistema |
|-------|---------|-----------|----------------|
| `TEM_INS` | °C | Temperatura instantânea | Regra de calor extremo |
| `TEM_MAX` | °C | Temperatura máxima (hora) | Alerta de saúde |
| `CHUVA` | mm | Precipitação acumulada (hora) | Regra de inundação |
| `UMD_INS` | % | Umidade relativa | Risco de incêndio |
| `VEN_VEL` | m/s | Velocidade do vento | Alerta de vendaval |
| `VEN_DIR` | graus | Direção do vento | Contexto |
| `PRE_INS` | hPa | Pressão atmosférica | Tendência meteorológica |

#### Estratégia de Ingestão

```
Frequência: A cada 1 hora
Processo:
1. Buscar lista de estações operantes (cache 24h)
2. Para cada estação:
   a. Buscar dados das últimas 2h (overlap para garantir completude)
   b. Verificar se dado já existe (dedup por estação + data_hora)
   c. Inserir novas medições no PostgreSQL
3. Após ingestão completa:
   a. Disparar recalculação de risco para municípios afetados
   b. Invalidar cache Redis dos municípios atualizados
```

#### Associação Estação → Município

```sql
-- Encontrar município mais próximo da estação
SELECT m.id, m.nome, 
       ST_Distance(
         m.geometria::geography, 
         ST_SetSRID(ST_MakePoint(estacao.longitude, estacao.latitude), 4326)::geography
       ) as distancia_metros
FROM municipios m
ORDER BY m.geometria <-> ST_SetSRID(ST_MakePoint(-49.071, -26.909), 4326)
LIMIT 1;
```

#### Considerações
- **Rate limit:** Não documentado oficialmente; recomenda-se 5 req/s
- **Disponibilidade:** Média (pode ter instabilidades)
- **Dados faltantes:** Estações podem não reportar em certas horas
- **Timezone:** Dados em UTC, converter para horário de Brasília
- **Backfill:** Possível buscar dados históricos por data
- **Fallback:** Se API indisponível, usar último dado em cache

---

## 4. ANA - Agência Nacional de Águas e Saneamento Básico

### 4.1 HidroWeb / SNIRH

**Portal:** `https://www.snirh.gov.br/hidroweb/`

**Descrição:** Dados hidrológicos de estações fluviométricas e pluviométricas em todo o Brasil.

#### Dados Disponíveis

| Tipo | Variáveis | Uso |
|------|-----------|-----|
| **Fluviométrica** | Nível do rio (cota), vazão | Risco de cheias |
| **Pluviométrica** | Precipitação diária/horária | Complemento ao INMET |
| **Sedimentométrica** | Sedimentos em suspensão | Contexto (v2) |

#### Acesso aos Dados

A ANA oferece dados via:

1. **Web service SOAP** (legado): `http://telemetriaws1.ana.gov.br/ServiceANA.asmx`
2. **API REST** (mais recente): via portal SNIRH
3. **Download de séries** (CSV/XML): via HidroWeb

#### Endpoints Web Service (SOAP)

| Operação | Descrição |
|----------|-----------|
| `HidroInventario` | Lista estações com metadados |
| `HidroSerieHistorica` | Série histórica de uma estação |
| `DadosHidroTelemetria` | Dados em tempo real (telemetria) |

#### Exemplo - Consulta Telemetria

```xml
<soap:Body>
  <DadosHidroTelemetria>
    <codEstacao>83680000</codEstacao>
    <dataInicio>2024-01-01</dataInicio>
    <dataFim>2024-01-15</dataFim>
  </DadosHidroTelemetria>
</soap:Body>
```

#### Resposta (simplificada)

```xml
<DadosTelemetria>
  <Estacao Codigo="83680000" Nome="BLUMENAU" RioNome="RIO ITAJAÍ-AÇU">
    <Dado>
      <DataHora>2024-01-15T12:00:00</DataHora>
      <Nivel>2.45</Nivel>
      <Vazao>185.3</Vazao>
      <Chuva>0.2</Chuva>
    </Dado>
  </Estacao>
</DadosTelemetria>
```

#### Variáveis Hidrológicas

| Campo | Unidade | Descrição | Limiar de Alerta |
|-------|---------|-----------|------------------|
| Nível (cota) | metros | Nível do rio na seção | Varia por estação |
| Vazão | m³/s | Volume de água por segundo | Varia por rio |
| Chuva | mm | Precipitação na bacia | > 50mm/24h |

#### Estratégia de Ingestão

```
Frequência: A cada 2 horas (dados de telemetria)
Processo:
1. Consultar estações de telemetria ativas (cache 7 dias)
2. Para cada estação em bacia monitorada:
   a. Buscar dados de telemetria das últimas 3h
   b. Calcular variação de nível (tendência)
   c. Inserir no PostgreSQL
3. Cruzar com limiares por estação:
   - Nível atenção: definido pela ANA por estação
   - Nível alerta: definido pela ANA por estação
   - Nível emergência: definido pela ANA por estação
```

#### Considerações
- **Complexidade:** API SOAP requer cliente específico (zeep/suds)
- **Disponibilidade:** Variável, dados de telemetria podem atrasar
- **Cobertura:** Nem todos os rios/bacias têm telemetria
- **Limiares:** Cada estação tem limiares próprios definidos pela ANA
- **Prioridade:** Implementar na v1 com subset de estações prioritárias (grandes rios)
- **Alternativa REST:** Avaliar disponibilidade de API REST mais moderna

---

## 5. Estratégia Geral de Ingestão

### 5.1 Frequências

```
┌─────────────────────────────────────────────────────────────┐
│               AGENDA DE INGESTÃO                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  IBGE Localidades     ──── Sob demanda (seed inicial)      │
│  IBGE Malhas          ──── Sob demanda (seed inicial)      │
│  IBGE Demográficos    ──── Mensal (dados mudam raramente)  │
│  INMET Estações       ──── Diária (lista de estações)      │
│  INMET Medições       ──── Horária (dados meteorológicos)  │
│  ANA Telemetria       ──── A cada 2h (dados hidrológicos)  │
│  Recálculo de Risco   ──── Após cada ingestão INMET/ANA   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Tratamento de Erros

| Cenário | Comportamento |
|---------|---------------|
| API indisponível | Retry com backoff exponencial (3 tentativas) |
| Dados parciais | Ingerir o que está disponível, logar gaps |
| Dados inválidos | Rejeitar registro, logar para revisão |
| Timeout | Retry após 30s, máximo 3 tentativas |
| Rate limit | Backoff de 60s, reduzir concorrência |

### 5.3 Pipeline de Dados

```
Fonte Externa → HTTP Client → Validação → Transformação → PostgreSQL → Trigger Risco
                    │                                          │
                    └── Retry/Backoff                          └── Invalidar Cache Redis
```

### 5.4 Monitoramento

Métricas a rastrear por fonte:
- Última ingestão bem-sucedida (timestamp)
- Número de registros ingeridos por execução
- Tempo de execução da ingestão
- Taxa de erros/rejeições
- Cobertura (% de estações com dados atualizados)

---

## 6. Mapeamento de Dados para o Modelo

### 6.1 IBGE → Tabelas Geográficas

```
API Localidades /estados       →  tabela: estados (id, codigo_ibge, nome, sigla)
API Localidades /municipios    →  tabela: municipios (id, codigo_ibge, nome, estado_id)
API Malhas /estados/{UF}       →  tabela: estados.geometria (MultiPolygon)
API Malhas /estados/{UF}?intra →  tabela: municipios.geometria (MultiPolygon)
API Agregados /4714            →  tabela: dados_demograficos.populacao
```

### 6.2 INMET → Tabelas Meteorológicas

```
/estacoes/T                    →  tabela: estacoes_meteorologicas
  CD_ESTACAO                   →  codigo_inmet
  DC_NOME                      →  nome
  VL_LATITUDE + VL_LONGITUDE   →  coordenada (Point, SRID 4326)
  
/estacao/dados/{inicio}/{fim}  →  tabela: medicoes_climaticas
  DT_MEDICAO + HR_MEDICAO     →  data_hora (timestamp with timezone)
  TEM_INS                      →  temperatura
  CHUVA                        →  precipitacao
  UMD_INS                      →  umidade
  VEN_VEL                      →  vento_velocidade
  VEN_DIR                      →  vento_direcao
```

### 6.3 ANA → Tabelas Hidrológicas (extensão futura)

```
HidroInventario                →  tabela: estacoes_hidrologicas
  Codigo                       →  codigo_ana
  NomeEstacao                  →  nome
  Latitude + Longitude         →  coordenada (Point)
  
DadosHidroTelemetria           →  tabela: medicoes_hidrologicas
  DataHora                     →  data_hora
  Nivel                        →  nivel_metros
  Vazao                        →  vazao_m3s
  Chuva                        →  precipitacao
```

---

## 7. Limitações Conhecidas

| Fonte | Limitação | Impacto | Mitigação |
|-------|-----------|---------|-----------|
| IBGE | Dados censitários desatualizados (Censo 2022) | Vulnerabilidade pode não refletir realidade | Usar estimativas populacionais mais recentes |
| INMET | ~600 estações para 5.570 municípios | Muitos municípios sem estação própria | Interpolar dados da estação mais próxima |
| INMET | Dados faltantes em estações | Gaps nas séries temporais | Usar última medição válida + flag de qualidade |
| ANA | API SOAP complexa | Maior esforço de integração | Considerar biblioteca zeep, implementar na v1.1 |
| ANA | Limiares por estação não padronizados | Configuração manual necessária | Usar limiares genéricos + permitir override |
| Todas | Sem SLA garantido (serviços públicos) | Possível indisponibilidade | Cache agressivo + graceful degradation |

---

*Documento gerado em: Julho 2026*  
*Versão: 1.0*
