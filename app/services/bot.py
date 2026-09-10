"""
bot.py — Serviço do agente WhatsApp para o Projeto Trill.

Responsabilidades:
  1. parse_intencao()   — identifica o que o usuário quer (por palavras-chave)
  2. parse_gasto()      — extrai valor e descrição de mensagens como "gastei 50 no ifood"
  3. processar_mensagem() — orquestra: usuário → ação → resposta
  4. responder()        — envia mensagem de volta via Evolution API HTTP
  5. formatar_*()       — formata dados do finance.py em texto legível para WhatsApp
"""

import os
import re
import json
import logging
import httpx
from sqlalchemy.orm import Session

from app.models import models
from app.models.schemas.schemas import GastoCreate
from app.services import finance

logger = logging.getLogger(__name__)

# ── Configurações do Gemini ──────────────────────────────────────────────────
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")

SYSTEM_INSTRUCTION = """
Você é o Trill, um assistente virtual de controle financeiro pessoal pelo WhatsApp.
Sua tarefa é analisar a mensagem enviada pelo usuário e identificar a intenção dele, além de extrair dados se for um lançamento de gasto/receita, mudança de meta, alteração de categoria ou exclusão de transação.

Intenções possíveis:
- 'registrar_gasto': quando o usuário informa uma despesa/gasto (ex: "gastei 50", "pagou 30 uber", "10 reais coxinha").
- 'registrar_receita': quando o usuário informa um ganho/receita (ex: "salario caiu 3000", "recebi 500 freelance", "ganhei 150 pix").
- 'alterar_meta': quando o usuário quer mudar, definir ou atualizar sua meta de gastos mensal (ex: "mudar minha meta para 2000 reais", "alterar meta para 1500").
- 'alterar_categoria': quando o usuário quer mudar ou atualizar a categoria de uma despesa recente (ex: "mudar categoria do ifood para Lazer", "mudar mercado para Alimentação", "mudar a categoria do último gasto para Transporte").
- 'deletar_transacao': quando o usuário deseja apagar, excluir ou deletar um gasto ou transação (ex: "deletar último gasto", "apagar gasto de 50 reais", "excluir receita de ontem").
- 'resumo_semanal': quando o usuário quer ver o resumo da semana (ex: "quanto gastei essa semana").
- 'resumo_mensal': quando o usuário quer ver o resumo do mês (ex: "resumo do mes", "quanto gastei esse mes").
- 'por_categoria': quando o usuário quer ver gastos por categoria (ex: "gastos por categoria").
- 'ultimos_gastos': quando o usuário quer ver as últimas transações (ex: "ultimos gastos").
- 'status_meta': quando o usuário quer ver a meta mensal (ex: "status da meta", "quanto falta para a meta").
- 'resumo_completo': quando o usuário quer um relatório completo de tudo (ex: "relatório completo").
- 'ajuda': quando o usuário pede ajuda ou envia saudação inicial (ex: "ajuda", "oi", "menu", "o que você faz").
- 'conversar': quando o usuário envia qualquer outra mensagem, dúvida de finanças, cálculos matemáticos ou conversa informal (ex: "quanto é 5 + 5", "como economizar dinheiro?", "boa noite", "o que é selic?").

Regras para extração de transações (se intent for registrar_gasto ou registrar_receita):
- valor: Extraia o valor numérico exato da transação (ex: 50.0).
- descricao: Extraia uma descrição simples da transação (ex: "Uber", "Ifood", "Salário"). Se não informada, use a categoria ou uma descrição genérica.
- categoria: Infira uma categoria adequada. 
  - Para despesas (registrar_gasto): "Alimentação", "Transporte", "Moradia", "Lazer", "Saúde", "Educação", ou "Geral".
  - Para receitas (registrar_receita): "Salário", "Investimentos", "Freelance", ou "Outros".

Regras para alteração de meta (se intent for alterar_meta):
- valor: Extraia o valor numérico da nova meta mensal desejada (ex: 1500.0).

Regras para alterar categoria (se intent for alterar_categoria):
- valor: Extraia o valor do gasto que se deseja alterar, caso o usuário tenha informado (ex: 50.0).
- descricao: Extraia a descrição da transação de busca que se deseja alterar, caso informado (ex: "ifood").
- categoria: Extraia a nova categoria desejada (ex: "Lazer", "Transporte", "Alimentação", etc.).

Regras para deletar transação (se intent for deletar_transacao):
- valor: Extraia o valor da transação a ser excluída, caso o usuário tenha informado (ex: 50.0).
- descricao: Extraia a descrição da transação a ser excluída, caso informado (ex: "ifood").

IMPORTANTE: Não confunda cálculos matemáticos (ex: "quanto é 5 + 5"), dúvidas genéricas que contêm números ou conversas casuais com registros de gastos ou receitas. Lançamentos financeiros devem indicar claramente que ocorreu um gasto ou ganho real. Se for apenas um cálculo matemático, dúvida ou conversa casual, classifique a intenção como 'conversar' e forneça a resposta ou o resultado do cálculo no campo 'resposta_conversa'.

Regras para resposta_conversa (se intent for conversar ou ajuda):
- Crie uma resposta curta, objetiva, amigável e prestativa em português do Brasil. Como é no WhatsApp, use emojis com moderação e formatação em negrito do WhatsApp (*texto*).
"""

