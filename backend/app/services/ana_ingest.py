"""Serviço de ingestão de dados hidrológicos da ANA (Agência Nacional de Águas).

Consome o web service SOAP da ANA para obter:
- Inventário de estações fluviométricas (HidroInventario)
- Dados de telemetria em tempo real (DadosHidroTelemetria)
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

import httpx
import xmltodict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.geographic import Municipio
from app.models.hydrology import EstacaoHidrologica, MedicaoHidrologica

logger = logging.getLogger(__name__)

ANA_WS_URL = settings.ANA_TELEMETRIA_URL


# Templates SOAP para a API da ANA
SOAP_INVENTARIO = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <HidroInventario xmlns="http://ana.gov.br/">
      <codEstDE>{cod_estacao_de}</codEstDE>
      <codEstATE>{cod_estacao_ate}</codEstATE>
      <tpEst>{tipo_estacao}</tpEst>
      <nmEst></nmEst>
      <nmRio></nmRio>
      <codSubBacia></codSubBacia>
      <codBacia></codBacia>
      <nmMunicipio></nmMunicipio>
      <nmEstado>{estado}</nmEstado>
      <sgResp></sgResp>
      <sgOper></sgOper>
      <telession>1</telession>
    </HidroInventario>
  </soap:Body>
</soap:Envelope>"""

SOAP_TELEMETRIA = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <DadosHidroTelemetria xmlns="http://ana.gov.br/">
      <codEstacao>{cod_estacao}</codEstacao>
      <dataInicio>{data_inicio}</dataInicio>
      <dataFim>{data_fim}</dataFim>
    </DadosHidroTelemetria>
  </soap:Body>
