"""Endpoints de dados hidrológicos (ANA)."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.hydrology import EstacaoHidrologica, MedicaoHidrologica
from app.models.geographic import Estado, Municipio

router = APIRouter(prefix="/api/v1/hydrology", tags=["hydrology"])


@router.get("/stations")
async def list_stations(
    state: Optional[str] = None,
    rio: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Lista estações hidrológicas com filtros opcionais."""
    query = select(
        EstacaoHidrologica.id,
        EstacaoHidrologica.codigo_ana,
        EstacaoHidrologica.nome,
        EstacaoHidrologica.municipio_id,
        EstacaoHidrologica.rio_nome,
        EstacaoHidrologica.bacia,
        EstacaoHidrologica.tipo,
        EstacaoHidrologica.ativa,
        EstacaoHidrologica.nivel_atencao,
        EstacaoHidrologica.nivel_alerta,
        EstacaoHidrologica.nivel_emergencia,
    )

    if state:
        query = query.join(Municipio).join(Estado).where(
            Estado.sigla == state.upper()
        )

    if rio:
        query = query.where(EstacaoHidrologica.rio_nome.ilike(f"%{rio}%"))

    result = await db.execute(query.order_by(EstacaoHidrologica.nome))
    stations = result.all()

    return [
        {
            "id": s.id,
            "codigo_ana": s.codigo_ana,
            "nome": s.nome,
            "municipio_id": s.municipio_id,
            "rio_nome": s.rio_nome,
            "bacia": s.bacia,
            "tipo": s.tipo,
            "ativa": s.ativa,
            "nivel_atencao": s.nivel_atencao,
            "nivel_alerta": s.nivel_alerta,
            "nivel_emergencia": s.nivel_emergencia,
        }
        for s in stations
    ]


