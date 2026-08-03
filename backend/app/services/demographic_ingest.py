"""Serviço de ingestão de dados demográficos do IBGE Agregados."""

import logging
from typing import Dict, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.geographic import Estado, Municipio
from app.models.demographic import DadosDemograficos

logger = logging.getLogger(__name__)

IBGE_BASE_URL = "https://servicodados.ibge.gov.br"


class DemographicIngestService:
    """Serviço de ingestão e cálculo de vulnerabilidade."""

    async def ingest_populacao_estado(self, uf_sigla: str, db: AsyncSession) -> int:
        """Ingere dados populacionais dos municípios de um estado."""
        # Buscar estado
        result = await db.execute(
            select(Estado).where(Estado.sigla == uf_sigla.upper())
        )
        estado = result.scalar_one_or_none()
        if not estado:
            raise ValueError(f"Estado {uf_sigla} não encontrado")

        # Buscar população via API IBGE Agregados
        headers = {"User-Agent": "AlertaBR/1.0"}
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            try:
                response = await client.get(
                    f"{IBGE_BASE_URL}/api/v3/agregados/4714/periodos/2021/variaveis/93",
                    params={"localidades": f"N6[N3[{estado.codigo_ibge}]]"},
                )
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                logger.warning(f"API IBGE Agregados indisponível: {e}")
                # Criar registros vazios quando a API não está disponível
                return await self._seed_empty_demographics(estado.id, db)

        # Processar resposta
        count = 0
        if data and len(data) > 0:
            resultados = data[0].get("resultados", [])
            for resultado in resultados:
                series = resultado.get("series", [])
                for serie in series:
                    localidade = serie.get("localidade", {})
                    cod_municipio = int(localidade.get("id", 0))
                    populacao_str = serie.get("serie", {}).get("2021")

                    if not cod_municipio or not populacao_str:
                        continue

                    try:
                        populacao = int(populacao_str)
                    except ValueError:
                        continue

                    # Buscar município
                    mun_result = await db.execute(
                        select(Municipio).where(Municipio.codigo_ibge == cod_municipio)
                    )
                    municipio = mun_result.scalar_one_or_none()
                    if not municipio:
                        continue

                    # Inserir ou atualizar
                    existing = await db.execute(
                        select(DadosDemograficos).where(
                            DadosDemograficos.municipio_id == municipio.id
                        )
                    )
                    demo = existing.scalar_one_or_none()

                    if demo:
                        demo.populacao = populacao
                    else:
                        demo = DadosDemograficos(
                            municipio_id=municipio.id,
                            populacao=populacao,
                            ano_referencia=2021,
                        )
                        db.add(demo)
                    count += 1

        await db.commit()

        # Calcular vulnerabilidade para todos
        await self._calculate_all_vulnerability(estado.id, db)

        logger.info(f"Ingeridos {count} registros demográficos de {uf_sigla}")
        return count

    async def _seed_empty_demographics(self, estado_id: int, db: AsyncSession) -> int:
        """Cria registros demográficos vazios quando a API não está disponível."""
        result = await db.execute(
            select(Municipio).where(Municipio.estado_id == estado_id)
        )
        municipios = result.scalars().all()

        count = 0
        for mun in municipios:
            existing = await db.execute(
                select(DadosDemograficos).where(
                    DadosDemograficos.municipio_id == mun.id
                )
            )
            if existing.scalar_one_or_none():
                continue

            demo = DadosDemograficos(
                municipio_id=mun.id,
                populacao=None,
                densidade_demografica=None,
                pct_idosos=None,
                pct_baixa_renda=None,
                idh=None,
                pct_esgoto=None,
                ano_referencia=2021,
            )
            db.add(demo)
            count += 1

        await db.commit()
        logger.info(
            f"Criados {count} registros demográficos vazios (API indisponível) "
            f"para estado_id={estado_id}"
        )
        return count

    async def _calculate_all_vulnerability(self, estado_id: int, db: AsyncSession):
        """Calcula índice de vulnerabilidade para todos os municípios de um estado."""
        result = await db.execute(
            select(DadosDemograficos)
            .join(Municipio)
            .where(Municipio.estado_id == estado_id)
        )
        demographics = result.scalars().all()

        for demo in demographics:
            demo.indice_vulnerabilidade = self._calculate_vulnerability(demo)

        await db.commit()

    @staticmethod
    def _calculate_vulnerability(demo: DadosDemograficos) -> float:
        """Calcula índice de vulnerabilidade (0-100)."""
        # Normalizar indicadores (0-1)
        densidade_norm = min((demo.densidade_demografica or 0) / 10000, 1.0)
        idosos_norm = min((demo.pct_idosos or 0) / 40, 1.0)
        renda_norm = (demo.pct_baixa_renda or 50) / 100
        infra_norm = 1 - (demo.pct_esgoto or 0.5)

        # Índice ponderado
        indice = (
            densidade_norm * 0.20
            + idosos_norm * 0.30
            + renda_norm * 0.30
            + infra_norm * 0.20
        ) * 100

        return round(min(max(indice, 0), 100), 1)
