import re
from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict
from typing import List, Optional
from datetime import datetime, date

# Validação de CPF utilizando o algoritmo oficial, garantindo que apenas CPFs válidos sejam aceitos.
def validar_cpf_matematicamente(cpf: str) -> bool:
    cpf = re.sub(r'[^0-9]', '', cpf)
    if len(cpf) != 11 or len(set(cpf)) == 1:
        return False
    
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito1 = (soma * 10 % 11) % 10
    if int(cpf[9]) != digito1:
        return False
        
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito2 = (soma * 10 % 11) % 10
    if int(cpf[10]) != digito2:
        return False
        
    return True

class ItemPedido(BaseModel):
    id_alimento: str
    gramas: float = Field(gt=0)

class PedidoMarmita(BaseModel):
    tamanho: str
    itens: List[ItemPedido]

class UsuarioCriar(BaseModel):
    nome: str
    email: EmailStr
    celular: str
    cpf: str
    data_nascimento: Optional[date] = None
    senha: str
    aceitou_termos: bool

    @field_validator('cpf')
    def validar_cpf(cls, v):
        cpf_limpo = re.sub(r'[^0-9]', '', v)
        if not validar_cpf_matematicamente(cpf_limpo):
            raise ValueError('CPF inválido ou incorreto.')
        return cpf_limpo

    @field_validator('celular')
    def validar_celular(cls, v):
        celular_limpo = re.sub(r'[^0-9]', '', v)
        if len(celular_limpo) < 10 or len(celular_limpo) > 11:
            raise ValueError('Número de celular inválido')
        return celular_limpo

    @field_validator('senha')
    def validar_senha(cls, v):
        if len(v) < 8:
            raise ValueError('A senha deve ter no mínimo 8 caracteres')
        if not re.search(r'[A-Z]', v):
            raise ValueError('A senha deve conter pelo menos uma letra maiúscula')
        if not re.search(r'[a-z]', v):
            raise ValueError('A senha deve conter pelo menos uma letra minúscula')
        if not re.search(r'\d', v):
            raise ValueError('A senha deve conter pelo menos um número')
        if not re.search(r'[@$!%*?&#]', v):
            raise ValueError('A senha deve conter pelo menos um caractere especial')
        return v

    @field_validator('aceitou_termos')
    def validar_termos(cls, v):
        if not v:
            raise ValueError('O aceite dos Termos de Uso e LGPD é obrigatório')
        return v

class Token(BaseModel):
    access_token: str
    token_type: str

class UsuarioResposta(BaseModel):
    id: int
    nome: str
    email: str
    celular: str | None = None
    cpf: str | None = None
    role: str
    
    model_config = ConfigDict(from_attributes=True)

class PedidoFinalizar(BaseModel):
    tamanho: str | None = None
    itens: List[ItemPedido] = []
    cep: str
    logradouro: str
    numero: str
    complemento: str | None = None
    bairro: str
    cidade: str
    uf: str
    is_combo: bool = False
    combo_id: str | None = None

class IngredienteMinimo(BaseModel):
    nome: str

    model_config = ConfigDict(from_attributes=True)

class ItemPedidoResponse(BaseModel):
    id: int
    ingrediente_id: str
    gramas: float
    ingrediente: IngredienteMinimo # Relacionamento mapeado via ORM
    model_config = ConfigDict(from_attributes=True)

class PedidoResponse(BaseModel):
    id: int
    tamanho_marmita: str
    peso_total_g: float
    preco_total: float
    data_criacao: datetime
    is_combo: bool
    nome_combo: str | None
    status: str
    itens: List[ItemPedidoResponse]

    model_config = ConfigDict(from_attributes=True)

class IngredienteCriar(BaseModel):
    id: str
    nome: str
    categoria: str
    calorias_100g: float
    proteinas_100g: float
    carboidratos_100g: float
    gorduras_100g: float
    preco_100g: float

class ItemComboCriar(BaseModel):
    ingrediente_id: str
    gramas: float

class ComboCriar(BaseModel):
    id: str
    nome: str
    preco: float
    imagem_url: Optional[str] = None
    itens: List[ItemComboCriar]

class IngredienteEditar(BaseModel):
    nome: str
    preco_100g: float

class UsuarioAtualizar(BaseModel):
    nome: Optional[str] = None
    celular: Optional[str] = None

    @field_validator('celular')
    def validar_celular(cls, v):
        if v is None:
            return v
        celular_limpo = re.sub(r'[^0-9]', '', v)
        if len(celular_limpo) < 10 or len(celular_limpo) > 11:
            raise ValueError('Número de celular inválido')
        return celular_limpo

class AlterarSenha(BaseModel):
    senha_atual: str
    nova_senha: str

    @field_validator('nova_senha')
    def validar_senha(cls, v):
        if len(v) < 8:
            raise ValueError('A nova senha deve ter no mínimo 8 caracteres')
        if not re.search(r'[A-Z]', v):
            raise ValueError('A nova senha deve conter ao menos uma letra maiúscula')
        if not re.search(r'[a-z]', v):
            raise ValueError('A nova senha deve conter ao menos uma letra minúscula')
        if not re.search(r'\d', v):
            raise ValueError('A nova senha deve conter ao menos um número')
        if not re.search(r'[@$!%*?&#]', v):
            raise ValueError('A nova senha deve conter ao menos um caractere especial')
        return v