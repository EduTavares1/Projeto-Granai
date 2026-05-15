from sqlalchemy import Column, Integer, Float, String, DateTime
from datetime import datetime
from app.core.database import Base

class Gasto(Base):
    __tablename__ = "gastos"

    id = Column(Integer, primary_key=True, index=True)
    valor = Column(Float, nullable=False)
    descricao = Column(String, nullable=False)
    categoria = Column(String, default="Outros")
    data_registro = Column(DateTime, default=datetime.utcnow)
    user_id = Column(String) 