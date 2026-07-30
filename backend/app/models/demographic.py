from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class DadosDemograficos(Base):
    __tablename__ = "dados_demograficos"

    id = Column(Integer, primary_key=True, index=True)
    municipio_id = Column(Integer, ForeignKey("municipios.id"), nullable=False, index=True)
    populacao = Column(Integer)
    densidade_demografica = Column(Float)
    pct_idosos = Column(Float)  # % população 60+
    pct_baixa_renda = Column(Float)  # % abaixo de 1/2 SM
    idh = Column(Float)
    pct_esgoto = Column(Float)  # % domicílios com esgoto
    indice_vulnerabilidade = Column(Float)  # calculado (0-100)
    ano_referencia = Column(Integer)

    municipio = relationship("Municipio", back_populates="dados_demograficos")

    def __repr__(self):
        return f"<DadosDemograficos municipio={self.municipio_id} ano={self.ano_referencia}>"
