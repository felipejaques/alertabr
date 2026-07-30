"""Endpoints de alertas."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.alerts import Alerta
from app.models.geographic import Municipio, Estado
from app.services.alert_service import AlertService

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


@router.get("")
async def list_alerts(
    state: Optional[str] = None,
    municipality_id: Optional[int] = None,
    severity: Optional[str] = None,
    active: bool = True,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Lista alertas com filtros."""
    query = select(Alerta).where(Alerta.ativo == active)

    if state:
        query = query.join(Municipio).join(Estado).where(
            Estado.sigla == state.upper()
        )
    if municipality_id:
        query = query.where(Alerta.municipio_id == municipality_id)
    if severity:
        query = query.where(Alerta.severidade == severity)

    query = query.order_by(Alerta.data_inicio.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    alertas = result.scalars().all()

    return [
        {
            "id": a.id,
            "municipio_id": a.municipio_id,
            "tipo": a.tipo,
            "severidade": a.severidade,
            "indice_risco": a.indice_risco,
            "descricao": a.descricao,
            "regras_ativadas": a.regras_ativadas,
            "data_inicio": a.data_inicio.isoformat() if a.data_inicio else None,
            "data_fim": a.data_fim.isoformat() if a.data_fim else None,
            "ativo": a.ativo,
        }
        for a in alertas
    ]


@router.get("/active/count")
async def count_active_alerts(
    state: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Contagem de alertas ativos por severidade."""
    base_query = select(
        Alerta.severidade, func.count(Alerta.id)
    ).where(Alerta.ativo == True)

    if state:
        base_query = base_query.join(Municipio).join(Estado).where(
            Estado.sigla == state.upper()
        )

    base_query = base_query.group_by(Alerta.severidade)
    result = await db.execute(base_query)

    counts = {"critico": 0, "alto": 0, "moderado": 0, "baixo": 0}
    total = 0
    for row in result.all():
        counts[row[0]] = row[1]
        total += row[1]
    counts["total"] = total

    return counts


@router.get("/{alert_id}")
async def get_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    """Detalhes de um alerta."""
    alert = await db.get(Alerta, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta não encontrado")

    return {
        "id": alert.id,
        "municipio_id": alert.municipio_id,
        "tipo": alert.tipo,
        "severidade": alert.severidade,
        "indice_risco": alert.indice_risco,
        "descricao": alert.descricao,
        "regras_ativadas": alert.regras_ativadas,
        "data_inicio": alert.data_inicio.isoformat() if alert.data_inicio else None,
        "data_fim": alert.data_fim.isoformat() if alert.data_fim else None,
        "ativo": alert.ativo,
    }


@router.post("/process")
async def process_alerts(
    state: str = Query(..., description="Sigla do estado"),
    db: AsyncSession = Depends(get_db),
):
    """Dispara processamento de alertas para um estado."""
    service = AlertService()
    result = await service.process_alerts_for_state(state, db)
    return result