@router.get("/stations/{station_id}")
async def get_station(
    station_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Retorna detalhes de uma estação hidrológica incluindo última medição."""
    result = await db.execute(
        select(EstacaoHidrologica).where(EstacaoHidrologica.id == station_id)
    )
    station = result.scalar_one_or_none()
    if not station:
        return {"error": "Estação não encontrada"}

    # Buscar última medição
    last_reading = await db.execute(
        select(MedicaoHidrologica)
        .where(MedicaoHidrologica.estacao_id == station_id)
        .order_by(MedicaoHidrologica.data_hora.desc())
        .limit(1)
    )
    reading = last_reading.scalar_one_or_none()

    # Determinar status do nível
    status_nivel = "normal"
    if reading and reading.nivel is not None and station.nivel_atencao:
        if station.nivel_emergencia and reading.nivel >= station.nivel_emergencia:
            status_nivel = "emergencia"
        elif station.nivel_alerta and reading.nivel >= station.nivel_alerta:
            status_nivel = "alerta"
        elif reading.nivel >= station.nivel_atencao:
            status_nivel = "atencao"

    return {
        "id": station.id,
        "codigo_ana": station.codigo_ana,
        "nome": station.nome,
        "municipio_id": station.municipio_id,
        "rio_nome": station.rio_nome,
        "bacia": station.bacia,
        "tipo": station.tipo,
        "ativa": station.ativa,
        "limiares": {
            "atencao": station.nivel_atencao,
            "alerta": station.nivel_alerta,
            "emergencia": station.nivel_emergencia,
        },
        "ultima_medicao": {
            "data_hora": reading.data_hora.isoformat() if reading else None,
            "nivel": reading.nivel if reading else None,
            "vazao": reading.vazao if reading else None,
            "chuva": reading.chuva if reading else None,
        },
        "status_nivel": status_nivel,
    }


@router.get("/readings/{station_id}")
async def get_readings(
    station_id: int,
    limit: int = Query(default=48, le=720),
    db: AsyncSession = Depends(get_db),
):
    """Retorna últimas medições hidrológicas de uma estação."""
    result = await db.execute(
        select(MedicaoHidrologica)
        .where(MedicaoHidrologica.estacao_id == station_id)
        .order_by(MedicaoHidrologica.data_hora.desc())
        .limit(limit)
    )
    medicoes = result.scalars().all()

    return [
        {
            "data_hora": m.data_hora.isoformat(),
            "nivel": m.nivel,
            "vazao": m.vazao,
            "chuva": m.chuva,
        }
        for m in medicoes
    ]


@router.get("/municipality/{municipality_id}")
async def get_hydrology_by_municipality(
    municipality_id: int,
    limit: int = Query(default=48, le=720),
    db: AsyncSession = Depends(get_db),
):
    """Retorna estações e medições hidrológicas de um município."""
    # Buscar estações do município
    stations_result = await db.execute(
        select(EstacaoHidrologica).where(
            EstacaoHidrologica.municipio_id == municipality_id,
            EstacaoHidrologica.ativa == True,
        )
    )
    stations = stations_result.scalars().all()

    if not stations:
        return {"stations": [], "readings": []}

    station_ids = [s.id for s in stations]

    # Buscar medições recentes
    readings_result = await db.execute(
        select(MedicaoHidrologica)
        .where(MedicaoHidrologica.estacao_id.in_(station_ids))
        .order_by(MedicaoHidrologica.data_hora.desc())
        .limit(limit)
    )
    medicoes = readings_result.scalars().all()

    return {
        "stations": [
            {
                "id": s.id,
                "codigo_ana": s.codigo_ana,
                "nome": s.nome,
                "rio_nome": s.rio_nome,
                "nivel_atencao": s.nivel_atencao,
                "nivel_alerta": s.nivel_alerta,
                "nivel_emergencia": s.nivel_emergencia,
            }
            for s in stations
        ],
        "readings": [
            {
                "estacao_id": m.estacao_id,
                "data_hora": m.data_hora.isoformat(),
                "nivel": m.nivel,
                "vazao": m.vazao,
                "chuva": m.chuva,
            }
            for m in medicoes
        ],
    }


@router.get("/status")
async def get_hydrology_status(
    state: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna resumo do status hidrológico: estações em alerta/emergência.
    Útil para o dashboard exibir indicadores rápidos.
    """
    query = select(
        EstacaoHidrologica.id,
        EstacaoHidrologica.codigo_ana,
        EstacaoHidrologica.nome,
        EstacaoHidrologica.rio_nome,
        EstacaoHidrologica.municipio_id,
        EstacaoHidrologica.nivel_atencao,
        EstacaoHidrologica.nivel_alerta,
        EstacaoHidrologica.nivel_emergencia,
    ).where(EstacaoHidrologica.ativa == True)

    if state:
        query = query.join(Municipio).join(Estado).where(
            Estado.sigla == state.upper()
        )

    result = await db.execute(query)
    stations = result.all()

    alerts = []
    for s in stations:
        # Buscar última medição de nível
        reading_result = await db.execute(
            select(MedicaoHidrologica.nivel, MedicaoHidrologica.data_hora)
            .where(
                MedicaoHidrologica.estacao_id == s.id,
                MedicaoHidrologica.nivel.isnot(None),
            )
            .order_by(MedicaoHidrologica.data_hora.desc())
            .limit(1)
        )
        reading = reading_result.first()
        if not reading or reading.nivel is None:
            continue

        nivel_atual = reading.nivel
        status = "normal"

        if s.nivel_emergencia and nivel_atual >= s.nivel_emergencia:
            status = "emergencia"
        elif s.nivel_alerta and nivel_atual >= s.nivel_alerta:
            status = "alerta"
        elif s.nivel_atencao and nivel_atual >= s.nivel_atencao:
            status = "atencao"

        if status != "normal":
            alerts.append({
                "estacao_id": s.id,
                "codigo_ana": s.codigo_ana,
                "nome": s.nome,
                "rio_nome": s.rio_nome,
                "municipio_id": s.municipio_id,
                "nivel_atual": nivel_atual,
                "status": status,
                "data_hora": reading.data_hora.isoformat(),
                "limiares": {
                    "atencao": s.nivel_atencao,
                    "alerta": s.nivel_alerta,
                    "emergencia": s.nivel_emergencia,
                },
            })

    # Ordenar: emergência primeiro, depois alerta, depois atenção
    priority = {"emergencia": 0, "alerta": 1, "atencao": 2}
    alerts.sort(key=lambda x: priority.get(x["status"], 99))

    return {
        "total_stations": len(stations),
        "alerts_count": len(alerts),
        "alerts": alerts,
    }
