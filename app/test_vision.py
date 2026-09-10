import os
import sys
import json

# Adiciona o diretório raiz ao path para encontrar o pacote 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services import vision

def testar_imagem_comprovante(caminho_imagem: str):
    print(f"\n==================================================")
    print(f"🚀 Iniciando teste de Visão Computacional / OCR")
    print(f"📁 Imagem: {caminho_imagem}")
    print(f"==================================================")

    if not os.path.exists(caminho_imagem):
        print(f"❌ Erro: O arquivo '{caminho_imagem}' não existe!")
        return

    # 1. Lendo os bytes da imagem
    with open(caminho_imagem, "rb") as f:
        img_bytes = f.read()

    # 2. Executando OCR
    print("\n[Passo 1] Executando pipeline do OpenCV e Tesseract OCR...")
    # Como rodamos localmente, as imagens de depuração serão salvas em ./debug_vision no host
    # Vamos sobreescrever o diretório de debug para ser local ao script de teste
    vision.DEBUG_DIR = "./debug_vision"
    
    texto_extraido = vision.extrair_texto_da_imagem(img_bytes, save_debug=True)

    print("\n--- TEXTO BRUTO DETECTADO ---")
    if texto_extraido.strip():
        print(texto_extraido)
    else:
        print("[Nenhum texto detectado]")
    print("-----------------------------")

    # 3. Analisando dados financeiros
    print("\n[Passo 2] Extraindo informações financeiras...")
    dados = vision.extrair_dados_financeiros(texto_extraido)

    print("\n--- RESULTADO DA EXTRAÇÃO ---")
    print(json.dumps(dados, indent=4, ensure_ascii=False))
    print("-----------------------------")
    print(f"📁 Imagens de depuração salvas em: {os.path.abspath('./debug_vision')}")
    print(f"==================================================\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python app/test_vision.py <caminho_da_imagem>")
        # Procura um comprovante padrão na pasta
        padrao = "receipt_test.jpg"
        if os.path.exists(padrao):
            print(f"Usando imagem padrão: {padrao}")
            testar_imagem_comprovante(padrao)
        else:
            sys.exit(1)
    else:
        testar_imagem_comprovante(sys.argv[1])
