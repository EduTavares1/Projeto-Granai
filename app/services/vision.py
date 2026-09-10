import os
import re
import cv2
import numpy as np
import pytesseract
import logging

logger = logging.getLogger(__name__)

# Diretório para salvar imagens de depuração (mapeado na raiz do projeto)
DEBUG_DIR = "/app/debug_vision"

def decodificar_imagem(img_bytes: bytes) -> np.ndarray:
    """Converte bytes brutos de uma imagem em uma matriz OpenCV (BGR)."""
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img

def preprocessar_imagem(img: np.ndarray, save_debug: bool = True) -> np.ndarray:
    """
    Aplica filtros de visão computacional para limpar o texto da imagem:
    1. Escala de cinza
    2. Redução de ruído (Gaussian Blur)
    3. Limiarização Binarizada (Adaptive Thresholding)
    """
    if save_debug:
        os.makedirs(DEBUG_DIR, exist_ok=True)
        cv2.imwrite(os.path.join(DEBUG_DIR, "01_original.jpg"), img)

    # 1. Escala de cinza
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if save_debug:
        cv2.imwrite(os.path.join(DEBUG_DIR, "02_cinza.jpg"), gray)

    # 2. Redução de ruído com desfoque de leve
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    if save_debug:
        cv2.imwrite(os.path.join(DEBUG_DIR, "03_desfocado.jpg"), blurred)

    # 3. Limiarização Adaptativa para destacar o texto e lidar com sombras
    # Ajusta o contraste local fazendo com que o texto fique bem escuro e o fundo branco
    binary = cv2.adaptiveThreshold(
        blurred, 
        255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 
        11, 
        2
    )
    if save_debug:
        cv2.imwrite(os.path.join(DEBUG_DIR, "04_binarizado.jpg"), binary)

    return binary

def extrair_texto_da_imagem(img_bytes: bytes, save_debug: bool = True) -> str:
    """
    Decodifica os bytes da imagem e tenta extrair o texto em duas etapas:
    1. Tenta direto em escala de cinza com PSM 6 (excelente para cupons digitais nítidos).
    2. Se não identificar um valor válido, aplica a binarização adaptativa OpenCV e tenta com PSM 6/4 (melhor para fotos com sombras).
    """
    try:
        img = decodificar_imagem(img_bytes)
        if img is None:
            logger.error("[VISION] Falha ao decodificar os bytes da imagem.")
            return ""

        # 1. Converter para escala de cinza
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Etapa 1: Tentar ler direto em escala de cinza com PSM 6
        logger.info("[VISION] Tentando OCR em escala de cinza (PSM 6)...")
        texto_gray = pytesseract.image_to_string(gray, lang="por", config="--oem 3 --psm 6")
        
        # Tenta extrair dados para ver se achou o valor da compra
        dados_gray = extrair_dados_financeiros(texto_gray)
        
        if dados_gray.get("valor") is not None:
            logger.info(f"[VISION] Sucesso na Etapa 1 (Grayscale). Valor extraído: R$ {dados_gray['valor']}")
            if save_debug:
                os.makedirs(DEBUG_DIR, exist_ok=True)
                cv2.imwrite(os.path.join(DEBUG_DIR, "01_original.jpg"), img)
                cv2.imwrite(os.path.join(DEBUG_DIR, "02_cinza.jpg"), gray)
                with open(os.path.join(DEBUG_DIR, "05_ocr_result.txt"), "w", encoding="utf-8") as f:
                    f.write(texto_gray)
            return texto_gray

        # Etapa 2 (Fallback): Aplicar binarização adaptativa para imagens com sombras/baixa qualidade
        logger.info("[VISION] Fallback: Iniciando binarização adaptativa OpenCV...")
        img_binarizada = preprocessar_imagem(img, save_debug=save_debug)
        
        logger.info("[VISION] Executando OCR na imagem binarizada (PSM 6)...")
        texto_bin = pytesseract.image_to_string(img_binarizada, lang="por", config="--oem 3 --psm 6")
        
        # Se falhar com PSM 6 na binarizada, tenta com PSM 4 como último recurso
        dados_bin = extrair_dados_financeiros(texto_bin)
        if dados_bin.get("valor") is None:
            logger.info("[VISION] OCR Binarizado PSM 6 falhou em achar valor. Tentando PSM 4...")
            texto_bin_psm4 = pytesseract.image_to_string(img_binarizada, lang="por", config="--oem 3 --psm 4")
            dados_bin_psm4 = extrair_dados_financeiros(texto_bin_psm4)
            if dados_bin_psm4.get("valor") is not None:
                texto_bin = texto_bin_psm4
                logger.info("[VISION] Sucesso com imagem binarizada (PSM 4).")

        if save_debug:
            with open(os.path.join(DEBUG_DIR, "05_ocr_result.txt"), "w", encoding="utf-8") as f:
                f.write(texto_bin)
                
        return texto_bin
    except Exception as e:
        logger.error(f"[VISION] Erro no pipeline de Visão/OCR: {e}")
        return ""

