"""Endpoints de ingestão de dados."""

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db, engine, Base
from app.services.ibge_ingest import IBGEIngestService

router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])


@router.post("/setup-db")
async def setup_database():
    """Cria todas as tabelas no banco (útil para setup inicial)."""
    # Importar todos os models para registrar no metadata
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        # Habilitar PostGIS
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        # Criar tabelas
        await conn.run_sync(Base.metadata.create_all)

    return {"status": "ok", "message": "Tabelas criadas com sucesso"}


@router.post("/ibge")
async def trigger_ibge_ingest(
    uf: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Dispara ingestão de dados do IBGE.
    Se `uf` for informado, ingere apenas municípios daquele estado.
    Sem parâmetro, ingere todos os estados e municípios.
    """
    service = IBGEIngestService()

    if uf:
        # Garantir que estados existem
        await service.ingest_estados(db)
        count = await service.ingest_municipios_estado(uf, db)
        return {
            "status": "ok",
            "message": f"Municípios de {uf.upper()} ingeridos",
            "count": count,
        }
    else:
        result = await service.ingest_all(db)
        return {
            "status": "ok",
            "message": "Todos os dados IBGE ingeridos",
            "estados": result["estados"],
            "municipios": result["municipios"],
        }


@router.post("/inmet")
async def trigger_inmet_ingest(
    readings: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """
    Dispara ingestão de dados do INMET.
    - Sem parâmetros: ingere lista de estações
    - Com readings=true: ingere estações + medições das últimas 24h
    """
    from app.services.inmet_ingest import INMETIngestService

    service = INMETIngestService()

    try:
        stations_count = await service.ingest_estacoes(db)
    except Exception as e:
        return {
            "status": "error",
            "message": f"API do INMET indisponível: {str(e)}",
            "hint": "A API do INMET pode estar instável. Tente novamente em alguns minutos.",
        }

    result = {"status": "ok", "stations_ingested": stations_count}

    if readings:
        readings_count = await service.ingest_medicoes_recentes(db, horas=24)
        result["readings_ingested"] = readings_count

    return result


@router.post("/demographics")
async def trigger_demographics_ingest(
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """Ingere dados demográficos e calcula vulnerabilidade para um estado."""
    from app.services.demographic_ingest import DemographicIngestService

    service = DemographicIngestService()
    try:
        count = await service.ingest_populacao_estado(state, db)
        return {
            "status": "ok",
            "state": state.upper(),
            "records": count,
            "message": f"Dados demográficos de {state.upper()} ingeridos com cálculo de vulnerabilidade",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/ana")
async def trigger_ana_ingest(
    readings: bool = False,
    estado: str = "",
    db: AsyncSession = Depends(get_db),
):
    """
    Dispara ingestão de dados hidrológicos da ANA.
    - Sem parâmetros: ingere inventário de estações fluviométricas
    - Com readings=true: ingere estações + telemetria das últimas 6h
    - Com estado: filtra estações por estado (nome completo, ex: "Santa Catarina")
    """
    from app.services.ana_ingest import ANAIngestService

    service = ANAIngestService()

    try:
        stations_count = await service.ingest_estacoes(db, estado=estado)
    except Exception as e:
        return {
            "status": "error",
            "message": f"API da ANA indisponível: {str(e)}",
            "hint": "O web service da ANA pode estar instável. Tente novamente mais tarde.",
        }

    result = {"status": "ok", "stations_ingested": stations_count}

    if readings:
        try:
            readings_count = await service.ingest_telemetria_recente(db, horas=6)
            result["readings_ingested"] = readings_count
        except Exception as e:
            result["readings_error"] = str(e)

    return result
