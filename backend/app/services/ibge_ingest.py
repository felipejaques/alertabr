"""Serviço de ingestão de dados do IBGE (localidades + malhas GeoJSON)."""

import logging
from typing import List, Dict, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.geographic import Estado, Municipio

logger = logging.getLogger(__name__)

IBGE_BASE_URL = "https://servicodados.ibge.gov.br"


class IBGEClient:
    """Cliente HTTP para APIs do IBGE."""

    def __init__(self, timeout: float = 60.0):
        self.timeout = timeout

    async def get_estados(self) -> List[Dict]:
        """Busca todos os estados do Brasil."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{IBGE_BASE_URL}/api/v1/localidades/estados",
                params={"orderBy": "nome"},
            )
            response.raise_for_status()
            return response.json()

    async def get_municipios_por_estado(self, uf_id: int) -> List[Dict]:
        """Busca todos os municípios de um estado."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{IBGE_BASE_URL}/api/v1/localidades/estados/{uf_id}/municipios"
            )
            response.raise_for_status()
            return response.json()

    async def get_malha_estado(self, uf_id: int) -> Optional[Dict]:
        """Busca GeoJSON com municípios de um estado."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(
                f"{IBGE_BASE_URL}/api/v3/malhas/estados/{uf_id}",
                params={
                    "formato": "application/vnd.geo+json",
                    "qualidade": "intermediaria",
                    "intrarregiao": "municipio",
                },
            )
            if response.status_code == 200:
                return response.json()
            logger.warning(f"Falha ao buscar malha do estado {uf_id}: {response.status_code}")
            return None

    async def get_contorno_estado(self, uf_id: int) -> Optional[Dict]:
        """Busca GeoJSON do contorno de um estado (sem subdivisão)."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(
                f"{IBGE_BASE_URL}/api/v3/malhas/estados/{uf_id}",
                params={
                    "formato": "application/vnd.geo+json",
                    "qualidade": "intermediaria",
                },
            )
            if response.status_code == 200:
                return response.json()
            logger.warning(f"Falha ao buscar contorno do estado {uf_id}: {response.status_code}")
            return None


