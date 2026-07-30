"""Serviço de gerenciamento de alertas."""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.geographic import Municipio, Estado
from app.models.alerts import Alerta
from app.services.risk_engine import RiskEngine

logger = logging.getLogger(__name__)


class AlertService:
    """Gerencia geração e lifecycle de alertas."""

    def __init__(self):
        self.engine = RiskEngine()

    async def process_alerts_for_state(
        self, state_sigla: str, db: AsyncSession
    ) -> dict:
        """Avalia todos os municípios de um estado e gera/atualiza alertas."""
        result = await db.execute(
            select(Estado).where(Estado.sigla == state_sigla.upper())
        )
        estado = result.scalar_one_or_none()
        if not estado:
            return {"error": f"Estado {state_sigla} não encontrado"}

        result = await db.execute(
            select(Municipio.id).where(Municipio.estado_id == estado.id)
        )
        municipio_ids = [row[0] for row in result.all()]

        created = 0
        updated = 0
        deactivated = 0

        for mun_id in municipio_ids:
            risk = await self.engine.calculate_risk(mun_id, db)

            if risk.classification in ("alto", "critico"):
                result = await self._create_or_update_alert(db, mun_id, risk)
                if result == "created":
                    created += 1
                elif result == "updated":
                    updated += 1
            else:
                count = await self._deactivate_alerts(db, mun_id)
                deactivated += count

        await db.commit()
        return {
            "created": created,
            "updated": updated,
            "deactivated": deactivated,
            "total_evaluated": len(municipio_ids),
        }

    async def _create_or_update_alert(self, db, municipio_id, risk) -> str:
        """Cria alerta novo ou atualiza existente (de-duplicação)."""
        existing = await db.execute(
            select(Alerta).where(
                Alerta.municipio_id == municipio_id,
                Alerta.tipo == risk.primary_type,
                Alerta.ativo == True,
            )
        )
        existing_alert = existing.scalar_one_or_none()

        if existing_alert:
            existing_alert.indice_risco = risk.index
            existing_alert.severidade = risk.classification
            existing_alert.regras_ativadas = risk.triggered_rules
            return "updated"
        else:
            new_alert = Alerta(
                municipio_id=municipio_id,
                tipo=risk.primary_type,
                severidade=risk.classification,
                indice_risco=risk.index,
                descricao=f"Alerta de {risk.primary_type} - Índice: {risk.index}",
                regras_ativadas=risk.triggered_rules,
                data_inicio=datetime.now(timezone.utc),
                ativo=True,
            )
            db.add(new_alert)
            return "created"

    async def _deactivate_alerts(self, db, municipio_id: int) -> int:
        """Desativa alertas quando risco volta ao normal."""
        result = await db.execute(
            select(Alerta).where(
                Alerta.municipio_id == municipio_id,
                Alerta.ativo == True,
            )
        )
        alerts = result.scalars().all()
        for alert in alerts:
            alert.ativo = False
            alert.data_fim = datetime.now(timezone.utc)
        return len(alerts)
