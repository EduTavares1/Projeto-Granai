import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# O engine é o "motor" que gerencia a conexão
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Cada instância da classe SessionLocal será uma sessão de banco
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Classe base para criar os modelos (tabelas)
Base = declarative_base()

# Dependência que as rotas vão usar para garantir que o banco feche após a requisição
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