def extrair_dados_financeiros(texto: str) -> dict:
    """
    Varre o texto extraído buscando o Valor Total, a Descrição/Loja e a Categoria.
    Retorna um dicionário estruturado.
    """
    dados = {
        "valor": None,
        "descricao": "Gasto por Imagem",
        "categoria": "Geral"
    }

    if not texto:
        return dados

    linhas = [l.strip() for l in texto.split("\n") if l.strip()]

    # --- 1. Extração da Descrição (Normalmente o nome da loja/empresa no topo) ---
    # Pegamos o primeiro texto relevante que não pareça um cabeçalho técnico de nota fiscal
    cabecalhos_comuns = ["cnpj", "cupom", "fiscal", "nfc-e", "danfe", "extrato", "via", "cliente", "operador"]
    for linha in linhas[:4]:  # Verifica as primeiras 4 linhas
        if not any(palavra in linha.lower() for palavra in cabecalhos_comuns) and len(linha) > 3:
            # Limpa caracteres especiais comuns de erros de OCR no nome
            nome_limpo = re.sub(r"[^\w\s\-\.\,\&]", "", linha).strip()
            if nome_limpo:
                dados["descricao"] = nome_limpo
                break


    # --- 2. Extração do Valor Total ---
    # Padrões comuns para achar valor (ex: "TOTAL R$ 45,90", "VALOR A PAGAR: 15.00", "PAGO R$12.50")
    # Captura R$ 123,45 ou 123,45 ou 123.45.
    # O (?!\d) assegura que o número não continue (evitando pegar parte de CPFs ou valores maiores)
    padroes_valor = [
        r"(?:total|pagar|pago|valor|subtotal|soma|dinheiro|pix|debito|credito|card)[\s\.:\$-]*(?:r\$)?[\s\.:]*([\d\s]+[\.,]\d{2})(?!\d)",
        r"(?:r\$)\s*([\d\s]+[\.,]\d{2})(?!\d)",
        r"([\d\s]+[\.,]\d{2})(?!\d)"
    ]

    valores_candidatos = []
    ignorar_palavras = ["cpf", "cnpj", "chpj", "tel", "telefone", "fone", "ie:", "im:", "inscricao"]
    
    # Busca por linhas contendo palavras-chave e números monetários
    for linha in linhas:
        linha_lf = linha.lower()
        # Se a linha contiver algum identificador como CNPJ ou Telefone, ignora inteira para evitar falsos positivos
        if any(kw in linha_lf for kw in ignorar_palavras):
            continue

        for padrao in padroes_valor:
            matches = re.findall(padrao, linha_lf)
            if matches:
                for val_str in matches:
                    # Remove espaços em branco que o OCR às vezes coloca entre os números
                    val_clean = val_str.replace(" ", "").replace(",", ".")
                    try:
                        val_float = float(val_clean)
                        # Ignora valores zerados
                        if val_float > 0:
                            # Se for uma linha com palavra total/pago, dá prioridade alta
                            prioridade = 2 if any(kw in linha_lf for kw in ["total", "pagar", "pago", "soma"]) else 1
                            valores_candidatos.append((val_float, prioridade))
                    except ValueError:
                        continue

    if valores_candidatos:
        # Ordena candidatos: prioridade 2 primeiro, depois maior valor
        valores_candidatos.sort(key=lambda x: (x[1], x[0]), reverse=True)
        dados["valor"] = valores_candidatos[0][0]
    else:
        # Fallback de último recurso: varre todo o texto por qualquer número que pareça dinheiro
        todos_valores = re.findall(r"\b\d+[\.,]\d{2}\b", texto)
        valores_finais = []
        for v in todos_valores:
            try:
                valores_finais.append(float(v.replace(",", ".")))
            except ValueError:
                continue
        if valores_finais:
            # Pega o maior valor (geralmente o total do cupom)
            dados["valor"] = max(valores_finais)

    # --- 3. Inferência de Categoria com base em palavras-chave ---
    keywords_categorias = {
        "Alimentação": ["mercado", "supermercado", "restaurante", "padaria", "ifood", "comida", "lanche", "café", "pão", "pizza", "churrasco", "bebida"],
        "Transporte": ["uber", "99taxi", "posto", "combustível", "gasolina", "etanol", "diesel", "metrô", "ônibus", "passagem", "pedágio"],
        "Lazer": ["cinema", "netflix", "spotify", "shopping", "show", "teatro", "jogos", "bar", "cerveja", "pub"],
        "Moradia": ["aluguel", "condomínio", "luz", "água", "energia", "gás", "internet", "iptu", "móveis"],
        "Saúde": ["farmácia", "drogaria", "médico", "consulta", "hospital", "remédio", "dentista"],
        "Educação": ["escola", "faculdade", "curso", "livro", "mensalidade"],
    }

    texto_lower = texto.lower()
    for cat, kws in keywords_categorias.items():
        if any(kw in texto_lower for kw in kws):
            dados["categoria"] = cat
            break

    return dados
