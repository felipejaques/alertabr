"""Endpoints geográficos - estados e municípios."""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.functions import ST_AsGeoJSON

from app.database import get_db
from app.models.geographic import Estado, Municipio

router = APIRouter(prefix="/api/v1", tags=["geographic"])


@router.get("/states")
async def list_states(db: AsyncSession = Depends(get_db)):
    """Lista todos os estados."""
    result = await db.execute(
        select(
            Estado.id,
            Estado.codigo_ibge,
            Estado.nome,
            Estado.sigla,
            Estado.regiao,
        ).order_by(Estado.nome)
    )
    states = result.all()
    return [
        {
            "id": s.id,
            "codigo_ibge": s.codigo_ibge,
            "nome": s.nome,
            "sigla": s.sigla,
            "regiao": s.regiao,
        }
        for s in states
    ]


@router.get("/states/{uf}/municipalities")
async def list_municipalities_by_state(
    uf: str,
    db: AsyncSession = Depends(get_db),
):
    """Lista municípios de um estado."""
    result = await db.execute(
        select(Estado).where(Estado.sigla == uf.upper())
    )
    estado = result.scalar_one_or_none()
    if not estado:
        raise HTTPException(status_code=404, detail=f"Estado {uf} não encontrado")

    result = await db.execute(
        select(
            Municipio.id,
            Municipio.codigo_ibge,
            Municipio.nome,
            Municipio.area_km2,
        )
        .where(Municipio.estado_id == estado.id)
        .order_by(Municipio.nome)
    )
    municipios = result.all()
    return [
        {
            "id": m.id,
            "codigo_ibge": m.codigo_ibge,
            "nome": m.nome,
            "area_km2": m.area_km2,
        }
        for m in municipios
    ]


@router.get("/geojson/states")
async def get_states_geojson(db: AsyncSession = Depends(get_db)):
    """Retorna GeoJSON dos estados."""
    result = await db.execute(
        select(
            Estado.codigo_ibge,
            Estado.nome,
            Estado.sigla,
            ST_AsGeoJSON(Estado.geometria).label("geojson"),
        ).where(Estado.geometria.isnot(None))
    )
    features = []
    for row in result.all():
        import json
        geom = json.loads(row.geojson) if row.geojson else None
        features.append({
            "type": "Feature",
            "properties": {
                "id": row.codigo_ibge,
                "nome": row.nome,
                "sigla": row.sigla,
            },
            "geometry": geom,
        })

    return {"type": "FeatureCollection", "features": features}


@router.get("/geojson/municipalities")
async def get_municipalities_geojson(
    state: str = Query(..., description="Sigla do estado (ex: SC)"),
    db: AsyncSession = Depends(get_db),
):
    """Retorna GeoJSON dos municípios de um estado."""
    result = await db.execute(
        select(Estado).where(Estado.sigla == state.upper())
    )
    estado = result.scalar_one_or_none()
    if not estado:
        raise HTTPException(status_code=404, detail=f"Estado {state} não encontrado")

    result = await db.execute(
        select(
            Municipio.id,
            Municipio.codigo_ibge,
            Municipio.nome,
            ST_AsGeoJSON(Municipio.geometria).label("geojson"),
        )
        .where(Municipio.estado_id == estado.id)
        .where(Municipio.geometria.isnot(None))
    )

    features = []
    for row in result.all():
        import json
        geom = json.loads(row.geojson) if row.geojson else None
        features.append({
            "type": "Feature",
            "properties": {
                "id": row.id,
                "codigo_ibge": row.codigo_ibge,
                "nome": row.nome,
            },
            "geometry": geom,
        })

    return {"type": "FeatureCollection", "features": features}
