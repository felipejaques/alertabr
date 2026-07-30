"""Serviço de ingestão de dados meteorológicos do INMET."""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.functions import ST_Distance, ST_SetSRID, ST_MakePoint

from app.models.geographic import Municipio
from app.models.weather import EstacaoMeteorologica, MedicaoClimatica

logger = logging.getLogger(__name__)

INMET_BASE_URL = "https://apitempo.inmet.gov.br"


class INMETClient:
    """Cliente HTTP para API do INMET."""

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    async def get_estacoes_automaticas(self) -> List[Dict]:
        """Lista todas as estações automáticas."""
        headers = {
            "User-Agent": "AlertaBR/1.0 (plataforma de prevencao a desastres)",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(timeout=self.timeout, headers=headers) as client:
            for attempt in range(3):
                try:
                    response = await client.get(f"{INMET_BASE_URL}/estacoes/T")
                    response.raise_for_status()
                    return response.json()
                except (httpx.RemoteProtocolError, httpx.ReadTimeout) as e:
                    logger.warning(f"Tentativa {attempt + 1}/3 falhou: {e}")
                    if attempt == 2:
                        raise
                    import asyncio
                    await asyncio.sleep(2 * (attempt + 1))
        return []

    async def get_dados_estacao(
        self, codigo: str, data_inicio: str, data_fim: str
    ) -> List[Dict]:
        """Busca dados horários de uma estação no período."""
        headers = {
            "User-Agent": "AlertaBR/1.0 (plataforma de prevencao a desastres)",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(timeout=self.timeout, headers=headers) as client:
            url = f"{INMET_BASE_URL}/estacao/dados/{data_inicio}/{data_fim}/{codigo}"
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.json()
            except (httpx.RemoteProtocolError, httpx.ReadTimeout) as e:
                logger.warning(f"INMET estação {codigo}: {e}")
            return []


class INMETIngestService:
    """Serviço de ingestão de dados meteorológicos."""

    def __init__(self):
        self.client = INMETClient()

    async def ingest_estacoes(self, db: AsyncSession) -> int:
        """Ingere lista de estações automáticas do INMET."""
        estacoes = await self.client.get_estacoes_automaticas()
        count = 0

        for est in estacoes:
            # Filtrar estações operantes com coordenadas válidas
            if not est.get("VL_LATITUDE") or not est.get("VL_LONGITUDE"):
                continue

            codigo = est.get("CD_ESTACAO", "")
            if not codigo:
                continue

            # Verificar se já existe
            existing = await db.execute(
                select(EstacaoMeteorologica).where(
                    EstacaoMeteorologica.codigo_inmet == codigo
                )
            )
            if existing.scalar_one_or_none():
                continue

            try:
                lat = float(est["VL_LATITUDE"])
                lon = float(est["VL_LONGITUDE"])
                altitude = float(est.get("VL_ALTITUDE", 0) or 0)
            except (ValueError, TypeError):
                continue

            # Buscar município mais próximo
            municipio_id = await self._find_nearest_municipality(db, lat, lon)

            estacao = EstacaoMeteorologica(
                codigo_inmet=codigo,
                nome=est.get("DC_NOME", ""),
                municipio_id=municipio_id,
                coordenada=f"SRID=4326;POINT({lon} {lat})",
                altitude=altitude,
                tipo=est.get("TP_ESTACAO", "Automatica"),
                ativa=est.get("CD_SITUACAO") == "Operante",
            )
            db.add(estacao)
            count += 1

        await db.commit()
        logger.info(f"Ingeridas {count} estações meteorológicas")
        return count

    async def ingest_medicoes_recentes(self, db: AsyncSession, horas: int = 24) -> int:
        """Ingere medições das últimas N horas de todas as estações ativas."""
        now = datetime.now(timezone.utc)
        data_fim = now.strftime("%Y-%m-%d")
        data_inicio = (now - timedelta(hours=horas)).strftime("%Y-%m-%d")

        result = await db.execute(
            select(EstacaoMeteorologica).where(EstacaoMeteorologica.ativa == True)
        )
        estacoes = result.scalars().all()

        count = 0
        for estacao in estacoes:
            try:
                dados = await self.client.get_dados_estacao(
                    estacao.codigo_inmet, data_inicio, data_fim
                )
                inserted = await self._process_medicoes(db, estacao.id, dados)
                count += inserted
            except Exception as e:
                logger.warning(f"Erro estação {estacao.codigo_inmet}: {e}")
                continue

        await db.commit()
        logger.info(f"Ingeridas {count} medições climáticas")
        return count

    async def _process_medicoes(
        self, db: AsyncSession, estacao_id: int, dados: List[Dict]
    ) -> int:
        """Processa e insere medições de uma estação."""
        count = 0
        for registro in dados:
            try:
                data_str = registro.get("DT_MEDICAO", "")
                hora_str = registro.get("HR_MEDICAO", "0000")
                if not data_str:
                    continue

                # Montar datetime
                hora = int(hora_str[:2]) if hora_str else 0
                data_hora = datetime.strptime(data_str, "%Y-%m-%d").replace(
                    hour=hora, tzinfo=timezone.utc
                )

                # Verificar duplicata
                existing = await db.execute(
                    select(MedicaoClimatica).where(
                        MedicaoClimatica.estacao_id == estacao_id,
                        MedicaoClimatica.data_hora == data_hora,
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                medicao = MedicaoClimatica(
                    estacao_id=estacao_id,
                    data_hora=data_hora,
                    temperatura=self._parse_float(registro.get("TEM_INS")),
                    temperatura_max=self._parse_float(registro.get("TEM_MAX")),
                    temperatura_min=self._parse_float(registro.get("TEM_MIN")),
                    precipitacao=self._parse_float(registro.get("CHUVA")),
                    umidade=self._parse_float(registro.get("UMD_INS")),
                    vento_velocidade=self._parse_float(registro.get("VEN_VEL")),
                    vento_direcao=self._parse_int(registro.get("VEN_DIR")),
                    pressao=self._parse_float(registro.get("PRE_INS")),
                    radiacao=self._parse_float(registro.get("RAD_GLO")),
                )
                db.add(medicao)
                count += 1
            except Exception as e:
                logger.debug(f"Erro ao processar medição: {e}")
                continue

        return count

    async def _find_nearest_municipality(
        self, db: AsyncSession, lat: float, lon: float
    ) -> Optional[int]:
        """Encontra o município mais próximo de uma coordenada."""
        point = f"SRID=4326;POINT({lon} {lat})"
        result = await db.execute(
            select(Municipio.id)
            .where(Municipio.geometria.isnot(None))
            .order_by(Municipio.geometria.ST_Distance(point))
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return row

    @staticmethod
    def _parse_float(value) -> Optional[float]:
        if value is None or value == "" or value == "null":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_int(value) -> Optional[int]:
        if value is None or value == "" or value == "null":
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None
