from sqlalchemy import Column, Integer, String, Float
from database import Base

class Ingrediente(Base):
    """Tabela de alimentos do cardápio."""
    __tablename__ = "ingredientes"

    id = Column(String, primary_key=True, index=True)
    nome = Column(String, index=True, nullable=False)
    categoria = Column(String, nullable=False)
    
    # Valores nutricionais padronizados para 100g.
    calorias_100g = Column(Float, nullable=False)
    proteinas_100g = Column(Float, nullable=False)
    carboidratos_100g = Column(Float, nullable=False)
    gorduras_100g = Column(Float, nullable=False)
    
    # Preço cobrado a cada 100g.
    preco_100g = Column(Float, nullable=False)

class TamanhoMarmita(Base):
    """Tabela de regras das embalagens (P, M, G)."""
    __tablename__ = "tamanhos_marmita"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True, nullable=False)
    capacidade_maxima_gramas = Column(Integer, nullable=False)
    preco_base = Column(Float, nullable=False)