</soap:Envelope>"""


class ANAClient:
    """Cliente HTTP para o web service SOAP da ANA."""

    def __init__(self, timeout: float = 60.0):
        self.timeout = timeout
        self.headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "User-Agent": "AlertaBR/1.0 (plataforma de prevencao a desastres)",
        }

    async def get_inventario_estacoes(
        self,
        tipo_estacao: int = 1,
        estado: str = "",
        cod_estacao_de: str = "",
        cod_estacao_ate: str = "",
    ) -> List[Dict]:
        """
        Busca inventário de estações hidrológicas.

        Args:
            tipo_estacao: 1=Fluviométrica, 2=Pluviométrica
            estado: Filtrar por estado (nome completo ou vazio para todos)
            cod_estacao_de: Código inicial para filtro de range
            cod_estacao_ate: Código final para filtro de range

        Returns:
            Lista de dicts com dados das estações
        """
        body = SOAP_INVENTARIO.format(
            tipo_estacao=tipo_estacao,
            estado=estado,
            cod_estacao_de=cod_estacao_de,
            cod_estacao_ate=cod_estacao_ate,
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(3):
                try:
                    response = await client.post(
                        ANA_WS_URL,
                        content=body,
                        headers={
                            **self.headers,
                            "SOAPAction": "http://ana.gov.br/HidroInventario",
                        },
                    )
                    response.raise_for_status()
                    return self._parse_inventario(response.text)
                except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError) as e:
                    logger.warning(f"ANA inventário tentativa {attempt + 1}/3 falhou: {e}")
                    if attempt == 2:
                        raise
                    await asyncio.sleep(3 * (attempt + 1))
        return []

    async def get_telemetria(
        self, cod_estacao: str, data_inicio: str, data_fim: str
    ) -> List[Dict]:
        """
        Busca dados de telemetria (nível, vazão, chuva) de uma estação.

        Args:
            cod_estacao: Código da estação ANA
            data_inicio: Data no formato DD/MM/YYYY
            data_fim: Data no formato DD/MM/YYYY

        Returns:
            Lista de dicts com medições
        """
        body = SOAP_TELEMETRIA.format(
            cod_estacao=cod_estacao,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(3):
                try:
                    response = await client.post(
                        ANA_WS_URL,
                        content=body,
                        headers={
                            **self.headers,
                            "SOAPAction": "http://ana.gov.br/DadosHidroTelemetria",
                        },
                    )
                    response.raise_for_status()
                    return self._parse_telemetria(response.text)
                except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError) as e:
                    logger.warning(
                        f"ANA telemetria {cod_estacao} tentativa {attempt + 1}/3: {e}"
                    )
                    if attempt == 2:
                        raise
                    await asyncio.sleep(2 * (attempt + 1))
        return []

    def _parse_inventario(self, xml_text: str) -> List[Dict]:
        """Parseia resposta SOAP do HidroInventario."""
        try:
            parsed = xmltodict.parse(xml_text)
            # Navegar na estrutura SOAP
            envelope = parsed.get("soap:Envelope", parsed.get("Envelope", {}))
            body = envelope.get("soap:Body", envelope.get("Body", {}))
            response = body.get(
                "HidroInventarioResponse",
                body.get("ns1:HidroInventarioResponse", {}),
            )
            result = response.get(
                "HidroInventarioResult",
                response.get("ns1:HidroInventarioResult", {}),
            )

            # Os dados podem estar em diferentes caminhos dependendo da versão
            table = result.get("DocumentElement", result.get("NewDataSet", {}))
            if not table:
                # Tentar buscar diretamente
                table = result

            estacoes = table.get("Table", [])
            if isinstance(estacoes, dict):
                estacoes = [estacoes]

            return estacoes
        except Exception as e:
            logger.error(f"Erro ao parsear inventário ANA: {e}")
            return []

    def _parse_telemetria(self, xml_text: str) -> List[Dict]:
        """Parseia resposta SOAP do DadosHidroTelemetria."""
        try:
            parsed = xmltodict.parse(xml_text)
            envelope = parsed.get("soap:Envelope", parsed.get("Envelope", {}))
            body = envelope.get("soap:Body", envelope.get("Body", {}))
            response = body.get(
                "DadosHidroTelemetriaResponse",
                body.get("ns1:DadosHidroTelemetriaResponse", {}),
            )
            result = response.get(
                "DadosHidroTelemetriaResult",
                response.get("ns1:DadosHidroTelemetriaResult", {}),
            )

            table = result.get("DocumentElement", result.get("NewDataSet", {}))
            if not table:
                table = result

            dados = table.get("DadosHidroTelemetria", [])
            if isinstance(dados, dict):
                dados = [dados]

            return dados
        except Exception as e:
            logger.error(f"Erro ao parsear telemetria ANA: {e}")
            return []


class ANAIngestService:
    """Serviço de ingestão de dados hidrológicos da ANA."""

    def __init__(self):
        self.client = ANAClient()

    async def ingest_estacoes(
        self, db: AsyncSession, estado: str = "", tipo: int = 1
    ) -> int:
        """
        Ingere estações fluviométricas do inventário da ANA.

        Args:
            db: Sessão do banco
            estado: Nome do estado para filtrar (vazio = todos)
            tipo: 1=Fluviométrica, 2=Pluviométrica

        Returns:
            Número de estações inseridas/atualizadas
        """
        estacoes_data = await self.client.get_inventario_estacoes(
            tipo_estacao=tipo, estado=estado
        )
        count = 0

        for est in estacoes_data:
            codigo = est.get("Codigo", est.get("CodEstacao", "")).strip()
            if not codigo:
                continue

            # Verificar se já existe
            existing = await db.execute(
                select(EstacaoHidrologica).where(
                    EstacaoHidrologica.codigo_ana == codigo
                )
            )
            estacao_obj = existing.scalar_one_or_none()

            lat = self._parse_float(est.get("Latitude"))
            lon = self._parse_float(est.get("Longitude"))
            nome = est.get("Nome", est.get("NomeEstacao", "")).strip()
            rio = est.get("RioNome", est.get("NomeRio", "")).strip()
            bacia = est.get("BaciaCodigo", est.get("Bacia", "")).strip()
            sub_bacia = est.get("SubBaciaCodigo", est.get("SubBacia", "")).strip()

            # Buscar município mais próximo
            municipio_id = None
            if lat and lon:
                municipio_id = await self._find_nearest_municipality(db, lat, lon)

            # Parsear limiares de alerta (quando disponíveis)
            nivel_atencao = self._parse_float(est.get("NivelAtencao"))
            nivel_alerta = self._parse_float(est.get("NivelAlerta"))
            nivel_emergencia = self._parse_float(
                est.get("NivelEmergencia", est.get("NivelInundacao"))
            )

            tipo_str = "Fluviometrica" if tipo == 1 else "Pluviometrica"

            if estacao_obj:
                # Atualizar dados existentes
                estacao_obj.nome = nome or estacao_obj.nome
                estacao_obj.rio_nome = rio or estacao_obj.rio_nome
                if lat and lon:
                    estacao_obj.coordenada = f"SRID=4326;POINT({lon} {lat})"
                if municipio_id:
                    estacao_obj.municipio_id = municipio_id
                if nivel_atencao is not None:
                    estacao_obj.nivel_atencao = nivel_atencao
                if nivel_alerta is not None:
                    estacao_obj.nivel_alerta = nivel_alerta
                if nivel_emergencia is not None:
                    estacao_obj.nivel_emergencia = nivel_emergencia
                estacao_obj.ativa = est.get("StatusEstacao", "1") == "1"
                count += 1
            else:
                coordenada = f"SRID=4326;POINT({lon} {lat})" if lat and lon else None
                estacao = EstacaoHidrologica(
                    codigo_ana=codigo,
                    nome=nome,
                    municipio_id=municipio_id,
                    coordenada=coordenada,
                    rio_nome=rio,
                    bacia=bacia,
                    sub_bacia=sub_bacia,
                    tipo=tipo_str,
                    ativa=est.get("StatusEstacao", "1") == "1",
                    nivel_atencao=nivel_atencao,
                    nivel_alerta=nivel_alerta,
                    nivel_emergencia=nivel_emergencia,
                )
                db.add(estacao)
                count += 1

        await db.commit()
        logger.info(f"ANA: ingeridas/atualizadas {count} estações hidrológicas")
        return count

    async def ingest_telemetria_recente(
        self, db: AsyncSession, horas: int = 6
    ) -> int:
        """
        Ingere dados de telemetria das últimas N horas de todas as estações ativas.

        Args:
            db: Sessão do banco
            horas: Janela de horas para buscar (default 6h)

        Returns:
            Número de medições inseridas
        """
        result = await db.execute(
            select(EstacaoHidrologica).where(EstacaoHidrologica.ativa == True)
        )
        estacoes = result.scalars().all()

        if not estacoes:
            logger.warning("ANA: nenhuma estação hidrológica ativa encontrada")
            return 0

        now = datetime.now(timezone.utc)
        data_fim = now.strftime("%d/%m/%Y")
        data_inicio = (now - timedelta(hours=horas)).strftime("%d/%m/%Y")

        count = 0
        for estacao in estacoes:
            try:
                dados = await self.client.get_telemetria(
                    estacao.codigo_ana, data_inicio, data_fim
                )
                inserted = await self._process_telemetria(db, estacao.id, dados)
                count += inserted
            except Exception as e:
                logger.warning(f"ANA telemetria estação {estacao.codigo_ana}: {e}")
                continue

            # Rate limiting: pequeno delay entre requests
            await asyncio.sleep(0.5)

        await db.commit()
        logger.info(f"ANA: ingeridas {count} medições hidrológicas")
        return count

    async def _process_telemetria(
        self, db: AsyncSession, estacao_id: int, dados: List[Dict]
    ) -> int:
        """Processa e insere medições de telemetria de uma estação."""
        count = 0
        for registro in dados:
            try:
                # O campo pode variar: DataHora, DataLeitura, etc.
                data_hora_str = registro.get(
                    "DataHora", registro.get("DataLeitura", "")
                )
                if not data_hora_str:
                    continue

                # Parsear datetime (formatos comuns da ANA)
                data_hora = self._parse_datetime(data_hora_str)
                if not data_hora:
                    continue

                # Verificar duplicata
                existing = await db.execute(
                    select(MedicaoHidrologica).where(
                        MedicaoHidrologica.estacao_id == estacao_id,
                        MedicaoHidrologica.data_hora == data_hora,
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                nivel = self._parse_float(registro.get("Nivel", registro.get("NivelAgua")))
                vazao = self._parse_float(registro.get("Vazao"))
                chuva = self._parse_float(registro.get("Chuva", registro.get("Precipitacao")))

                # Pular registros sem dados úteis
                if nivel is None and vazao is None and chuva is None:
                    continue

                medicao = MedicaoHidrologica(
                    estacao_id=estacao_id,
                    data_hora=data_hora,
                    nivel=nivel,
                    vazao=vazao,
                    chuva=chuva,
                )
                db.add(medicao)
                count += 1
            except Exception as e:
                logger.debug(f"Erro ao processar medição hidrológica: {e}")
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
        """Converte valor para float, tratando valores inválidos."""
        if value is None or value == "" or value == "null" or value == "--":
            return None
        try:
            # A ANA às vezes usa vírgula como separador decimal
            if isinstance(value, str):
                value = value.replace(",", ".")
            result = float(value)
            # Valores absurdos (sensor com defeito)
            if result < -9000 or result > 99999:
                return None
            return result
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_datetime(value: str) -> Optional[datetime]:
        """Parseia datetime em formatos comuns da ANA."""
        if not value:
            return None

        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%Y-%m-%dT%H:%M:%S.%f",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(value.strip(), fmt)
                # Assumir UTC-3 (horário de Brasília) e converter para UTC
                dt = dt.replace(tzinfo=timezone(timedelta(hours=-3)))
                return dt.astimezone(timezone.utc)
            except ValueError:
                continue

        logger.debug(f"Formato de data não reconhecido: {value}")
        return None
