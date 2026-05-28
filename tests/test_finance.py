"""
Testes unitários para o serviço finance.py.

Estratégia: usamos um banco SQLite em memória para não depender
de conexão com o Supabase/PostgreSQL real — os testes rodam offline
e são rápidos.

Como rodar:
    pytest tests/test_finance.py -v
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.models import User, Gasto
from app.services import finance


# ──────────────────────────────────────────────
#  Fixtures — configuração do banco de teste
# ──────────────────────────────────────────────

@pytest.fixture(scope="module")
def db():
    """
    Cria um banco SQLite em memória e retorna uma sessão de teste.
    O banco é destruído ao final do módulo de testes.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()

    # Cria um usuário de teste com meta mensal definida
    usuario = User(
        email="teste@trill.com",
        hashed_password="hash_fake",
        nome="Usuário Teste",
        telefone="11999999999",
        meta_mensal=2000.0,
        is_active=True
    )
    session.add(usuario)
    session.commit()
    session.refresh(usuario)

    # Cria gastos de teste distribuídos no mês corrente e semana atual
    agora = datetime.utcnow()
    inicio_semana = agora - timedelta(days=agora.weekday())  # segunda-feira

    gastos_teste = [
        Gasto(valor=500.0,  descricao="Aluguel",      categoria="Moradia",      data_registro=agora.replace(day=1),   user_id=usuario.id),
        Gasto(valor=350.0,  descricao="Supermercado", categoria="Alimentação",  data_registro=agora.replace(day=5),   user_id=usuario.id),
        Gasto(valor=120.0,  descricao="Uber",          categoria="Transporte",   data_registro=agora.replace(day=10),  user_id=usuario.id),
        Gasto(valor=200.0,  descricao="Cinema",        categoria="Lazer",        data_registro=agora.replace(day=15),  user_id=usuario.id),
        Gasto(valor=80.0,   descricao="Café",          categoria="Alimentação",  data_registro=inicio_semana,          user_id=usuario.id),
        Gasto(valor=60.0,   descricao="Ônibus",        categoria="Transporte",   data_registro=inicio_semana + timedelta(days=1), user_id=usuario.id),
    ]
    for g in gastos_teste:
        session.add(g)
    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def user_id(db):
    """Retorna o ID do usuário de teste."""
    user = db.query(User).filter(User.email == "teste@trill.com").first()
    return user.id


# ──────────────────────────────────────────────
#  Testes — get_resumo_mensal
# ──────────────────────────────────────────────

class TestResumoMensal:
    def test_retorna_dict_com_campos_esperados(self, db, user_id):
        resultado = finance.get_resumo_mensal(db, user_id)
        campos = ["mes", "mes_nome", "ano", "total_gasto",
                  "quantidade_transacoes", "meta_mensal",
                  "percentual_meta", "saldo_restante", "status_meta"]
        for campo in campos:
            assert campo in resultado, f"Campo '{campo}' ausente no resultado"

    def test_total_gasto_correto(self, db, user_id):
        """Total deve ser a soma de todos os gastos do mês atual."""
        resultado = finance.get_resumo_mensal(db, user_id)
        # 500 + 350 + 120 + 200 + 80 + 60 = 1310
        assert resultado["total_gasto"] == 1310.0

    def test_quantidade_transacoes_correta(self, db, user_id):
        resultado = finance.get_resumo_mensal(db, user_id)
        assert resultado["quantidade_transacoes"] == 6

    def test_meta_mensal_presente(self, db, user_id):
        resultado = finance.get_resumo_mensal(db, user_id)
        assert resultado["meta_mensal"] == 2000.0

    def test_percentual_calculado(self, db, user_id):
        resultado = finance.get_resumo_mensal(db, user_id)
        # 1310 / 2000 * 100 = 65.5%
        assert resultado["percentual_meta"] == 65.5

    def test_saldo_restante_calculado(self, db, user_id):
        resultado = finance.get_resumo_mensal(db, user_id)
        # 2000 - 1310 = 690
        assert resultado["saldo_restante"] == 690.0

    def test_status_meta_atencao(self, db, user_id):
        """65.5% da meta → status deve ser 'atencao' (entre 60% e 80%)."""
        resultado = finance.get_resumo_mensal(db, user_id)
        assert resultado["status_meta"] == "atencao"


# ──────────────────────────────────────────────
#  Testes — get_gastos_por_categoria
# ──────────────────────────────────────────────

class TestGastosPorCategoria:
    def test_retorna_lista(self, db, user_id):
        resultado = finance.get_gastos_por_categoria(db, user_id)
        assert isinstance(resultado, list)

    def test_categorias_corretas(self, db, user_id):
        resultado = finance.get_gastos_por_categoria(db, user_id)
        categorias = [r["categoria"] for r in resultado]
        assert "Moradia" in categorias
        assert "Alimentação" in categorias
        assert "Transporte" in categorias
        assert "Lazer" in categorias

    def test_ordenado_por_maior_valor(self, db, user_id):
        resultado = finance.get_gastos_por_categoria(db, user_id)
        totais = [r["total"] for r in resultado]
        assert totais == sorted(totais, reverse=True)

    def test_alimentacao_soma_correta(self, db, user_id):
        resultado = finance.get_gastos_por_categoria(db, user_id)
        alimentacao = next(r for r in resultado if r["categoria"] == "Alimentação")
        # 350 (Supermercado) + 80 (Café) = 430
        assert alimentacao["total"] == 430.0

    def test_soma_percentuais_100(self, db, user_id):
        resultado = finance.get_gastos_por_categoria(db, user_id)
        soma_pct = sum(r["percentual"] for r in resultado)
        assert abs(soma_pct - 100.0) < 0.5  # tolerância de arredondamento


