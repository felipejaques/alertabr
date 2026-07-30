"""Endpoints de dados meteorológicos."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.weather import EstacaoMeteorologica, MedicaoClimatica
from app.models.geographic import Estado, Municipio
from app.services.inmet_ingest import INMETIngestService

router = APIRouter(prefix="/api/v1/weather", tags=["weather"])


@router.get("/stations")
async def list_stations(
    state: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Lista estações meteorológicas."""
    query = select(
        EstacaoMeteorologica.id,
        EstacaoMeteorologica.codigo_inmet,
        EstacaoMeteorologica.nome,
        EstacaoMeteorologica.municipio_id,
        EstacaoMeteorologica.altitude,
        EstacaoMeteorologica.tipo,
        EstacaoMeteorologica.ativa,
    )

    if state:
        query = query.join(Municipio).join(Estado).where(
            Estado.sigla == state.upper()
        )

    result = await db.execute(query.order_by(EstacaoMeteorologica.nome))
    stations = result.all()

    return [
        {
            "id": s.id,
            "codigo_inmet": s.codigo_inmet,
            "nome": s.nome,
            "municipio_id": s.municipio_id,
            "altitude": s.altitude,
            "tipo": s.tipo,
            "ativa": s.ativa,
        }
        for s in stations
    ]


@router.get("/readings/{station_id}")
async def get_readings(
    station_id: int,
    limit: int = Query(default=24, le=168),
    db: AsyncSession = Depends(get_db),
):
    """Retorna últimas medições de uma estação."""
    result = await db.execute(
        select(MedicaoClimatica)
        .where(MedicaoClimatica.estacao_id == station_id)
        .order_by(MedicaoClimatica.data_hora.desc())
        .limit(limit)
    )
    medicoes = result.scalars().all()

    return [
        {
            "data_hora": m.data_hora.isoformat(),
            "temperatura": m.temperatura,
            "temperatura_max": m.temperatura_max,
            "precipitacao": m.precipitacao,
            "umidade": m.umidade,
            "vento_velocidade": m.vento_velocidade,
            "vento_direcao": m.vento_direcao,
            "pressao": m.pressao,
        }
        for m in medicoes
    ]


@router.get("/municipality/{municipality_id}/readings")
async def get_readings_by_municipality(
    municipality_id: int,
    limit: int = Query(default=168, le=2160),
    db: AsyncSession = Depends(get_db),
):
    """Retorna últimas medições de todas as estações de um município."""
    # Busca todas as estações do município
    stations_result = await db.execute(
        select(EstacaoMeteorologica.id).where(
            EstacaoMeteorologica.municipio_id == municipality_id,
            EstacaoMeteorologica.ativa == True,
        )
    )
    station_ids = [row[0] for row in stations_result.all()]

    if not station_ids:
        return []

    # Busca medições de todas as estações do município
    result = await db.execute(
        select(MedicaoClimatica)
        .where(MedicaoClimatica.estacao_id.in_(station_ids))
        .order_by(MedicaoClimatica.data_hora.desc())
        .limit(limit)
    )
    medicoes = result.scalars().all()

    return [
        {
            "data_hora": m.data_hora.isoformat(),
            "temperatura": m.temperatura,
            "temperatura_max": m.temperatura_max,
            "temperatura_min": m.temperatura_min,
            "precipitacao": m.precipitacao,
            "umidade": m.umidade,
            "vento_velocidade": m.vento_velocidade,
            "vento_direcao": m.vento_direcao,
            "pressao": m.pressao,
        }
        for m in medicoes
    ]
