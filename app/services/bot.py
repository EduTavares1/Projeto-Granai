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
import logging
import httpx
from sqlalchemy.orm import Session

from app.models import models
from app.models.schemas.schemas import GastoCreate
from app.services import finance

logger = logging.getLogger(__name__)

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

💸 *Registrar gasto:*
  "gastei 50 no ifood"
  "50 reais mercado"

📊 *Consultas:*
  "resumo" ou "relatório"
  "quanto gastei essa semana"
  "quanto gastei esse mês"
  "gastos por categoria"
  "últimos gastos"
  "status da meta"

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

    if any(p in t for p in ["semana", "semanal"]):
        return "resumo_semanal"

    if any(p in t for p in ["mês", "mes", "mensal", "esse mês", "este mês"]):
        return "resumo_mensal"

    if any(p in t for p in ["categoria", "categorias", "por categoria"]):
        return "por_categoria"

    if any(p in t for p in ["último", "ultimo", "últimos", "ultimos", "histórico", "historico", "recente"]):
        return "ultimos_gastos"

    if any(p in t for p in ["meta", "objetivo", "limite"]):
        return "status_meta"

    if any(p in t for p in ["resumo", "relatório", "relatorio", "completo", "tudo"]):
        return "resumo_completo"

    # Detecta intenção de registrar gasto (número + contexto)
    if _tem_valor_monetario(t):
        return "registrar_gasto"

    return "desconhecido"


def _tem_valor_monetario(texto: str) -> bool:
    """Verifica se a mensagem contém um valor numérico que parece ser um gasto."""
    padrao = r'\b\d+([.,]\d{1,2})?\b'
    return bool(re.search(padrao, texto))


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
        f"🧾 Transações: *{dados['quantidade_transacoes']}*",
    ]
    if dados.get("meta_mensal"):
        linhas.append(f"🎯 Meta: R$ {dados['meta_mensal']:.2f}")
        linhas.append(f"📊 Utilizado: *{dados['percentual_meta']}%*")
        saldo = dados.get("saldo_restante", 0)
        emoji = "✅" if saldo >= 0 else "❌"
        linhas.append(f"{emoji} Saldo restante: *R$ {saldo:.2f}*")
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

    # Identifica a intenção
    intencao = parse_intencao(texto)
    logger.info(f"[BOT] Intenção detectada: {intencao}")

    # Executa a ação correspondente
    try:
        resposta = _executar_intencao(db, usuario, intencao, texto)
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


def _executar_intencao(db: Session, usuario: models.User, intencao: str, texto: str) -> str:
    """Executa a ação correspondente à intenção e retorna a resposta formatada."""

    if intencao == "ajuda":
        return MENU_AJUDA

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
        dados = finance.get_ultimos_gastos(db, usuario.id, limit=5)
        return formatar_ultimos_gastos(dados)

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
        gasto_parsed = parse_gasto(texto)
        if not gasto_parsed:
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

    # Intenção desconhecida
    return (
        "🤔 Não entendi sua mensagem.\n\n"
        "Digite *'ajuda'* para ver os comandos disponíveis."
    )
