"""Motor de regras para cálculo de risco por município."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.geographic import Municipio
from app.models.weather import EstacaoMeteorologica, MedicaoClimatica
from app.models.demographic import DadosDemograficos

logger = logging.getLogger(__name__)


# Configuração de regras
RISK_RULES = [
    {
        "id": "flood_24h",
        "name": "Risco de Inundação (24h)",
        "type": "inundacao",
        "metric": "precipitacao_acumulada_24h",
        "operator": ">",
        "threshold": 80,
        "severity": "alto",
        "weight": 0.4,
    },
    {
        "id": "flood_72h_critical",
        "name": "Risco Crítico de Inundação (72h)",
        "type": "inundacao",
        "metric": "precipitacao_acumulada_72h",
        "operator": ">",
        "threshold": 150,
        "geographic_condition": "em_vale",
        "severity": "critico",
        "weight": 0.5,
    },
    {
        "id": "heat_health",
        "name": "Risco de Saúde - Calor Extremo",
        "type": "calor",
        "metric": "temperatura_maxima",
        "operator": ">",
        "threshold": 40,
        "demographic_condition": {"field": "pct_idosos", "operator": ">", "value": 20},
        "severity": "alto",
        "weight": 0.3,
    },
    {
        "id": "drought_30d",
        "name": "Risco de Seca",
        "type": "seca",
        "metric": "precipitacao_acumulada_30d",
        "operator": "<",
        "threshold": 10,
        "severity": "alto",
        "weight": 0.3,
    },
    {
        "id": "wind_alert",
        "name": "Alerta de Vendaval",
        "type": "vendaval",
        "metric": "vento_velocidade_max",
        "operator": ">",
        "threshold": 20,
        "severity": "moderado",
        "weight": 0.2,
    },
]


@dataclass
class WeatherMetrics:
    """Métricas climáticas calculadas para um município."""

    precipitacao_acumulada_24h: float = 0.0
    precipitacao_acumulada_72h: float = 0.0
    precipitacao_acumulada_30d: float = 0.0
    temperatura_maxima: float = 0.0
    vento_velocidade_max: float = 0.0
    umidade_minima: float = 100.0


@dataclass
class RiskResult:
    """Resultado do cálculo de risco."""

    municipio_id: int
    index: float = 0.0
    classification: str = "baixo"
    triggered_rules: List[str] = field(default_factory=list)
    primary_type: str = "indefinido"
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class RiskEngine:
    """Motor de regras para avaliação de risco climático."""

    def __init__(self, rules: List[Dict] = None):
        self.rules = rules or RISK_RULES

    async def calculate_risk(
        self, municipio_id: int, db: AsyncSession
    ) -> RiskResult:
        """Calcula índice de risco composto para um município."""
        # 1. Buscar métricas climáticas
        weather = await self._get_weather_metrics(municipio_id, db)

        # 2. Buscar dados geográficos
        municipio = await db.get(Municipio, municipio_id)
        if not municipio:
            return RiskResult(municipio_id=municipio_id)

        # 3. Buscar dados demográficos
        demo_result = await db.execute(
            select(DadosDemograficos).where(
                DadosDemograficos.municipio_id == municipio_id
            )
        )
        demographics = demo_result.scalar_one_or_none()

        # 4. Avaliar cada regra
        triggered_rules = []
        for rule in self.rules:
            if self._evaluate_rule(rule, weather, municipio, demographics):
                triggered_rules.append(rule)

        # 5. Calcular índice composto
        risk_index = self._compute_index(triggered_rules, demographics)

        # 6. Classificar
        classification = self._classify(risk_index)

        # 7. Determinar tipo de risco primário
        primary_type = "indefinido"
        if triggered_rules:
            # Maior peso = tipo primário
            primary_type = max(triggered_rules, key=lambda r: r["weight"])["type"]

        return RiskResult(
            municipio_id=municipio_id,
            index=risk_index,
            classification=classification,
            triggered_rules=[r["id"] for r in triggered_rules],
            primary_type=primary_type,
        )

    async def calculate_risk_map(
        self, state_sigla: str, db: AsyncSession
    ) -> List[Dict]:
        """Calcula risco para todos os municípios de um estado."""
        from app.models.geographic import Estado

        result = await db.execute(
            select(Estado).where(Estado.sigla == state_sigla.upper())
        )
        estado = result.scalar_one_or_none()
        if not estado:
            return []

        result = await db.execute(
            select(Municipio.id, Municipio.nome, Municipio.codigo_ibge).where(
                Municipio.estado_id == estado.id
            )
        )
        municipios = result.all()

        risks = []
        for mun in municipios:
            risk = await self.calculate_risk(mun.id, db)
            risks.append({
                "municipio_id": mun.id,
                "codigo_ibge": mun.codigo_ibge,
                "nome": mun.nome,
                "risk_index": risk.index,
                "classification": risk.classification,
                "triggered_rules": risk.triggered_rules,
                "primary_type": risk.primary_type,
            })

        return risks

    async def _get_weather_metrics(
        self, municipio_id: int, db: AsyncSession
    ) -> WeatherMetrics:
        """Calcula métricas climáticas a partir de medições recentes."""
        now = datetime.now(timezone.utc)

        # Buscar estações do município
        result = await db.execute(
            select(EstacaoMeteorologica.id).where(
                EstacaoMeteorologica.municipio_id == municipio_id,
                EstacaoMeteorologica.ativa == True,
            )
        )
        estacao_ids = [row[0] for row in result.all()]

        if not estacao_ids:
            return WeatherMetrics()

        metrics = WeatherMetrics()

        # Precipitação acumulada 24h
        result = await db.execute(
            select(func.coalesce(func.sum(MedicaoClimatica.precipitacao), 0)).where(
                MedicaoClimatica.estacao_id.in_(estacao_ids),
                MedicaoClimatica.data_hora >= now - timedelta(hours=24),
                MedicaoClimatica.precipitacao.isnot(None),
            )
        )
        metrics.precipitacao_acumulada_24h = float(result.scalar() or 0)

        # Precipitação acumulada 72h
        result = await db.execute(
            select(func.coalesce(func.sum(MedicaoClimatica.precipitacao), 0)).where(
                MedicaoClimatica.estacao_id.in_(estacao_ids),
                MedicaoClimatica.data_hora >= now - timedelta(hours=72),
                MedicaoClimatica.precipitacao.isnot(None),
            )
        )
        metrics.precipitacao_acumulada_72h = float(result.scalar() or 0)

        # Precipitação acumulada 30d
        result = await db.execute(
            select(func.coalesce(func.sum(MedicaoClimatica.precipitacao), 0)).where(
                MedicaoClimatica.estacao_id.in_(estacao_ids),
                MedicaoClimatica.data_hora >= now - timedelta(days=30),
                MedicaoClimatica.precipitacao.isnot(None),
            )
        )
        metrics.precipitacao_acumulada_30d = float(result.scalar() or 0)

        # Temperatura máxima (últimas 24h)
        result = await db.execute(
            select(func.max(MedicaoClimatica.temperatura_max)).where(
                MedicaoClimatica.estacao_id.in_(estacao_ids),
                MedicaoClimatica.data_hora >= now - timedelta(hours=24),
                MedicaoClimatica.temperatura_max.isnot(None),
            )
        )
        metrics.temperatura_maxima = float(result.scalar() or 0)

        # Velocidade máxima do vento (últimas 24h)
        result = await db.execute(
            select(func.max(MedicaoClimatica.vento_velocidade)).where(
                MedicaoClimatica.estacao_id.in_(estacao_ids),
                MedicaoClimatica.data_hora >= now - timedelta(hours=24),
                MedicaoClimatica.vento_velocidade.isnot(None),
            )
        )
        metrics.vento_velocidade_max = float(result.scalar() or 0)

        return metrics

    def _evaluate_rule(
        self,
        rule: Dict,
        weather: WeatherMetrics,
        municipio: Municipio,
        demographics: Optional[DadosDemograficos],
    ) -> bool:
        """Avalia se uma regra é ativada."""
        # Obter valor da métrica
        metric_name = rule["metric"]
        value = getattr(weather, metric_name, None)
        if value is None:
            return False

        # Avaliar condição principal
        threshold = rule["threshold"]
        operator = rule["operator"]

        if operator == ">" and not (value > threshold):
            return False
        elif operator == "<" and not (value < threshold):
            return False
        elif operator == ">=" and not (value >= threshold):
            return False

        # Avaliar condição geográfica
        geo_condition = rule.get("geographic_condition")
        if geo_condition == "em_vale" and not municipio.em_vale:
            return False

        # Avaliar condição demográfica
        demo_condition = rule.get("demographic_condition")
        if demo_condition and demographics:
            field_name = demo_condition["field"]
            demo_value = getattr(demographics, field_name, None)
            if demo_value is not None:
                demo_threshold = demo_condition["value"]
                demo_op = demo_condition["operator"]
                if demo_op == ">" and not (demo_value > demo_threshold):
                    return False

        return True

    def _compute_index(
        self, triggered_rules: List[Dict], demographics: Optional[DadosDemograficos]
    ) -> float:
        """Calcula índice composto de risco (0-100)."""
        if not triggered_rules:
            return 0.0

        # Score climático baseado nos pesos das regras ativadas
        climate_score = sum(r["weight"] for r in triggered_rules) * 100
        climate_score = min(climate_score, 100)

        # Fator de vulnerabilidade
        vuln_factor = 0.5  # padrão se não há dados
        if demographics and demographics.indice_vulnerabilidade is not None:
            vuln_factor = demographics.indice_vulnerabilidade / 100

        # Índice final: clima (70%) + vulnerabilidade (30%)
        final_index = climate_score * 0.7 + (vuln_factor * 100) * 0.3
        return round(min(final_index, 100), 1)

    @staticmethod
    def _classify(index: float) -> str:
        """Classifica o índice de risco."""
        if index <= 25:
            return "baixo"
        elif index <= 50:
            return "moderado"
        elif index <= 75:
            return "alto"
        return "critico"
