import logging
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

# Importamos a infraestrutura do banco e os modelos/schemas
from app.core.database import engine, Base, get_db
from app.models import models
from app.models.schemas import schemas

# Configuração de logging para vermos o que acontece no terminal do Docker
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Tenta criar as tabelas no banco de dados assim que o script inicia
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Tabelas criadas ou verificadas com sucesso no Supabase.")
except Exception as e:
    logger.error(f"Erro ao conectar no banco de dados durante o startup: {e}")

app = FastAPI(title="Monitor de Gastos API")

@app.get("/")
def read_root():
    """Rota inicial para verificar se a API está online."""
    return {"message": "Monitor de Gastos API está rodando!"}

@app.post("/gastos/", response_model=schemas.GastoResponse)
def criar_gasto(gasto: schemas.GastoCreate, db: Session = Depends(get_db)):
    """
    Endpoint para cadastrar um novo gasto.
    Recebe os dados validados pelo Pydantic (schemas.GastoCreate)
    e salva no Postgres via SQLAlchemy (models.Gasto).
    """
    try:
        # Converte o schema do Pydantic em um modelo do SQLAlchemy
        novo_gasto = models.Gasto(**gasto.model_dump())
        
        db.add(novo_gasto)
        db.commit()
        db.refresh(novo_gasto) # Atualiza o objeto com o ID gerado pelo banco
        
        return novo_gasto
    except Exception as e:
        db.rollback() # Cancela a operação se algo der errado
        logger.error(f"Erro ao salvar gasto: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao salvar o gasto.")