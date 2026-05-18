import logging
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List

# Importamos a infraestrutura do banco e os modelos/schemas
from app.core.database import engine, Base, get_db
from app.models import models
from app.models.schemas import schemas
from app.core import security, deps

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

# Configuração de CORS para o Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    """Rota inicial para verificar se a API está online."""
    return {"message": "Monitor de Gastos API está rodando!"}

# --- Rotas de Autenticação ---

@app.post("/register", response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = security.get_password_hash(user.password)
    new_user = models.User(
        email=user.email, 
        hashed_password=hashed_password,
        nome=user.nome,
        telefone=user.telefone
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(deps.get_current_user)):
    """
    Retorna os dados do usuário atualmente logado.
    """
    return current_user

# --- Rotas de Gastos ---

@app.post("/gastos/", response_model=schemas.GastoResponse)
def criar_gasto(
    gasto: schemas.GastoCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Endpoint para cadastrar um novo gasto.
    Recebe os dados validados pelo Pydantic e salva associado ao usuário autenticado.
    """
    try:
        # Converte o schema do Pydantic em um modelo do SQLAlchemy associando ao usuário
        novo_gasto = models.Gasto(**gasto.model_dump(), user_id=current_user.id)
        
        db.add(novo_gasto)
        db.commit()
        db.refresh(novo_gasto) # Atualiza o objeto com o ID gerado pelo banco
        
        return novo_gasto
    except Exception as e:
        db.rollback() # Cancela a operação se algo der errado
        logger.error(f"Erro ao salvar gasto: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao salvar o gasto.")

@app.get("/gastos/", response_model=List[schemas.GastoResponse])
def listar_gastos(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Lista todos os gastos vinculados ao usuário autenticado.
    """
    gastos = db.query(models.Gasto).filter(models.Gasto.user_id == current_user.id).all()
    return gastos

@app.put("/gastos/{gasto_id}", response_model=schemas.GastoResponse)
def atualizar_gasto(
    gasto_id: int,
    gasto_atualizado: schemas.GastoUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Atualiza um gasto existente. Garante que só o dono possa atualizar.
    """
    db_gasto = db.query(models.Gasto).filter(
        models.Gasto.id == gasto_id, 
        models.Gasto.user_id == current_user.id
    ).first()
    
    if not db_gasto:
        raise HTTPException(status_code=404, detail="Gasto não encontrado")
    
    update_data = gasto_atualizado.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_gasto, key, value)
        
    db.commit()
    db.refresh(db_gasto)
    return db_gasto

@app.delete("/gastos/{gasto_id}")
def deletar_gasto(
    gasto_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Deleta um gasto existente. Garante que só o dono possa deletar.
    """
    db_gasto = db.query(models.Gasto).filter(
        models.Gasto.id == gasto_id, 
        models.Gasto.user_id == current_user.id
    ).first()
    
    if not db_gasto:
        raise HTTPException(status_code=404, detail="Gasto não encontrado")
        
    db.delete(db_gasto)
    db.commit()
    return {"detail": "Gasto deletado com sucesso"}