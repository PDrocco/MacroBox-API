from pydantic import BaseModel, Field
from typing import List

class ItemPedido(BaseModel):
    id_alimento: str
    gramas: float = Field(gt=0)

class PedidoMarmita(BaseModel):
    tamanho: str
    itens: List[ItemPedido]

class UsuarioCriar(BaseModel):
    nome: str
    email: str
    senha: str
    aceitou_termos: bool

class Token(BaseModel):
    access_token: str
    token_type: str

class UsuarioResposta(BaseModel):
    id: int
    nome: str
    email: str
    role: str