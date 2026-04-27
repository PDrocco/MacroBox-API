from sqlalchemy import Column, Integer, String, Float, Numeric, Boolean, DateTime
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
    senha_hash = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)

    aceitou_termos = Column(Boolean, nullable=False, default=False)
    data_aceite_termos = Column(DateTime, nullable=True)