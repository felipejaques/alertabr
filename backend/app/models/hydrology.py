"""Modelos SQLAlchemy para dados hidrológicos da ANA."""

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from app.database import Base


class EstacaoHidrologica(Base):
    """Estação fluviométrica/pluviométrica da ANA."""

    __tablename__ = "estacoes_hidrologicas"

    id = Column(Integer, primary_key=True, index=True)
    codigo_ana = Column(String(20), unique=True, nullable=False, index=True)
    nome = Column(String(200), nullable=False)
    municipio_id = Column(Integer, ForeignKey("municipios.id"), index=True)
    coordenada = Column(Geometry("POINT", srid=4326))
    rio_nome = Column(String(200))
    bacia = Column(String(200))
    sub_bacia = Column(String(200))
    tipo = Column(String(30))  # Fluviometrica, Pluviometrica
    ativa = Column(Boolean, default=True)
    nivel_atencao = Column(Float)  # Cota de atenção (metros)
    nivel_alerta = Column(Float)  # Cota de alerta (metros)
    nivel_emergencia = Column(Float)  # Cota de emergência (metros)

    municipio = relationship("Municipio", back_populates="estacoes_hidrologicas")
    medicoes = relationship(
        "MedicaoHidrologica", back_populates="estacao", lazy="selectin"
    )

    def __repr__(self):
        return f"<EstacaoHidrologica {self.codigo_ana} - {self.nome} ({self.rio_nome})>"


class MedicaoHidrologica(Base):
    """Medição hidrológica (nível, vazão, chuva) de uma estação."""

    __tablename__ = "medicoes_hidrologicas"

    id = Column(Integer, primary_key=True, index=True)
    estacao_id = Column(
        Integer, ForeignKey("estacoes_hidrologicas.id"), nullable=False, index=True
    )
    data_hora = Column(DateTime(timezone=True), nullable=False, index=True)
    nivel = Column(Float)  # Nível do rio em metros (cota)
    vazao = Column(Float)  # Vazão em m³/s
    chuva = Column(Float)  # Precipitação em mm

    estacao = relationship("EstacaoHidrologica", back_populates="medicoes")

    def __repr__(self):
        return f"<MedicaoHidrologica estacao={self.estacao_id} em {self.data_hora}>"
