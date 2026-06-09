from sqlalchemy import Column, Integer, String, Float, Numeric, Boolean, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base

class Ingrediente(Base):
    __tablename__ = "ingredientes"

    id = Column(String, primary_key=True, index=True)
    nome = Column(String, index=True, nullable=False)
    categoria = Column(String, nullable=False)
    
    calorias_100g = Column(Float, nullable=False)
    proteinas_100g = Column(Float, nullable=False)
    carboidratos_100g = Column(Float, nullable=False)
    gorduras_100g = Column(Float, nullable=False)
    
    preco_100g = Column(Numeric(10, 2), nullable=False)
    ativo = Column(Boolean, default=True)

class TamanhoMarmita(Base):
    __tablename__ = "tamanhos_marmita"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True, nullable=False)
    capacidade_maxima_gramas = Column(Integer, nullable=False)
    preco_base = Column(Numeric(10, 2), nullable=False)

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    celular = Column(String, nullable=False)
    cpf = Column(String, unique=True, index=True, nullable=False)
    data_nascimento = Column(Date, nullable=True)
    senha_hash = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)
    aceitou_termos = Column(Boolean, nullable=False, default=False)
    data_aceite_termos = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    tamanho_marmita = Column(String, nullable=False)
    peso_total_g = Column(Float, nullable=False)
    preco_total = Column(Numeric(10, 2), nullable=False)
    
    status = Column(String, default="Pendente", nullable=False)
    
    is_combo = Column(Boolean, nullable=False, default=False)
    nome_combo = Column(String, nullable=True)
    
    # Dados de Logística
    cep_entrega = Column(String, nullable=False)
    logradouro = Column(String, nullable=False)
    numero = Column(String, nullable=False)
    complemento = Column(String, nullable=True)
    bairro = Column(String, nullable=False)
    cidade = Column(String, nullable=False)
    uf = Column(String, nullable=False)
    
    data_criacao = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    usuario = relationship("Usuario")
    itens = relationship("ItemPedidoDB", back_populates="pedido")

class ItemPedidoDB(Base):
    __tablename__ = "itens_pedido"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False)
    ingrediente_id = Column(String, ForeignKey("ingredientes.id"), nullable=False)
    gramas = Column(Float, nullable=False)

    pedido = relationship("Pedido", back_populates="itens")
    ingrediente = relationship("Ingrediente")

class Combo(Base):
    __tablename__ = "combos"

    id = Column(String, primary_key=True, index=True) 
    nome = Column(String, nullable=False)
    preco = Column(Numeric(10, 2), nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    imagem_url = Column(String, nullable=True)
    itens = relationship("ItemCombo", back_populates="combo")

class ItemCombo(Base):
    __tablename__ = "itens_combo"

    id = Column(Integer, primary_key=True, index=True)
    combo_id = Column(String, ForeignKey("combos.id"), nullable=False)
    ingrediente_id = Column(String, ForeignKey("ingredientes.id"), nullable=False)
    gramas = Column(Float, nullable=False)

    combo = relationship("Combo", back_populates="itens")
    ingrediente = relationship("Ingrediente")