def analisar_com_gemini(texto: str) -> dict:
    """
    Chama a API do Gemini com JSON Schema estruturado
    para analisar a intenção e os dados da mensagem do usuário.
    """
    if not GEMINI_KEY:
        logger.warning("[GEMINI] Chave de API não configurada.")
        return {"intent": "desconhecido"}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
    headers = {"Content-Type": "application/json"}
    
    prompt = f"{SYSTEM_INSTRUCTION}\nMensagem do usuário: {texto}"
    
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "object",
                "properties": {
                    "intent": {
                        "type": "string",
                        "enum": [
                            "registrar_gasto",
                            "registrar_receita",
                            "alterar_meta",
                            "alterar_categoria",
                            "deletar_transacao",
                            "resumo_semanal",
                            "resumo_mensal",
                            "por_categoria",
                            "ultimos_gastos",
                            "status_meta",
                            "resumo_completo",
                            "ajuda",
                            "conversar"
                        ]
                    },
                    "valor": {
                        "type": "number",
                        "description": "O valor da transação caso a intenção seja registrar_gasto/registrar_receita, o valor da nova meta se for alterar_meta, ou o valor do gasto de busca para alterar_categoria/deletar_transacao."
                    },
                    "descricao": {
                        "type": "string",
                        "description": "A descrição da transação se for registrar_gasto/registrar_receita, ou o termo de busca para alterar_categoria/deletar_transacao."
                    },
                    "categoria": {
                        "type": "string",
                        "description": "A categoria da transação (para criação se for registrar_gasto/registrar_receita, ou a nova categoria a ser aplicada se for alterar_categoria)."
                    },
                    "resposta_conversa": {
                        "type": "string",
                        "description": "Uma resposta curta, amigável e prestativa simulando um consultor financeiro (ou o resultado/resposta para contas ou dúvidas), caso a intenção seja 'conversar' ou 'ajuda'."
                    }
                },
                "required": ["intent"]
            }
        }
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            res_json = response.json()
            
            candidates = res_json.get("candidates", [])
            if candidates:
                text_response = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                if text_response:
                    return json.loads(text_response.strip())
            
            logger.error(f"[GEMINI] Resposta do Gemini vazia ou inválida: {res_json}")
    except Exception as e:
        logger.error(f"[GEMINI] Erro ao chamar a API do Gemini: {e}")
        
    return {"intent": "desconhecido"}

# ── Configurações da Evolution API ───────────────────────────────────────────
EVOLUTION_URL      = os.getenv("EVOLUTION_API_URL", "http://evolution_api:8080")
EVOLUTION_KEY      = os.getenv("EVOLUTION_API_KEY", "")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "trill-bot")

