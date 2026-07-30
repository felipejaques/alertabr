"""Endpoints de risco."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.risk_engine import RiskEngine

router = APIRouter(prefix="/api/v1/risk", tags=["risk"])


@router.get("/map")
async def get_risk_map(
    state: str = Query(..., description="Sigla do estado (ex: SC)"),
    db: AsyncSession = Depends(get_db),
):
    """Retorna mapa de risco para todos os municípios de um estado."""
    engine = RiskEngine()
    risks = await engine.calculate_risk_map(state, db)
    return {"state": state.upper(), "municipalities": risks}


@router.get("/{municipio_id}")
async def get_municipality_risk(
    municipio_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Calcula e retorna risco de um município específico."""
    engine = RiskEngine()
    result = await engine.calculate_risk(municipio_id, db)
    return {
        "municipio_id": result.municipio_id,
        "index": result.index,
        "classification": result.classification,
        "triggered_rules": result.triggered_rules,
        "primary_type": result.primary_type,
        "calculated_at": result.calculated_at.isoformat(),
    }
