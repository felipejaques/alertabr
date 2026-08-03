"""Add hydrological tables (ANA)

Revision ID: 002
Revises: 001
Create Date: 2024-08-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Estações Hidrológicas (ANA)
    op.create_table(
        "estacoes_hidrologicas",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("codigo_ana", sa.String(20), unique=True, nullable=False, index=True),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("municipio_id", sa.Integer(), sa.ForeignKey("municipios.id"), index=True),
        sa.Column("coordenada", geoalchemy2.Geometry("POINT", srid=4326)),
        sa.Column("rio_nome", sa.String(200)),
        sa.Column("bacia", sa.String(200)),
        sa.Column("sub_bacia", sa.String(200)),
        sa.Column("tipo", sa.String(30)),
        sa.Column("ativa", sa.Boolean(), default=True),
        sa.Column("nivel_atencao", sa.Float()),
        sa.Column("nivel_alerta", sa.Float()),
        sa.Column("nivel_emergencia", sa.Float()),
    )

    # Medições Hidrológicas
    op.create_table(
        "medicoes_hidrologicas",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "estacao_id",
            sa.Integer(),
            sa.ForeignKey("estacoes_hidrologicas.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("data_hora", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("nivel", sa.Float()),
        sa.Column("vazao", sa.Float()),
        sa.Column("chuva", sa.Float()),
    )

    # Índice espacial GiST para estações hidrológicas
    op.create_index(
        "idx_estacoes_hidro_coordenada",
        "estacoes_hidrologicas",
        ["coordenada"],
        postgresql_using="gist",
    )

    # Índice composto para queries de medições por estação e data
    op.create_index(
        "idx_medicoes_hidro_estacao_data",
        "medicoes_hidrologicas",
        [sa.text("estacao_id"), sa.text("data_hora DESC")],
    )


def downgrade() -> None:
    op.drop_index("idx_medicoes_hidro_estacao_data", table_name="medicoes_hidrologicas")
    op.drop_index("idx_estacoes_hidro_coordenada", table_name="estacoes_hidrologicas")
    op.drop_table("medicoes_hidrologicas")
    op.drop_table("estacoes_hidrologicas")
