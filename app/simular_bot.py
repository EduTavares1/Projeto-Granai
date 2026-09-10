import os
import sys
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Ajusta o PYTHONPATH para importar a pasta app corretamente
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models import models
from app.services import bot

def main():
    print("==================================================")
    print("🤖  SIMULADOR CLI — BOT FINANCEIRO TRILL  🤖")
    print("==================================================")
    
    # 1. Abre a sessão do banco de dados
    db = SessionLocal()
    
    # 2. Busca ou cria um usuário de teste
    email_teste = "test_cli@trill.com.br"
    user = db.query(models.User).filter(models.User.email == email_teste).first()
    
    if not user:
        print(f"[*] Criando usuário de teste '{email_teste}' no banco...")
        from app.core.security import get_password_hash
        user = models.User(
            email=email_teste,
            hashed_password=get_password_hash("password123"),
            nome="Usuário Teste CLI",
            telefone="558192441512",
            meta_mensal=1000.0
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print("✅ Usuário criado com sucesso!")
    
    print(f"👤 Usuário: {user.nome}")
    print(f"📞 Telefone cadastrado: {user.telefone}")
    print(f"🎯 Meta Mensal Atual: R$ {user.meta_mensal:.2f}")
    print("\nDigite suas mensagens abaixo para simular a conversa.")
    print("Digite 'sair' para encerrar o simulador.")
    print("==================================================\n")
    
    try:
        while True:
            # Entrada do usuário
            try:
                texto = input("Você > ").strip()
            except KeyboardInterrupt:
                break
                
            if not texto:
                continue
            if texto.lower() in ["sair", "exit"]:
                break
                
            # Executa a análise com o Gemini (ou fallback regex)
            gemini_analise = None
            if bot.GEMINI_KEY:
                gemini_analise = bot.analisar_com_gemini(texto)
                intencao = gemini_analise.get("intent", "desconhecido")
                print(f"\n[AI] Intenção detectada pelo Gemini: {intencao}")
                print(f"[AI] Dados extraídos: {gemini_analise}")
            else:
                intencao = bot.parse_intencao(texto)
                print(f"\n[Fallback] Intenção detectada por Regex: {intencao}")
                
            # Executa a lógica da intenção
            try:
                resposta = bot._executar_intencao(db, user, intencao, texto, gemini_analise)
                db.refresh(user)
            except Exception as e:
                resposta = f"⚠️ Erro ao processar a ação: {e}"
                
            print(f"\nBot > {resposta}")
            print(f"🎯 Meta Mensal Atual: R$ {user.meta_mensal:.2f}")
            print("-" * 50 + "\n")
            
    finally:
        db.close()
        print("\nSessão encerrada. Até logo!")

if __name__ == "__main__":
    main()
