from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# Schema para DADOS QUE ENTRAM (O que o usuário envia)
class GastoCreate(BaseModel):
    valor: float
    descricao: str
    categoria: Optional[str] = "Geral"

# Schema para DADOS QUE SAEM (O que a API devolve)
class GastoResponse(GastoCreate):
    id: int
    data_registro: datetime

    class Config:
        from_attributes = True