# ── Mapa de palavras-chave por categoria ─────────────────────────────────────
CATEGORIA_KEYWORDS = {
    "Alimentação": ["ifood", "uber eats", "rappi", "mercado", "supermercado",
                    "restaurante", "lanche", "pizza", "açaí", "padaria",
                    "café", "almoço", "jantar", "comida", "feira"],
    "Transporte":  ["uber", "99", "onibus", "ônibus", "metrô", "metro",
                    "gasolina", "combustível", "táxi", "taxi", "passagem"],
    "Moradia":     ["aluguel", "condomínio", "condominio", "luz", "água", "agua",
                    "internet", "gás", "gas", "energia", "iptu"],
    "Lazer":       ["netflix", "spotify", "cinema", "show", "teatro", "jogo",
                    "bar", "balada", "viagem", "hotel", "festa"],
    "Saúde":       ["farmácia", "farmacia", "remédio", "remedio", "médico",
                    "medico", "dentista", "academia", "plano de saúde"],
    "Educação":    ["curso", "faculdade", "escola", "livro", "udemy",
                    "alura", "mensalidade"],
}

MENU_AJUDA = """🤖 *Trill Bot — Comandos disponíveis*

💸 *Registrar transações:*
  "gastei 50 no ifood"
  "recebi 3000 de salário"

🎯 *Metas:*
  "alterar minha meta para 1500"
  "status da meta"

📊 *Consultas & Relatórios:*
  "resumo" ou "relatório"
  "quanto gastei essa semana"
  "gastos por categoria"
  "últimos gastos"

ℹ️ *Outros:*
  "ajuda" — exibe este menu"""


# ═══════════════════════════════════════════════════════════════════════════════
#  1. PARSER DE INTENÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

def parse_intencao(texto: str) -> str:
    """
    Identifica a intenção do usuário por palavras-chave.
    Retorna uma string representando a intenção detectada.
    """
    t = texto.lower().strip()

    if any(p in t for p in ["ajuda", "help", "menu", "comandos", "oi", "olá", "ola"]):
        return "ajuda"

    # Checa alteração de categoria e exclusão antes de checar por_categoria
    if any(p in t for p in ["mudar categoria", "alterar categoria", "mudar a categoria", "alterar a categoria", "atualizar categoria", "mudar de categoria", "alterar de categoria"]):
        return "alterar_categoria"

    if any(p in t for p in ["deletar", "excluir", "apagar", "remover"]):
        return "deletar_transacao"

    if any(p in t for p in ["semana", "semanal"]):
        return "resumo_semanal"

    if any(p in t for p in ["mês", "mes", "mensal", "esse mês", "este mês"]):
        return "resumo_mensal"

    if any(p in t for p in ["categoria", "categorias", "por categoria"]):
        return "por_categoria"

    if any(p in t for p in ["último", "ultimo", "últimos", "ultimos", "histórico", "historico", "recente"]):
        return "ultimos_gastos"

    # Detecta alteração de meta antes de checar consulta de status_meta
    if any(p in t for p in ["mudar meta", "alterar meta", "nova meta", "definir meta", "atualizar meta", "ajustar meta", "meta nova", "mudar o limite", "alterar o limite", "novo limite", "definir limite", "limite novo"]):
        if _tem_valor_monetario(t):
            return "alterar_meta"

    if any(p in t for p in ["meta", "objetivo", "limite"]):
        return "status_meta"

    if any(p in t for p in ["resumo", "relatório", "relatorio", "completo", "tudo"]):
        return "resumo_completo"

    # Detecta intenção de registrar receita (número + contexto de ganho)
    if _tem_valor_monetario(t) and any(p in t for p in ["recebi", "ganhei", "receita", "salario", "salário", "freelance", "ganho", "pix"]):
        return "registrar_receita"

    # Detecta intenção de registrar gasto (número + contexto financeiro)
    if _tem_valor_monetario(t) and _tem_contexto_financeiro_despesa(t):
        return "registrar_gasto"

    return "desconhecido"


def _tem_valor_monetario(texto: str) -> bool:
    """Verifica se a mensagem contém um valor numérico."""
    padrao = r'\b\d+([.,]\d{1,2})?\b'
    return bool(re.search(padrao, texto))


