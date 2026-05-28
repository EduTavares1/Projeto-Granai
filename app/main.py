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
from app.services import finance
from app.services import bot

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

@app.put("/users/me/meta", response_model=schemas.UserResponse)
def update_user_meta(
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Atualiza a meta mensal do usuário.
    """
    if user_update.meta_mensal is not None:
        current_user.meta_mensal = user_update.meta_mensal
        db.commit()
        db.refresh(current_user)
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
        novo_gasto = models.Gasto(**gasto.model_dump(exclude_unset=True), user_id=current_user.id)
        
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


# --- Rotas de Receitas ---

@app.post("/receitas/", response_model=schemas.ReceitaResponse)
def criar_receita(
    receita: schemas.ReceitaCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Endpoint para cadastrar uma nova receita.
    """
    try:
        return finance.criar_receita(db, receita, current_user.id)
    except Exception as e:
        logger.error(f"Erro ao salvar receita: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao salvar a receita.")


@app.get("/receitas/", response_model=List[schemas.ReceitaResponse])
def listar_receitas(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Lista todas as receitas vinculadas ao usuário autenticado.
    """
    return finance.get_receitas(db, current_user.id)


@app.delete("/receitas/{receita_id}")
def deletar_receita(
    receita_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Deleta uma receita existente. Garante que só o dono possa deletar.
    """
    sucesso = finance.deletar_receita(db, receita_id, current_user.id)
    if not sucesso:
        raise HTTPException(status_code=404, detail="Receita não encontrada")
    return {"detail": "Receita deletada com sucesso"}


@app.put("/receitas/{receita_id}", response_model=schemas.ReceitaResponse)
def atualizar_receita(
    receita_id: int,
    receita_atualizada: schemas.ReceitaUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Atualiza uma receita existente. Garante que só o dono possa atualizar.
    """
    db_receita = finance.atualizar_receita(db, receita_id, receita_atualizada, current_user.id)
    if not db_receita:
        raise HTTPException(status_code=404, detail="Receita não encontrada")
    return db_receita


# --- Rotas de Analytics ---

@app.get("/analytics/resumo-mensal")
def resumo_mensal(
    mes: int = None,
    ano: int = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Retorna o resumo financeiro de um mês específico:
    total gasto, nº de transações, meta, percentual e saldo restante.
    """
    return finance.get_resumo_mensal(db, current_user.id, mes=mes, ano=ano)


@app.get("/analytics/por-categoria")
def gastos_por_categoria(
    mes: int = None,
    ano: int = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Retorna os gastos agrupados por categoria no mês,
    ordenados do maior para o menor, com percentual sobre o total.
    """
    return finance.get_gastos_por_categoria(db, current_user.id, mes=mes, ano=ano)


@app.get("/analytics/status-meta")
def status_meta(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Retorna o status atual da meta mensal com uma mensagem legível.
    Status possíveis: seguro, atencao, alerta, estourado, sem_meta.
    """
    return finance.get_status_meta(db, current_user.id)


@app.get("/analytics/resumo-semanal")
def resumo_semanal(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Retorna o resumo de gastos da semana atual (segunda a domingo),
    incluindo média diária e projeção para o fim da semana.
    """
    return finance.get_resumo_semanal(db, current_user.id)


@app.get("/analytics/comparativo")
def comparativo_mensal(
    meses: int = 3,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Retorna o comparativo de gastos dos últimos N meses (padrão: 3),
    com variação percentual mês a mês.
    """
    return finance.get_comparativo_mensal(db, current_user.id, meses=meses)


@app.get("/analytics/completo")
def analytics_completo(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Consolida todos os dados de análise em um único payload.
    Ideal para o agente de IA ter contexto completo do usuário.
    """
    return finance.get_resumo_completo(db, current_user.id)


# --- Rota do Webhook WhatsApp (Evolution API) ---

@app.post("/webhook/whatsapp", status_code=200)
async def webhook_whatsapp(
    payload: dict,
    db: Session = Depends(get_db)
):
    """
    Recebe eventos da Evolution API (mensagens do WhatsApp).
    
    A Evolution API envia um POST neste endpoint sempre que
    uma nova mensagem chega na instância configurada.
    Este endpoint é público (sem JWT) pois a autenticação
    é feita pelo telefone cadastrado do usuário.
    """
    try:
        evento = payload.get("event", "")

        # Processa apenas eventos de mensagem recebida
        if evento != "messages.upsert":
            return {"status": "ignored", "event": evento}

        data = payload.get("data", {})
        mensagem = data.get("message", {})
        key = data.get("key", {})

        # Ignora mensagens enviadas pelo próprio bot (evita loop)
        if key.get("fromMe", False):
            return {"status": "ignored", "reason": "fromMe"}

        # Extrai o texto e o número do remetente
        texto = (
            mensagem.get("conversation")
            or mensagem.get("extendedTextMessage", {}).get("text")
            or ""
        ).strip()

        numero = key.get("remoteJid", "")

        if not texto or not numero:
            return {"status": "ignored", "reason": "empty message"}

        logger.info(f"[WEBHOOK] Mensagem de {numero}: {texto!r}")

        # Processa a mensagem (síncrono por ora, suficiente para v1)
        bot.processar_mensagem(db=db, numero=numero, texto=texto)

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"[WEBHOOK] Erro ao processar payload: {e}")
        # Retorna 200 mesmo com erro para a Evolution API não retentar
        return {"status": "error", "detail": str(e)}