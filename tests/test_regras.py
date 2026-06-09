import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from pydantic import ValidationError

from main import app
from database import get_db
from routers.auth import obter_usuario_atual
from models import TamanhoMarmita, Usuario, Ingrediente
from schemas import validar_cpf_matematicamente, UsuarioCriar, AlterarSenha

client = TestClient(app)


# MOCKS  - Isolam o Banco de Dados

def override_obter_usuario():
    return Usuario(id=1, nome="Inspetor QA", role="user")
# Injetando os mocks para substituir as dependências reais durante os testes, garantindo que os testes sejam isolados e não dependam de um banco de dados real ou de autenticação real.
class MockQuery:
    """Mock SQLAlchemy"""
    def __init__(self, model):
        self.model = model

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        if self.model == TamanhoMarmita:
            return TamanhoMarmita(nome="Pequena", capacidade_maxima_gramas=400, preco_base=15.0)
        return None

    def all(self):
        if self.model == Ingrediente:
            return [Ingrediente(id="BRC001", nome="Frango Grelhado", categoria="proteina", preco_100g=5.0, calorias_100g=100.0, proteinas_100g=20.0, carboidratos_100g=0.0, gorduras_100g=2.0)]
        from models import Pedido
        if self.model == Pedido:
            return []
        return []

def override_get_db():
    db_mock = MagicMock()
    db_mock.query = lambda model: MockQuery(model)
    yield db_mock

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[obter_usuario_atual] = override_obter_usuario

def test_rota_principal_online():
    """Garante que o servidor está de pé e respondendo na raiz."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_senha_fraca_deve_ser_bloqueada():
    with pytest.raises(ValidationError):
        UsuarioCriar(
            nome="Teste", email="teste@teste.com", celular="11999999999",
            cpf="12345678909", senha="123", aceitou_termos=True
        )

def test_celular_invalido_deve_ser_bloqueado():
    with pytest.raises(ValidationError):
        UsuarioCriar(
            nome="Teste", email="teste@teste.com", celular="123", 
            cpf="12345678909", senha="SenhaForte123!", aceitou_termos=True
        )

def test_cpf_falso_deve_ser_bloqueado():
    assert validar_cpf_matematicamente("11111111111") is False

def test_cpf_verdadeiro_deve_passar():
    """Um CPF gerado por validação matemática para cobrir a linha final da função."""
    assert validar_cpf_matematicamente("12345678909") is True

def test_alterar_senha_fraca_bloqueada():
    with pytest.raises(ValidationError):
        AlterarSenha(senha_atual="SenhaForte123!", nova_senha="fraca")

def test_calcular_marmita_com_carga_excedida():
    payload = {
        "tamanho": "Pequena",
        "itens": [
            {"id_alimento": "BRC001", "gramas": 250},
            {"id_alimento": "BRC002", "gramas": 200} 
        ]
    }
    response = client.post("/api/calcular-marmita", json=payload)
    assert response.status_code == 400
    assert "Carga excedida!" in response.json()["detail"]

def test_listar_catalogo_ingredientes():
    """A API deve retornar a lista de ingredientes disponíveis."""
    response = client.get("/api/ingredientes")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

from security import obter_hash_senha, verificar_senha

def test_criptografia_de_senha_valida():
    """Garante que o hash da senha funciona e a verificação bate corretamente."""
    senha_plana = "MinhaSenhaForte123!"
    
    senha_hasheada = obter_hash_senha(senha_plana)
    
    assert verificar_senha(senha_plana, senha_hasheada) is True
    
    assert verificar_senha("SenhaIncorreta", senha_hasheada) is False

def test_criacao_usuario_schema_sucesso():
    """Testa o caminho feliz do schema de usuário (cobre as linhas que faltam no schemas.py)."""
    user = UsuarioCriar(
        nome="João da Silva",
        email="joao@teste.com",
        celular="11999999999",
        cpf="12345678909",
        senha="SenhaForte123!", 
        aceitou_termos=True
    )
    assert user.nome == "João da Silva"
    
def test_listar_meus_pedidos_vazio():
    """Testa se a rota de listar pedidos do cliente logado funciona."""
    response = client.get("/api/meus-pedidos")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

from security import criar_token_acesso, decodificar_token

def test_criacao_e_decodificacao_de_token():
    """Garante que o token JWT é criado e decodificado corretamente."""
    dados_teste = {"sub": "usuario@teste.com"}
    token = criar_token_acesso(dados_teste)
    
    assert isinstance(token, str)
    assert len(token) > 20
    
    email_decodificado = decodificar_token(token)
    assert email_decodificado == "usuario@teste.com"

def test_token_adulterado_deve_falhar():
    """Garante que um token falso levanta ValueError."""
    with pytest.raises(ValueError):
        decodificar_token("eyJhGciOi.FalsoToken.Invalido")