def _tem_contexto_financeiro_despesa(texto: str) -> bool:
    """Verifica se há indicação de que o número na mensagem representa um gasto/despesa real."""
    # Evita falsos positivos com contas de matemática/operações no fallback
    if any(op in texto for op in ["+", "-", "*", "/", "=", "soma", "vezes", "dividido", "menos", "mais"]):
        return False

    palavras_acao = ["gastei", "gasto", "despesa", "paguei", "pago", "comprei", "compra", "fatura", "pagou", "comprou", "custou", "saída", "saida", "débito", "debito"]
    if any(p in texto for p in palavras_acao):
        return True

    indicadores_moeda = ["reais", "r$", "conto", "cruzeiros", "dólares", "dolares", "eur", "euros"]
    if any(m in texto for m in indicadores_moeda):
        return True

    # Se contém qualquer uma das palavras-chave das categorias de despesas
    for keywords in CATEGORIA_KEYWORDS.values():
        if any(kw in texto for kw in keywords):
            return True

    return False


# ═══════════════════════════════════════════════════════════════════════════════
#  2. PARSER DE GASTO
# ═══════════════════════════════════════════════════════════════════════════════

def parse_gasto(texto: str) -> dict | None:
    """
    Extrai valor, descrição e categoria de mensagens como:
    - "gastei 50 no ifood"
    - "50 reais mercado"
    - "120,50 almoço restaurante"

    Retorna dict com {valor, descricao, categoria} ou None se não conseguir.
    """
    t = texto.lower().strip()

    # Remove palavras de ação comuns
    t_limpo = re.sub(r'\b(gastei|gasto|paguei|pago|comprei|compra|reais?|r\$)\b', '', t).strip()

    # Extrai o primeiro número encontrado como valor
    match = re.search(r'\b(\d+([.,]\d{1,2})?)\b', t_limpo)
    if not match:
        return None

    valor_str = match.group(1).replace(',', '.')
    try:
        valor = float(valor_str)
    except ValueError:
        return None

    if valor <= 0:
        return None

    # Descrição = tudo que não é o número, limpo
    descricao_raw = re.sub(r'\b\d+([.,]\d{1,2})?\b', '', t_limpo).strip()
    descricao_raw = re.sub(r'\s+', ' ', descricao_raw).strip(" -–")

    # Remove preposições soltas no início
    descricao_raw = re.sub(r'^(no|na|em|de|do|da|com|para)\b', '', descricao_raw).strip()

    descricao = descricao_raw.title() if descricao_raw else "Gasto via WhatsApp"

    # Infere categoria
    categoria = _inferir_categoria(texto.lower())

    return {
        "valor": valor,
        "descricao": descricao,
        "categoria": categoria,
    }


def _inferir_categoria(texto: str) -> str:
    """Tenta inferir a categoria com base em palavras-chave no texto."""
    for categoria, keywords in CATEGORIA_KEYWORDS.items():
        if any(kw in texto for kw in keywords):
            return categoria
    return "Geral"


# ═══════════════════════════════════════════════════════════════════════════════
#  3. FORMATADORES DE RESPOSTA
# ═══════════════════════════════════════════════════════════════════════════════

def formatar_resumo_mensal(dados: dict) -> str:
    linhas = [
        f"📅 *Resumo de {dados['mes_nome']}/{dados['ano']}*\n",
        f"💰 Total gasto: *R$ {dados['total_gasto']:.2f}*",
        f"📈 Total recebido: *R$ {dados.get('total_receita', 0.0):.2f}*",
        f"⚖️ Saldo líquido: *R$ {dados.get('saldo_liquido', 0.0):.2f}*",
        f"🧾 Transações de gastos: *{dados['quantidade_transacoes']}*",
    ]
    if dados.get("meta_mensal"):
        linhas.append(f"🎯 Meta de gastos: R$ {dados['meta_mensal']:.2f}")
        linhas.append(f"📊 Meta utilizada: *{dados['percentual_meta']}%*")
        saldo = dados.get("saldo_restante", 0)
        emoji = "✅" if saldo >= 0 else "❌"
        linhas.append(f"{emoji} Limite restante: *R$ {saldo:.2f}*")
    return "\n".join(linhas)


