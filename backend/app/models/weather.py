from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from app.database import Base


class EstacaoMeteorologica(Base):
    __tablename__ = "estacoes_meteorologicas"

    id = Column(Integer, primary_key=True, index=True)
    codigo_inmet = Column(String(10), unique=True, nullable=False, index=True)
    nome = Column(String(200), nullable=False)
    municipio_id = Column(Integer, ForeignKey("municipios.id"), index=True)
    coordenada = Column(Geometry("POINT", srid=4326), nullable=False)
    altitude = Column(Float)
    tipo = Column(String(20))  # Automatica, Convencional
    ativa = Column(Boolean, default=True)

    municipio = relationship("Municipio", back_populates="estacoes")
    medicoes = relationship("MedicaoClimatica", back_populates="estacao", lazy="selectin")

    def __repr__(self):
        return f"<Estacao {self.codigo_inmet} - {self.nome}>"


class MedicaoClimatica(Base):
    __tablename__ = "medicoes_climaticas"

    id = Column(Integer, primary_key=True, index=True)
    estacao_id = Column(Integer, ForeignKey("estacoes_meteorologicas.id"), nullable=False, index=True)
    data_hora = Column(DateTime(timezone=True), nullable=False, index=True)
    temperatura = Column(Float)
    temperatura_max = Column(Float)
    temperatura_min = Column(Float)
    precipitacao = Column(Float)
    umidade = Column(Float)
    vento_velocidade = Column(Float)
    vento_direcao = Column(Integer)
    pressao = Column(Float)
    radiacao = Column(Float)

    estacao = relationship("EstacaoMeteorologica", back_populates="medicoes")

    def __repr__(self):
        return f"<Medicao estacao={self.estacao_id} em {self.data_hora}>"