# ──────────────────────────────────────────────
#  Testes — get_ultimos_gastos
# ──────────────────────────────────────────────

class TestUltimosGastos:
    def test_retorna_lista(self, db, user_id):
        resultado = finance.get_ultimos_gastos(db, user_id)
        assert isinstance(resultado, list)

    def test_respeita_limite(self, db, user_id):
        resultado = finance.get_ultimos_gastos(db, user_id, limit=3)
        assert len(resultado) == 3

    def test_campos_esperados(self, db, user_id):
        resultado = finance.get_ultimos_gastos(db, user_id, limit=1)
        item = resultado[0]
        for campo in ["id", "descricao", "valor", "categoria", "data"]:
            assert campo in item

    def test_data_formatada_pt_br(self, db, user_id):
        resultado = finance.get_ultimos_gastos(db, user_id, limit=1)
        data = resultado[0]["data"]
        # Formato esperado: DD/MM/AAAA
        partes = data.split("/")
        assert len(partes) == 3
        assert len(partes[2]) == 4  # ano com 4 dígitos


# ──────────────────────────────────────────────
#  Testes — get_status_meta
# ──────────────────────────────────────────────

class TestStatusMeta:
    def test_usuario_com_meta(self, db, user_id):
        resultado = finance.get_status_meta(db, user_id)
        assert resultado["tem_meta"] is True

    def test_campos_presentes(self, db, user_id):
        resultado = finance.get_status_meta(db, user_id)
        for campo in ["tem_meta", "status", "total_gasto", "meta_mensal",
                      "saldo_restante", "percentual_utilizado", "mensagem"]:
            assert campo in resultado

    def test_mensagem_nao_vazia(self, db, user_id):
        resultado = finance.get_status_meta(db, user_id)
        assert len(resultado["mensagem"]) > 0

    def test_usuario_sem_meta(self, db):
        """Usuário sem meta definida deve retornar tem_meta=False."""
        usuario_sem_meta = User(
            email="semmeta@trill.com",
            hashed_password="hash_fake",
            nome="Sem Meta",
            meta_mensal=None,
            is_active=True
        )
        db.add(usuario_sem_meta)
        db.commit()
        db.refresh(usuario_sem_meta)

        resultado = finance.get_status_meta(db, usuario_sem_meta.id)
        assert resultado["tem_meta"] is False
        assert "mensagem" in resultado


# ──────────────────────────────────────────────
#  Testes — get_resumo_semanal
# ──────────────────────────────────────────────

class TestResumoSemanal:
    def test_retorna_dict(self, db, user_id):
        resultado = finance.get_resumo_semanal(db, user_id)
        assert isinstance(resultado, dict)

    def test_campos_esperados(self, db, user_id):
        resultado = finance.get_resumo_semanal(db, user_id)
        for campo in ["periodo", "total_gasto", "quantidade_transacoes",
                      "media_diaria", "projecao_semana"]:
            assert campo in resultado

    def test_total_maior_ou_igual_zero(self, db, user_id):
        resultado = finance.get_resumo_semanal(db, user_id)
        assert resultado["total_gasto"] >= 0

    def test_media_diaria_coerente(self, db, user_id):
        resultado = finance.get_resumo_semanal(db, user_id)
        assert resultado["media_diaria"] >= 0


# ──────────────────────────────────────────────
#  Testes — get_comparativo_mensal
# ──────────────────────────────────────────────

class TestComparativoMensal:
    def test_retorna_lista(self, db, user_id):
        resultado = finance.get_comparativo_mensal(db, user_id, meses=3)
        assert isinstance(resultado, list)

    def test_quantidade_meses_correta(self, db, user_id):
        resultado = finance.get_comparativo_mensal(db, user_id, meses=3)
        assert len(resultado) == 3

    def test_campos_esperados(self, db, user_id):
        resultado = finance.get_comparativo_mensal(db, user_id, meses=3)
        for item in resultado:
            for campo in ["mes", "mes_nome", "mes_numero", "ano",
                          "total", "variacao_percentual"]:
                assert campo in item

    def test_primeiro_mes_sem_variacao(self, db, user_id):
        """O primeiro mês não tem referência anterior, variação deve ser None."""
        resultado = finance.get_comparativo_mensal(db, user_id, meses=3)
        assert resultado[0]["variacao_percentual"] is None

    def test_totais_nao_negativos(self, db, user_id):
        resultado = finance.get_comparativo_mensal(db, user_id, meses=3)
        for item in resultado:
            assert item["total"] >= 0


# ──────────────────────────────────────────────
#  Testes — get_resumo_completo
# ──────────────────────────────────────────────

class TestResumoCompleto:
    def test_retorna_todos_os_blocos(self, db, user_id):
        resultado = finance.get_resumo_completo(db, user_id)
        blocos = ["resumo_mensal", "status_meta", "resumo_semanal",
                  "por_categoria", "ultimos_gastos", "comparativo_3_meses"]
        for bloco in blocos:
            assert bloco in resultado, f"Bloco '{bloco}' ausente no resumo completo"