def formatar_resumo_semanal(dados: dict) -> str:
    return (
        f"📅 *Resumo Semanal*\n"
        f"🗓️ Período: {dados['periodo']}\n\n"
        f"💰 Total: *R$ {dados['total_gasto']:.2f}*\n"
        f"🧾 Transações: *{dados['quantidade_transacoes']}*\n"
        f"📊 Média/dia: *R$ {dados['media_diaria']:.2f}*\n"
        f"📈 Projeção da semana: *R$ {dados['projecao_semana']:.2f}*"
    )


def formatar_por_categoria(dados: list) -> str:
    if not dados:
        return "📂 Nenhum gasto registrado neste mês ainda."
    linhas = ["📂 *Gastos por Categoria — este mês:*\n"]
    for i, cat in enumerate(dados, 1):
        linhas.append(
            f"{i}. *{cat['categoria']}*: R$ {cat['total']:.2f} "
            f"({cat['percentual']}%) — {cat['quantidade']} transação(ões)"
        )
    return "\n".join(linhas)


def formatar_ultimos_gastos(dados: list) -> str:
    if not dados:
        return "📋 Nenhum gasto registrado ainda."
    linhas = ["📋 *Últimos gastos:*\n"]
    for g in dados:
        linhas.append(f"• {g['data']} — *{g['descricao']}*: R$ {g['valor']:.2f} [{g['categoria']}]")
    return "\n".join(linhas)


def formatar_status_meta(dados: dict) -> str:
    if not dados.get("tem_meta"):
        return (
            "🎯 *Meta mensal não definida.*\n"
            "Acesse o painel em http://localhost:5173 para configurar sua meta."
        )
    return f"🎯 *Status da Meta*\n\n{dados['mensagem']}"


def formatar_confirmacao_gasto(gasto: dict) -> str:
    return (
        f"✅ *Gasto registrado!*\n\n"
        f"💸 Valor: *R$ {gasto['valor']:.2f}*\n"
        f"📝 Descrição: *{gasto['descricao']}*\n"
        f"📂 Categoria: *{gasto['categoria']}*"
    )


