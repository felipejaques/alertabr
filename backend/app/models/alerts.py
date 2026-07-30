from sqlalchemy import Column, Integer, String, Float, Boolean, Text, ForeignKey, DateTime, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Alerta(Base):
    __tablename__ = "alertas"

    id = Column(Integer, primary_key=True, index=True)
    municipio_id = Column(Integer, ForeignKey("municipios.id"), nullable=False, index=True)
    tipo = Column(String(50), nullable=False)  # inundacao, calor, vendaval, seca
    severidade = Column(String(20), nullable=False)  # baixo, moderado, alto, critico
    indice_risco = Column(Float)
    descricao = Column(Text)
    regras_ativadas = Column(JSON)  # lista de regras que dispararam
    data_inicio = Column(DateTime(timezone=True), nullable=False)
    data_fim = Column(DateTime(timezone=True))
    ativo = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    municipio = relationship("Municipio", back_populates="alertas")

    def __repr__(self):
        return f"<Alerta {self.tipo} {self.severidade} municipio={self.municipio_id}>"
