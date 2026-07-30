"""Endpoints de cenários (El Niño, La Niña)."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.geographic import Estado, Municipio

router = APIRouter(prefix="/api/v1/scenarios", tags=["scenarios"])

# Configuração de cenários
EL_NINO_SCENARIO = {
    "id": "el-nino",
    "name": "El Niño - Cenário Projetado",
    "description": "Projeção de impactos do fenômeno El Niño no Brasil baseada em padrões históricos",
    "impacts": {
        "Sul": {
            "precipitation_factor": 1.6,
            "temperature_factor": 1.1,
            "primary_risk": "inundacao",
            "description": "Chuvas 60% acima da média, risco elevado de inundações",
            "affected_states": ["RS", "SC", "PR"],
            "severity_projection": "alto_a_critico",
        },
        "Sudeste": {
            "precipitation_factor": 1.3,
            "temperature_factor": 1.15,
            "primary_risk": "inundacao",
            "description": "Chuvas 30% acima da média, calor acima do normal",
            "affected_states": ["SP", "RJ", "MG", "ES"],
            "severity_projection": "moderado_a_alto",
        },
        "Nordeste": {
            "precipitation_factor": 0.4,
            "temperature_factor": 1.2,
            "primary_risk": "seca",
            "description": "Seca severa, precipitação 60% abaixo da média",
            "affected_states": ["MA", "PI", "CE", "RN", "PB", "PE", "AL", "SE", "BA"],
            "severity_projection": "alto_a_critico",
        },
        "Norte": {
            "precipitation_factor": 0.5,
            "temperature_factor": 1.25,
            "primary_risk": "seca",
            "description": "Redução de chuvas, risco de incêndios florestais",
            "affected_states": ["AM", "PA", "AC", "RO", "RR", "AP", "TO"],
            "severity_projection": "moderado_a_alto",
        },
        "Centro-Oeste": {
            "precipitation_factor": 0.8,
            "temperature_factor": 1.15,
            "primary_risk": "seca",
            "description": "Chuvas levemente abaixo da média",
            "affected_states": ["MT", "MS", "GO", "DF"],
            "severity_projection": "moderado",
        },
    },
}

LA_NINA_SCENARIO = {
    "id": "la-nina",
    "name": "La Niña - Cenário Projetado",
    "description": "Projeção de impactos do fenômeno La Niña no Brasil",
    "impacts": {
        "Sul": {
            "precipitation_factor": 0.6,
            "temperature_factor": 0.95,
            "primary_risk": "seca",
            "description": "Chuvas 40% abaixo da média, seca no Sul",
            "affected_states": ["RS", "SC", "PR"],
            "severity_projection": "moderado_a_alto",
        },
        "Nordeste": {
            "precipitation_factor": 1.4,
            "temperature_factor": 0.95,
            "primary_risk": "inundacao",
            "description": "Chuvas 40% acima da média no semiárido",
            "affected_states": ["MA", "PI", "CE", "RN", "PB", "PE", "AL", "SE", "BA"],
            "severity_projection": "moderado_a_alto",
        },
        "Norte": {
            "precipitation_factor": 1.3,
            "temperature_factor": 0.9,
            "primary_risk": "inundacao",
            "description": "Chuvas acima da média na Amazônia",
            "affected_states": ["AM", "PA", "AC", "RO", "RR", "AP", "TO"],
            "severity_projection": "moderado",
        },
    },
}

SCENARIOS = {
    "el-nino": EL_NINO_SCENARIO,
    "la-nina": LA_NINA_SCENARIO,
}


@router.get("")
async def list_scenarios():
    """Lista cenários disponíveis."""
    return [
        {"id": s["id"], "name": s["name"], "description": s["description"]}
        for s in SCENARIOS.values()
    ]


@router.get("/{scenario_id}")
async def get_scenario(scenario_id: str):
    """Retorna detalhes de um cenário."""
    scenario = SCENARIOS.get(scenario_id)
    if not scenario:
        return {"error": f"Cenário '{scenario_id}' não encontrado"}
    return scenario


@router.get("/{scenario_id}/risk-map")
async def get_scenario_risk_map(
    scenario_id: str,
    state: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Retorna mapa de risco projetado para um cenário."""
    scenario = SCENARIOS.get(scenario_id)
    if not scenario:
        return {"error": f"Cenário '{scenario_id}' não encontrado"}

    # Buscar estados com suas regiões
    query = select(Estado)
    if state:
        query = query.where(Estado.sigla == state.upper())
    result = await db.execute(query)
    estados = result.scalars().all()

    projections = []
    for estado in estados:
        # Encontrar impacto da região deste estado
        impact = None
        for region_name, region_impact in scenario["impacts"].items():
            if estado.sigla in region_impact["affected_states"]:
                impact = region_impact
                break

        if not impact:
            continue

        # Buscar municípios do estado
        mun_result = await db.execute(
            select(Municipio.id, Municipio.nome, Municipio.codigo_ibge).where(
                Municipio.estado_id == estado.id
            )
        )
        municipios = mun_result.all()

        for mun in municipios:
            # Calcular risco projetado baseado no cenário
            base_risk = 30  # risco base médio
            precip_factor = impact["precipitation_factor"]

            if precip_factor > 1:
                # Mais chuva = mais risco de inundação
                projected_risk = min(base_risk * precip_factor, 100)
            else:
                # Menos chuva = risco de seca
                projected_risk = min(base_risk * (2 - precip_factor), 100)

            classification = _classify(projected_risk)

            projections.append({
                "municipio_id": mun.id,
                "codigo_ibge": mun.codigo_ibge,
                "nome": mun.nome,
                "state": estado.sigla,
                "projected_risk": round(projected_risk, 1),
                "classification": classification,
                "primary_risk": impact["primary_risk"],
                "description": impact["description"],
            })

    return {
        "scenario": scenario_id,
        "state": state,
        "total_municipalities": len(projections),
        "municipalities": projections,
    }


def _classify(index: float) -> str:
    if index <= 25:
        return "baixo"
    elif index <= 50:
        return "moderado"
    elif index <= 75:
        return "alto"
    return "critico"
