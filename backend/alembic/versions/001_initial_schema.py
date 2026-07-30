"""Initial schema - tabelas geoespaciais

Revision ID: 001
Revises: None
Create Date: 2024-07-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Habilitar PostGIS
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # Estados
    op.create_table(
        "estados",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("codigo_ibge", sa.Integer(), unique=True, nullable=False, index=True),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("sigla", sa.String(2), unique=True, nullable=False, index=True),
        sa.Column("regiao", sa.String(20)),
        sa.Column("geometria", geoalchemy2.Geometry("MULTIPOLYGON", srid=4326)),
    )

    # Municípios
    op.create_table(
        "municipios",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("codigo_ibge", sa.Integer(), unique=True, nullable=False, index=True),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("estado_id", sa.Integer(), sa.ForeignKey("estados.id"), nullable=False, index=True),
        sa.Column("geometria", geoalchemy2.Geometry("MULTIPOLYGON", srid=4326)),
        sa.Column("area_km2", sa.Float()),
        sa.Column("em_vale", sa.Boolean(), default=False),
    )

    # Estações Meteorológicas
    op.create_table(
        "estacoes_meteorologicas",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("codigo_inmet", sa.String(10), unique=True, nullable=False, index=True),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("municipio_id", sa.Integer(), sa.ForeignKey("municipios.id"), index=True),
        sa.Column("coordenada", geoalchemy2.Geometry("POINT", srid=4326), nullable=False),
        sa.Column("altitude", sa.Float()),
        sa.Column("tipo", sa.String(20)),
        sa.Column("ativa", sa.Boolean(), default=True),
    )

    # Medições Climáticas
    op.create_table(
        "medicoes_climaticas",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("estacao_id", sa.Integer(), sa.ForeignKey("estacoes_meteorologicas.id"), nullable=False, index=True),
        sa.Column("data_hora", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("temperatura", sa.Float()),
        sa.Column("temperatura_max", sa.Float()),
        sa.Column("temperatura_min", sa.Float()),
        sa.Column("precipitacao", sa.Float()),
        sa.Column("umidade", sa.Float()),
        sa.Column("vento_velocidade", sa.Float()),
        sa.Column("vento_direcao", sa.Integer()),
        sa.Column("pressao", sa.Float()),
        sa.Column("radiacao", sa.Float()),
    )

    # Dados Demográficos
    op.create_table(
        "dados_demograficos",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("municipio_id", sa.Integer(), sa.ForeignKey("municipios.id"), nullable=False, index=True),
        sa.Column("populacao", sa.Integer()),
        sa.Column("densidade_demografica", sa.Float()),
        sa.Column("pct_idosos", sa.Float()),
        sa.Column("pct_baixa_renda", sa.Float()),
        sa.Column("idh", sa.Float()),
        sa.Column("pct_esgoto", sa.Float()),
        sa.Column("indice_vulnerabilidade", sa.Float()),
        sa.Column("ano_referencia", sa.Integer()),
    )

    # Alertas
    op.create_table(
        "alertas",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("municipio_id", sa.Integer(), sa.ForeignKey("municipios.id"), nullable=False, index=True),
        sa.Column("tipo", sa.String(50), nullable=False),
        sa.Column("severidade", sa.String(20), nullable=False),
        sa.Column("indice_risco", sa.Float()),
        sa.Column("descricao", sa.Text()),
        sa.Column("regras_ativadas", sa.JSON()),
        sa.Column("data_inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_fim", sa.DateTime(timezone=True)),
        sa.Column("ativo", sa.Boolean(), default=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Índices espaciais GiST
    op.create_index("idx_estados_geometria", "estados", ["geometria"], postgresql_using="gist")
    op.create_index("idx_municipios_geometria", "municipios", ["geometria"], postgresql_using="gist")
    op.create_index("idx_estacoes_coordenada", "estacoes_meteorologicas", ["coordenada"], postgresql_using="gist")

    # Índices compostos para queries frequentes
    op.create_index(
        "idx_medicoes_estacao_data",
        "medicoes_climaticas",
        [sa.text("estacao_id"), sa.text("data_hora DESC")],
    )
    op.create_index(
        "idx_alertas_municipio_ativo",
        "alertas",
        ["municipio_id", "ativo"],
        postgresql_where=sa.text("ativo = true"),
    )


def downgrade() -> None:
    op.drop_table("alertas")
    op.drop_table("dados_demograficos")
    op.drop_table("medicoes_climaticas")
    op.drop_table("estacoes_meteorologicas")
    op.drop_table("municipios")
    op.drop_table("estados")
    op.execute("DROP EXTENSION IF EXISTS postgis")
