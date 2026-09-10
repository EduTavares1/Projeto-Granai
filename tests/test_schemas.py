from datetime import datetime
from app.models.schemas.schemas import GastoCreate, GastoResponse


class TestGastoCreate:
    def test_criacao_basica(self):
        """Testa criação com campos obrigatórios"""
        gasto = GastoCreate(valor=50.0, descricao="Almoço")
        assert gasto.valor == 50.0
        assert gasto.descricao == "Almoço"
        assert gasto.categoria == "Geral"  # valor padrão

    def test_criacao_com_categoria(self):
        """Testa criação com categoria personalizada"""
        gasto = GastoCreate(valor=150.0, descricao="Uber", categoria="Transporte")
        assert gasto.categoria == "Transporte"

    def test_valor_float(self):
        """Testa que o valor é armazenado como float"""
        gasto = GastoCreate(valor=99, descricao="Teste")
        assert isinstance(gasto.valor, float)


class TestGastoResponse:
    def test_herda_campos_de_gasto_create(self):
        """GastoResponse deve conter todos os campos de GastoCreate"""
        agora = datetime.utcnow()
        gasto = GastoResponse(
            id=1,
            user_id=1,
            valor=200.0,
            descricao="Supermercado",
            categoria="Alimentação",
            data_registro=agora,
        )
        assert gasto.id == 1
        assert gasto.valor == 200.0
        assert gasto.descricao == "Supermercado"
        assert gasto.categoria == "Alimentação"
        assert gasto.data_registro == agora

    def test_categoria_padrao(self):
        """Testa que a categoria padrão é 'Geral' quando não informada"""
        agora = datetime.utcnow()
        gasto = GastoResponse(id=2, user_id=1, valor=10.0, descricao="Café", data_registro=agora)
        assert gasto.categoria == "Geral"

    def test_id_inteiro(self):
        """Testa que o id é um inteiro"""
        agora = datetime.utcnow()
        gasto = GastoResponse(id=99, user_id=1, valor=5.0, descricao="X", data_registro=agora)
        assert isinstance(gasto.id, int)
