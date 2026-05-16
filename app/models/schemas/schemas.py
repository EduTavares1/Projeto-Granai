from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

# --- Schemas de Usuário ---

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    is_active: bool

    class Config:
        from_attributes = True

# --- Schemas de Token ---

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# --- Schemas de Gasto ---

# Schema para DADOS QUE ENTRAM (O que o usuário envia)
class GastoCreate(BaseModel):
    valor: float
    descricao: str
    categoria: Optional[str] = "Geral"

class GastoUpdate(BaseModel):
    valor: Optional[float] = None
    descricao: Optional[str] = None
    categoria: Optional[str] = None

# Schema para DADOS QUE SAEM (O que a API devolve)
class GastoResponse(GastoCreate):
    id: int
    data_registro: datetime
    user_id: int

    class Config:
        from_attributes = True