class IBGEIngestService:
    """Serviço de ingestão de dados geográficos do IBGE."""

    def __init__(self):
        self.client = IBGEClient()

    async def ingest_estados(self, db: AsyncSession) -> int:
        """Ingere todos os estados do Brasil com geometrias. Retorna quantidade inserida."""
        estados_data = await self.client.get_estados()
        count = 0

        for estado_data in estados_data:
            # Verificar se já existe
            existing = await db.execute(
                select(Estado).where(Estado.codigo_ibge == estado_data["id"])
            )
            estado_obj = existing.scalar_one_or_none()

            if estado_obj:
                # Se já existe mas sem geometria, buscar geometria
                if estado_obj.geometria is None:
                    geojson = await self.client.get_contorno_estado(estado_data["id"])
                    if geojson and "features" in geojson and geojson["features"]:
                        geom = geojson["features"][0].get("geometry")
                        if geom:
                            estado_obj.geometria = self._geojson_to_ewkt(geom)
                            count += 1
                continue

            estado = Estado(
                codigo_ibge=estado_data["id"],
                nome=estado_data["nome"],
                sigla=estado_data["sigla"],
                regiao=estado_data["regiao"]["nome"],
            )
            db.add(estado)
            count += 1

        await db.commit()

        # Buscar geometrias para estados recém-inseridos
        result = await db.execute(
            select(Estado).where(Estado.geometria.is_(None))
        )
        estados_sem_geom = result.scalars().all()

        for estado in estados_sem_geom:
            try:
                geojson = await self.client.get_contorno_estado(estado.codigo_ibge)
                if geojson and "features" in geojson and geojson["features"]:
                    geom = geojson["features"][0].get("geometry")
                    if geom:
                        estado.geometria = self._geojson_to_ewkt(geom)
            except Exception as e:
                logger.warning(f"Erro ao buscar geometria de {estado.sigla}: {e}")

        await db.commit()
        logger.info(f"Ingeridos/atualizados {count} estados")
        return count

    async def ingest_municipios_estado(self, uf_sigla: str, db: AsyncSession) -> int:
        """Ingere municípios de um estado com geometrias. Retorna quantidade."""
        # Buscar estado no banco
        result = await db.execute(
            select(Estado).where(Estado.sigla == uf_sigla.upper())
        )
        estado = result.scalar_one_or_none()
        if not estado:
            raise ValueError(f"Estado {uf_sigla} não encontrado. Execute ingest_estados primeiro.")

        # Buscar municípios da API
        municipios_data = await self.client.get_municipios_por_estado(estado.codigo_ibge)

        # Buscar malha GeoJSON
        geojson = await self.client.get_malha_estado(estado.codigo_ibge)

        # Criar mapa de código → geometria WKT
        geometrias: Dict[str, str] = {}
        if geojson and "features" in geojson:
            for feature in geojson["features"]:
                cod = feature["properties"].get("codarea", "")
                geom = feature.get("geometry")
                if cod and geom:
                    # Converter geometry dict para WKT usando formato GeoJSON
                    geometrias[cod] = self._geojson_to_ewkt(geom)

        count = 0
        for mun_data in municipios_data:
            codigo = mun_data["id"]

            # Verificar se já existe
            existing = await db.execute(
                select(Municipio).where(Municipio.codigo_ibge == codigo)
            )
            if existing.scalar_one_or_none():
                continue

            # Buscar geometria
            geom_ewkt = geometrias.get(str(codigo))

            municipio = Municipio(
                codigo_ibge=codigo,
                nome=mun_data["nome"],
                estado_id=estado.id,
                geometria=geom_ewkt,
            )
            db.add(municipio)
            count += 1

        await db.commit()
        logger.info(f"Ingeridos {count} municípios de {uf_sigla}")
        return count

    async def ingest_all(self, db: AsyncSession) -> Dict[str, int]:
        """Ingere todos os estados e municípios."""
        estados_count = await self.ingest_estados(db)

        # Buscar todos os estados para ingerir municípios
        result = await db.execute(select(Estado))
        estados = result.scalars().all()

        municipios_count = 0
        for estado in estados:
            try:
                count = await self.ingest_municipios_estado(estado.sigla, db)
                municipios_count += count
            except Exception as e:
                logger.error(f"Erro ao ingerir municípios de {estado.sigla}: {e}")
                continue

        return {"estados": estados_count, "municipios": municipios_count}

    def _geojson_to_ewkt(self, geojson_geometry: Dict) -> str:
        """Converte geometria GeoJSON para EWKT (PostGIS)."""
        import json
        # PostGIS aceita GeoJSON diretamente via ST_GeomFromGeoJSON
        # Usamos formato especial que o GeoAlchemy2 entende
        geojson_str = json.dumps(geojson_geometry)
        return f"SRID=4326;{self._geojson_to_wkt(geojson_geometry)}"

    def _geojson_to_wkt(self, geojson_geometry: Dict) -> str:
        """Converte GeoJSON geometry para WKT."""
        geom_type = geojson_geometry.get("type", "")
        coordinates = geojson_geometry.get("coordinates", [])

        if geom_type == "Polygon":
            rings = []
            for ring in coordinates:
                points = ", ".join(f"{p[0]} {p[1]}" for p in ring)
                rings.append(f"({points})")
            return f"MULTIPOLYGON(({', '.join(rings)}))"

        elif geom_type == "MultiPolygon":
            polygons = []
            for polygon in coordinates:
                rings = []
                for ring in polygon:
                    points = ", ".join(f"{p[0]} {p[1]}" for p in ring)
                    rings.append(f"({points})")
                polygons.append(f"({', '.join(rings)})")
            return f"MULTIPOLYGON({', '.join(polygons)})"

        else:
            logger.warning(f"Tipo de geometria não suportado: {geom_type}")
            return "MULTIPOLYGON EMPTY"