def formatar_confirmacao_receita(receita: dict) -> str:
    return (
        f"✅ *Receita registrada!*\n\n"
        f"📈 Valor: *R$ {receita['valor']:.2f}*\n"
        f"📝 Descrição: *{receita['descricao']}*\n"
        f"📂 Categoria: *{receita['categoria']}*"
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  4. ENVIO VIA EVOLUTION API
# ═══════════════════════════════════════════════════════════════════════════════

def responder(numero: str, mensagem: str) -> bool:
    """
    Envia uma mensagem de texto para o número via Evolution API.
    Retorna True se enviou com sucesso.
    """
    url = f"{EVOLUTION_URL}/message/sendText/{EVOLUTION_INSTANCE}"
    headers = {"apikey": EVOLUTION_KEY, "Content-Type": "application/json"}
    payload = {
        "number": numero,
        "text": mensagem,
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return True
    except httpx.HTTPStatusError as e:
        logger.error(f"Erro HTTP ao enviar mensagem: {e.response.status_code} — {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"Erro de conexão com Evolution API: {e}")
    return False


# ═══════════════════════════════════════════════════════════════════════════════
#  5. ORQUESTRADOR PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def processar_mensagem(db: Session, numero: str, texto: str) -> None:
    """
    Ponto de entrada principal do bot.
    Recebe o número do remetente e o texto da mensagem,
    processa e envia a resposta pelo WhatsApp.
    """
    logger.info(f"[BOT] Mensagem de {numero}: {texto!r}")

    # Normaliza o número (remove "@s.whatsapp.net" se vier do webhook)
    numero_limpo = numero.split("@")[0]

    # Busca o usuário pelo telefone cadastrado
    usuario = _buscar_usuario_por_telefone(db, numero_limpo)

    if not usuario:
        # Ignora silenciosamente para não responder a contatos pessoais não cadastrados
        return

    # Se a chave do Gemini estiver ativa, faz a análise com a LLM
    gemini_analise = None
    intencao = "desconhecido"
    if GEMINI_KEY:
        gemini_analise = analisar_com_gemini(texto)
        intencao = gemini_analise.get("intent", "desconhecido")
        logger.info(f"[BOT] Intenção detectada pelo Gemini: {intencao}")

    # Fallback para Regex se a intenção for desconhecida ou a API falhar
    if intencao == "desconhecido":
        intencao = parse_intencao(texto)
        logger.info(f"[BOT] Intenção detectada por Regex (fallback): {intencao}")

    # Executa a ação correspondente
    try:
        resposta = _executar_intencao(db, usuario, intencao, texto, gemini_analise)
    except Exception as e:
        logger.error(f"[BOT] Erro ao processar intenção '{intencao}': {e}")
        resposta = "⚠️ Ocorreu um erro ao processar sua solicitação. Tente novamente."

    responder(numero_limpo, resposta)


def _buscar_usuario_por_telefone(db: Session, numero: str) -> models.User | None:
    """Busca o usuário pelo campo telefone, normalizando formatos."""
    # Tenta encontrar com e sem código de país
    tentativas = [numero, numero.lstrip("55"), "55" + numero]
    for tel in tentativas:
        user = db.query(models.User).filter(
            models.User.telefone.contains(tel[-8:])  # busca pelos 8 últimos dígitos
        ).first()
        if user:
            return user
    return None


def _executar_intencao(db: Session, usuario: models.User, intencao: str, texto: str, gemini_analise: dict = None) -> str:
    """Executa a ação correspondente à intenção e retorna a resposta formatada."""

    if intencao == "ajuda":
        if gemini_analise and gemini_analise.get("resposta_conversa"):
            return gemini_analise["resposta_conversa"]
        return MENU_AJUDA

    if intencao == "conversar":
        if gemini_analise and gemini_analise.get("resposta_conversa"):
            return gemini_analise["resposta_conversa"]
        return "Olá! Sou o Trill, seu assistente de controle financeiro. Como posso ajudar você hoje?"

    if intencao == "resumo_semanal":
        dados = finance.get_resumo_semanal(db, usuario.id)
        return formatar_resumo_semanal(dados)

    if intencao == "resumo_mensal":
        dados = finance.get_resumo_mensal(db, usuario.id)
        return formatar_resumo_mensal(dados)

    if intencao == "por_categoria":
        dados = finance.get_gastos_por_categoria(db, usuario.id)
        return formatar_por_categoria(dados)

    if intencao == "ultimos_gastos":
        dados_gastos = finance.get_ultimos_gastos(db, usuario.id, limit=5)
        return formatar_ultimos_gastos(dados_gastos)

    if intencao == "status_meta":
        dados = finance.get_status_meta(db, usuario.id)
        return formatar_status_meta(dados)

    if intencao == "resumo_completo":
        mensal = finance.get_resumo_mensal(db, usuario.id)
        semanal = finance.get_resumo_semanal(db, usuario.id)
        meta = finance.get_status_meta(db, usuario.id)
        return (
            formatar_resumo_mensal(mensal) + "\n\n" +
            formatar_resumo_semanal(semanal) + "\n\n" +
            formatar_status_meta(meta)
        )

    if intencao == "registrar_gasto":
        if gemini_analise and gemini_analise.get("valor") is not None:
            gasto_parsed = {
                "valor": float(gemini_analise["valor"]),
                "descricao": gemini_analise.get("descricao") or "Gasto",
                "categoria": gemini_analise.get("categoria") or "Geral"
            }
        else:
            gasto_parsed = parse_gasto(texto)
            # Se falhar pelo parser de regex simples, mas for texto multilinha de OCR, tenta o parser de visão
            if (not gasto_parsed or not gasto_parsed.get("valor")) and ("\n" in texto or "comprovante" in texto.lower() or "total" in texto.lower()):
                from app.services import vision
                vision_parsed = vision.extrair_dados_financeiros(texto)
                if vision_parsed and vision_parsed.get("valor") is not None:
                    gasto_parsed = vision_parsed
            
        if not gasto_parsed or not gasto_parsed.get("valor"):
            return (
                "🤔 Não consegui identificar o valor do gasto.\n\n"
                "Tente: *'gastei 50 no ifood'* ou *'120 mercado'*"
            )

        novo_gasto = models.Gasto(
            valor=gasto_parsed["valor"],
            descricao=gasto_parsed["descricao"],
            categoria=gasto_parsed["categoria"],
            user_id=usuario.id,
        )
        db.add(novo_gasto)
        db.commit()
        db.refresh(novo_gasto)

        return formatar_confirmacao_gasto(gasto_parsed)

    if intencao == "registrar_receita":
        if gemini_analise and gemini_analise.get("valor") is not None:
            receita_parsed = {
                "valor": float(gemini_analise["valor"]),
                "descricao": gemini_analise.get("descricao") or "Receita",
                "categoria": gemini_analise.get("categoria") or "Outros"
            }
        else:
            receita_parsed = parse_gasto(texto)
            if receita_parsed and receita_parsed["categoria"] == "Geral":
                t = texto.lower()
                if "salario" in t or "salário" in t:
                    receita_parsed["categoria"] = "Salário"
                elif "invest" in t:
                    receita_parsed["categoria"] = "Investimentos"
                elif "free" in t:
                    receita_parsed["categoria"] = "Freelance"

        if not receita_parsed or not receita_parsed.get("valor"):
            return (
                "🤔 Não consegui identificar o valor da receita.\n\n"
                "Tente: *'recebi 3000 do salario'* ou *'receita 500 freelance'*"
            )

        nova_receita = models.Receita(
            valor=receita_parsed["valor"],
            descricao=receita_parsed["descricao"],
            categoria=receita_parsed["categoria"],
            user_id=usuario.id,
        )
        db.add(nova_receita)
        db.commit()
        db.refresh(nova_receita)

        return formatar_confirmacao_receita(receita_parsed)

    if intencao == "alterar_meta":
        if gemini_analise and gemini_analise.get("valor") is not None:
            nova_meta = float(gemini_analise["valor"])
        else:
            gasto_parsed = parse_gasto(texto)
            nova_meta = gasto_parsed["valor"] if gasto_parsed else None

        if not nova_meta or nova_meta <= 0:
            return (
                "🤔 Não consegui identificar o valor para a nova meta.\n\n"
                "Tente algo como: *'alterar minha meta para 1500'* ou *'mudar meta para 2000'*."
            )

        usuario.meta_mensal = nova_meta
        db.commit()
        db.refresh(usuario)

        return (
            f"🎯 *Meta mensal atualizada com sucesso!*\n\n"
            f"Seu novo limite de gastos mensal é: *R$ {nova_meta:.2f}*."
        )

    if intencao == "alterar_categoria":
        # Extrai a nova categoria
        nova_categoria = None
        if gemini_analise and gemini_analise.get("categoria"):
            nova_categoria = gemini_analise["categoria"].title()
        else:
            nova_categoria = _inferir_categoria(texto.lower())

        if not nova_categoria or nova_categoria == "Geral":
            for cat in CATEGORIA_KEYWORDS.keys():
                if cat.lower() in texto.lower():
                    nova_categoria = cat
                    break

        if not nova_categoria or nova_categoria == "Geral":
            return (
                "🤔 Não consegui identificar a nova categoria que você deseja aplicar.\n\n"
                "Tente algo como: *'mudar a categoria de mercado para Lazer'*."
            )

        # Extrai critérios de busca
        busca_desc = None
        busca_val = None
        if gemini_analise:
            busca_desc = gemini_analise.get("descricao")
            busca_val = gemini_analise.get("valor")

        if not busca_val:
            gasto_parsed = parse_gasto(texto)
            if gasto_parsed:
                busca_val = gasto_parsed["valor"]

        # Busca nos lançamentos recentes do usuário (últimos 10 gastos)
        gastos_recentes = db.query(models.Gasto).filter(
            models.Gasto.user_id == usuario.id
        ).order_by(models.Gasto.data_registro.desc()).limit(10).all()

        transacao_encontrada = None

        # 1. Tenta achar um match exato por descrição e/ou valor
        if busca_desc or busca_val:
            for g in gastos_recentes:
                match_desc = busca_desc and busca_desc.lower() in g.descricao.lower()
                match_val = busca_val and abs(g.valor - float(busca_val)) < 0.01
                if (busca_desc and busca_val and match_desc and match_val) or \
                   (busca_desc and not busca_val and match_desc) or \
                   (busca_val and not busca_desc and match_val):
                    transacao_encontrada = g
                    break

        # 2. Se não achou, pega o último gasto absoluto
        if not transacao_encontrada and gastos_recentes:
            transacao_encontrada = gastos_recentes[0]

        if not transacao_encontrada:
            return "📂 Não encontrei nenhum gasto recente para alterar a categoria."

        # Efetua a atualização
        categoria_antiga = transacao_encontrada.categoria
        transacao_encontrada.categoria = nova_categoria
        db.commit()
        db.refresh(transacao_encontrada)

        return (
            f"✅ *Categoria atualizada com sucesso!*\n\n"
            f"📝 Transação: *{transacao_encontrada.descricao}*\n"
            f"💸 Valor: *R$ {transacao_encontrada.valor:.2f}*\n"
            f"📂 De: *{categoria_antiga}* ➔ Para: *{nova_categoria}*"
        )

    if intencao == "deletar_transacao":
        # Extrai critérios de busca
        busca_desc = None
        busca_val = None
        if gemini_analise:
            busca_desc = gemini_analise.get("descricao")
            busca_val = gemini_analise.get("valor")

        if not busca_val:
            gasto_parsed = parse_gasto(texto)
            if gasto_parsed:
                busca_val = gasto_parsed["valor"]

        # Busca nos lançamentos recentes do usuário (últimos 10 gastos)
        gastos_recentes = db.query(models.Gasto).filter(
            models.Gasto.user_id == usuario.id
        ).order_by(models.Gasto.data_registro.desc()).limit(10).all()

        transacao_encontrada = None

        # 1. Tenta achar um match exato
        if busca_desc or busca_val:
            for g in gastos_recentes:
                match_desc = busca_desc and busca_desc.lower() in g.descricao.lower()
                match_val = busca_val and abs(g.valor - float(busca_val)) < 0.01
                if (busca_desc and busca_val and match_desc and match_val) or \
                   (busca_desc and not busca_val and match_desc) or \
                   (busca_val and not busca_desc and match_val):
                    transacao_encontrada = g
                    break

        # 2. Se não achou, pega o último gasto absoluto
        if not transacao_encontrada and gastos_recentes:
            transacao_encontrada = gastos_recentes[0]

        # 3. Se ainda não achou, busca nas receitas recentes
        if not transacao_encontrada:
            receitas_recentes = db.query(models.Receita).filter(
                models.Receita.user_id == usuario.id
            ).order_by(models.Receita.data_registro.desc()).limit(10).all()

            if busca_desc or busca_val:
                for r in receitas_recentes:
                    match_desc = busca_desc and busca_desc.lower() in r.descricao.lower()
                    match_val = busca_val and abs(r.valor - float(busca_val)) < 0.01
                    if (busca_desc and busca_val and match_desc and match_val) or \
                       (busca_desc and not busca_val and match_desc) or \
                       (busca_val and not busca_desc and match_val):
                        transacao_encontrada = r
                        break
            if not transacao_encontrada and receitas_recentes and not (busca_desc or busca_val):
                transacao_encontrada = receitas_recentes[0]

        if not transacao_encontrada:
            return "📋 Não encontrei nenhuma transação recente para deletar."

        # Guarda dados para a mensagem de confirmação
        desc = transacao_encontrada.descricao
        val = transacao_encontrada.valor
        tipo = "Despesa" if isinstance(transacao_encontrada, models.Gasto) else "Receita"

        # Efetua exclusão
        db.delete(transacao_encontrada)
        db.commit()

        return (
            f"🗑️ *Transação excluída com sucesso!*\n\n"
            f"Tipo: *{tipo}*\n"
            f"📝 Descrição: *{desc}*\n"
            f"💸 Valor: *R$ {val:.2f}*\n"
            f"O lançamento foi removido do seu histórico."
        )

    # Intenção desconhecida
    return (
        "🤔 Não entendi sua mensagem.\n\n"
        "Digite *'ajuda'* para ver os comandos disponíveis."
    )
