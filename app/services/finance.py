from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from typing import Optional

from app.models import models
from app.models.schemas import schemas


# ──────────────────────────────────────────────
#  Helpers internos
# ──────────────────────────────────────────────

def _calcular_status_meta(total: float, meta: float) -> str:
    """Classifica o status de consumo da meta em 4 níveis."""
    percentual = (total / meta) * 100
    if percentual >= 100:
        return "estourado"
    elif percentual >= 80:
        return "alerta"
    elif percentual >= 60:
        return "atencao"
    else:
        return "seguro"


def _nome_mes(numero: int) -> str:
    nomes = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
             "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    return nomes[numero - 1]


def _nome_mes_abrev(numero: int) -> str:
    nomes = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
             "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    return nomes[numero - 1]


# ──────────────────────────────────────────────
#  Funções públicas do serviço
# ──────────────────────────────────────────────

def get_resumo_mensal(
    db: Session,
    user_id: int,
    mes: Optional[int] = None,
    ano: Optional[int] = None
) -> dict:
    """
    Retorna um resumo completo dos gastos de um mês específico.
    Se `mes` e `ano` não forem informados, usa o mês corrente.
    """
    now = datetime.utcnow()
    mes = mes or now.month
    ano = ano or now.year

    gastos = db.query(models.Gasto).filter(
        models.Gasto.user_id == user_id,
        extract("month", models.Gasto.data_registro) == mes,
        extract("year", models.Gasto.data_registro) == ano
    ).all()

    total = sum(g.valor for g in gastos)

    # Buscar receitas do mesmo período
    receitas = db.query(models.Receita).filter(
        models.Receita.user_id == user_id,
        extract("month", models.Receita.data_registro) == mes,
        extract("year", models.Receita.data_registro) == ano
    ).all()

    total_receita = sum(r.valor for r in receitas)

    usuario = db.query(models.User).filter(models.User.id == user_id).first()
    meta = usuario.meta_mensal if usuario else None

    return {
        "mes": mes,
        "mes_nome": _nome_mes(mes),
        "ano": ano,
        "total_gasto": round(total, 2),
        "total_receita": round(total_receita, 2),
        "saldo_liquido": round(total_receita - total, 2),
        "quantidade_transacoes": len(gastos),
        "meta_mensal": meta,
        "percentual_meta": round((total / meta) * 100, 1) if meta else None,
        "saldo_restante": round(meta - total, 2) if meta else None,
        "status_meta": _calcular_status_meta(total, meta) if meta else "sem_meta",
    }


def criar_receita(db: Session, receita: schemas.ReceitaCreate, user_id: int) -> models.Receita:
    """Cadastra uma nova receita associada ao usuário."""
    nova_receita = models.Receita(**receita.model_dump(exclude_unset=True), user_id=user_id)
    db.add(nova_receita)
    db.commit()
    db.refresh(nova_receita)
    return nova_receita


def deletar_receita(db: Session, receita_id: int, user_id: int) -> bool:
    """Exclui uma receita pelo ID, se pertencer ao usuário."""
    db_receita = db.query(models.Receita).filter(
        models.Receita.id == receita_id,
        models.Receita.user_id == user_id
    ).first()
    if not db_receita:
        return False
    db.delete(db_receita)
    db.commit()
    return True


def get_receitas(db: Session, user_id: int) -> list[models.Receita]:
    """Retorna todas as receitas cadastradas do usuário."""
    return db.query(models.Receita).filter(models.Receita.user_id == user_id).all()


def atualizar_receita(
    db: Session,
    receita_id: int,
    receita_atualizada: schemas.ReceitaUpdate,
    user_id: int
) -> Optional[models.Receita]:
    """Atualiza uma receita existente."""
    db_receita = db.query(models.Receita).filter(
        models.Receita.id == receita_id,
        models.Receita.user_id == user_id
    ).first()
    if not db_receita:
        return None
    update_data = receita_atualizada.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_receita, key, value)
    db.commit()
    db.refresh(db_receita)
    return db_receita


def get_gastos_por_categoria(
    db: Session,
    user_id: int,
    mes: Optional[int] = None,
    ano: Optional[int] = None
) -> list[dict]:
    """
    Retorna os gastos agrupados por categoria no mês especificado,
    ordenados do maior para o menor valor.
    """
    now = datetime.utcnow()
    mes = mes or now.month
    ano = ano or now.year

    resultado = db.query(
        models.Gasto.categoria,
        func.sum(models.Gasto.valor).label("total"),
        func.count(models.Gasto.id).label("quantidade")
    ).filter(
        models.Gasto.user_id == user_id,
        extract("month", models.Gasto.data_registro) == mes,
        extract("year", models.Gasto.data_registro) == ano
    ).group_by(models.Gasto.categoria).all()

    total_geral = sum(r.total for r in resultado)

    return [
        {
            "categoria": r.categoria,
            "total": round(r.total, 2),
            "quantidade": r.quantidade,
            "percentual": round((r.total / total_geral) * 100, 1) if total_geral > 0 else 0,
        }
        for r in sorted(resultado, key=lambda x: x.total, reverse=True)
    ]


