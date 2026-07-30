from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from app.database import Base


class Estado(Base):
    __tablename__ = "estados"

    id = Column(Integer, primary_key=True, index=True)
    codigo_ibge = Column(Integer, unique=True, nullable=False, index=True)
    nome = Column(String(100), nullable=False)
    sigla = Column(String(2), unique=True, nullable=False, index=True)
    regiao = Column(String(20))
    geometria = Column(Geometry("MULTIPOLYGON", srid=4326))

    municipios = relationship("Municipio", back_populates="estado", lazy="selectin")

    def __repr__(self):
        return f"<Estado {self.sigla} - {self.nome}>"


class Municipio(Base):
    __tablename__ = "municipios"

    id = Column(Integer, primary_key=True, index=True)
    codigo_ibge = Column(Integer, unique=True, nullable=False, index=True)
    nome = Column(String(200), nullable=False)
    estado_id = Column(Integer, ForeignKey("estados.id"), nullable=False, index=True)
    geometria = Column(Geometry("MULTIPOLYGON", srid=4326))
    area_km2 = Column(Float)
    em_vale = Column(Boolean, default=False)

    estado = relationship("Estado", back_populates="municipios")
    estacoes = relationship("EstacaoMeteorologica", back_populates="municipio", lazy="selectin")
    dados_demograficos = relationship("DadosDemograficos", back_populates="municipio", lazy="selectin")
    alertas = relationship("Alerta", back_populates="municipio", lazy="selectin")

    def __repr__(self):
        return f"<Municipio {self.codigo_ibge} - {self.nome}>"