def get_ultimos_gastos(
    db: Session,
    user_id: int,
    limit: int = 5
) -> list[dict]:
    """Retorna os últimos N gastos do usuário, do mais recente ao mais antigo."""
    gastos = db.query(models.Gasto).filter(
        models.Gasto.user_id == user_id
    ).order_by(models.Gasto.data_registro.desc()).limit(limit).all()

    return [
        {
            "id": g.id,
            "descricao": g.descricao,
            "valor": round(g.valor, 2),
            "categoria": g.categoria,
            "data": g.data_registro.strftime("%d/%m/%Y"),
        }
        for g in gastos
    ]


def get_status_meta(db: Session, user_id: int) -> dict:
    """
    Retorna o status detalhado da meta do mês corrente,
    incluindo uma mensagem legível — útil para o agente de IA.
    """
    resumo = get_resumo_mensal(db, user_id)
    meta = resumo.get("meta_mensal")
    total = resumo.get("total_gasto")

    if not meta:
        return {
            "tem_meta": False,
            "mensagem": "Você ainda não definiu uma meta mensal.",
        }

    status = resumo["status_meta"]
    saldo = resumo["saldo_restante"]
    pct = resumo["percentual_meta"]

    mensagens = {
        "seguro": (
            f"✅ Tudo certo! Você gastou R$ {total:.2f} de R$ {meta:.2f} "
            f"({pct}%) em {resumo['mes_nome']}."
        ),
        "atencao": (
            f"⚠️ Atenção! Você já consumiu {pct}% da sua meta em {resumo['mes_nome']}. "
            f"Restam R$ {saldo:.2f}."
        ),
        "alerta": (
            f"🚨 Alerta! Você usou {pct}% da meta. "
            f"Só restam R$ {saldo:.2f} para o resto do mês."
        ),
        "estourado": (
            f"❌ Meta estourada! Você ultrapassou o limite em "
            f"R$ {abs(saldo):.2f} em {resumo['mes_nome']}."
        ),
    }

    return {
        "tem_meta": True,
        "status": status,
        "mes": resumo["mes_nome"],
        "total_gasto": total,
        "meta_mensal": meta,
        "saldo_restante": saldo,
        "percentual_utilizado": pct,
        "mensagem": mensagens.get(status, ""),
    }


def get_resumo_semanal(db: Session, user_id: int) -> dict:
    """
    Retorna o resumo de gastos da semana atual (segunda a domingo).
    """
    hoje = datetime.utcnow().date()
    inicio_semana = hoje - timedelta(days=hoje.weekday())   # segunda-feira
    fim_semana = inicio_semana + timedelta(days=6)           # domingo

    gastos = db.query(models.Gasto).filter(
        models.Gasto.user_id == user_id,
        func.date(models.Gasto.data_registro) >= inicio_semana,
        func.date(models.Gasto.data_registro) <= fim_semana
    ).all()

    total = sum(g.valor for g in gastos)
    dias_passados = hoje.weekday() + 1  # quantos dias da semana já se passaram

    return {
        "periodo": f"{inicio_semana.strftime('%d/%m')} a {fim_semana.strftime('%d/%m/%Y')}",
        "total_gasto": round(total, 2),
        "quantidade_transacoes": len(gastos),
        "media_diaria": round(total / dias_passados, 2) if dias_passados > 0 else 0,
        "projecao_semana": round((total / dias_passados) * 7, 2) if dias_passados > 0 else 0,
    }


def get_comparativo_mensal(
    db: Session,
    user_id: int,
    meses: int = 3
) -> list[dict]:
    """
    Retorna o comparativo de gastos totais dos últimos N meses (padrão: 3).
    Inclui variação percentual em relação ao mês anterior.
    """
    agora = datetime.utcnow()
    resultado = []

    for i in range(meses - 1, -1, -1):
        # Calcula mês e ano retrocedendo corretamente sem underflow
        mes_idx = (agora.month - 1 - i) % 12
        anos_atras = (agora.month - 1 - i) // 12  # negativo quando retroage
        mes_numero = mes_idx + 1
        ano_numero = agora.year + anos_atras

        total = db.query(func.sum(models.Gasto.valor)).filter(
            models.Gasto.user_id == user_id,
            extract("month", models.Gasto.data_registro) == mes_numero,
            extract("year", models.Gasto.data_registro) == ano_numero
        ).scalar() or 0.0

        resultado.append({
            "mes": _nome_mes_abrev(mes_numero),
            "mes_nome": _nome_mes(mes_numero),
            "mes_numero": mes_numero,
            "ano": ano_numero,
            "total": round(total, 2),
        })

    # Adiciona variação percentual mês a mês
    for idx in range(1, len(resultado)):
        anterior = resultado[idx - 1]["total"]
        atual = resultado[idx]["total"]
        if anterior > 0:
            variacao = round(((atual - anterior) / anterior) * 100, 1)
        else:
            variacao = None
        resultado[idx]["variacao_percentual"] = variacao

    resultado[0]["variacao_percentual"] = None  # primeiro mês não tem referência

    return resultado


def get_resumo_completo(db: Session, user_id: int) -> dict:
    """
    Consolida todas as análises em um único payload.
    Ideal para o agente de IA ter contexto completo do usuário.
    """
    return {
        "resumo_mensal": get_resumo_mensal(db, user_id),
        "status_meta": get_status_meta(db, user_id),
        "resumo_semanal": get_resumo_semanal(db, user_id),
        "por_categoria": get_gastos_por_categoria(db, user_id),
        "ultimos_gastos": get_ultimos_gastos(db, user_id, limit=5),
        "comparativo_3_meses": get_comparativo_mensal(db, user_id, meses=3),
    }
