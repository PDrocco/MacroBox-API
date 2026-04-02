from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from database import get_db
from models import Ingrediente, TamanhoMarmita

app = FastAPI(title="MacroBox API")

# Configuração de CORS para o frontend.
ORIGENS_PERMITIDAS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENS_PERMITIDAS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Schemas (Pydantic) ---
class ItemPedido(BaseModel):
    id_alimento: str
    gramas: float

class PedidoMarmita(BaseModel):
    tamanho: str
    itens: List[ItemPedido]

# --- Rotas ---
@app.get("/")
def home():
    """Health check da API."""
    return {"status": "ok", "mensagem": "MacroBox API Operacional."}

@app.get("/api/ingredientes")
def listar_ingredientes(db: Session = Depends(get_db)):
    """Lista todos os ingredientes cadastrados."""
    ingredientes_db = db.query(Ingrediente).all()
    
    resultado = []
    for item in ingredientes_db:
        resultado.append({
            "id": str(item.id), 
            "nome": item.nome,
            "categoria": item.categoria,
            "preco_adicional": item.preco_100g,
            "porcao_base_g": 100 
        })
        
    return resultado

@app.post("/api/calcular-marmita")
def calcular_marmita(pedido: PedidoMarmita, db: Session = Depends(get_db)):
    """Valida capacidade da embalagem e calcula macros totais do pedido."""
    
    # Busca a embalagem.
    tamanho_db = db.query(TamanhoMarmita).filter(TamanhoMarmita.nome == pedido.tamanho).first()
    if not tamanho_db:
        raise HTTPException(status_code=400, detail="Tamanho de marmita não encontrado.")
    
    total_gramas_pedido = sum(item.gramas for item in pedido.itens)
    
    # Valida o limite de peso.
    if total_gramas_pedido > tamanho_db.capacidade_maxima_gramas:
        raise HTTPException(
            status_code=400, 
            detail=f"Carga excedida! A marmita {pedido.tamanho} suporta no máximo {tamanho_db.capacidade_maxima_gramas}g. Selecionado: {total_gramas_pedido}g."
        )

    # Busca todos os ingredientes do pedido em uma única consulta.
    ids_pedidos = [item.id_alimento for item in pedido.itens]
    ingredientes_db = db.query(Ingrediente).filter(Ingrediente.id.in_(ids_pedidos)).all()
    mapa_ingredientes = {ing.id: ing for ing in ingredientes_db}

    # Acumuladores.
    total_calorias = 0.0
    total_proteinas = 0.0
    total_carbos = 0.0
    total_gorduras = 0.0
    preco_final = tamanho_db.preco_base
    
    detalhes_calculados = []

    # Cálculo dos macros por alimento na memória (sem chamar o banco).
    for item in pedido.itens:
        alimento_db = mapa_ingredientes.get(item.id_alimento)
        if not alimento_db:
            raise HTTPException(status_code=404, detail=f"Ingrediente {item.id_alimento} não existe no banco.")

        fator = item.gramas / 100.0
        
        cal_item = alimento_db.calorias_100g * fator
        prot_item = alimento_db.proteinas_100g * fator
        carb_item = alimento_db.carboidratos_100g * fator
        gord_item = alimento_db.gorduras_100g * fator
        preco_item = alimento_db.preco_100g * fator

        total_calorias += cal_item
        total_proteinas += prot_item
        total_carbos += carb_item
        total_gorduras += gord_item
        preco_final += preco_item

        detalhes_calculados.append({
            "nome": alimento_db.nome,
            "gramas": item.gramas,
            "calorias": round(cal_item, 2),
            "preco": round(preco_item, 2)
        })

    return {
        "status": "sucesso",
        "resumo": {
            "tamanho": tamanho_db.nome,
            "peso_total_g": total_gramas_pedido,
            "capacidade_restante_g": tamanho_db.capacidade_maxima_gramas - total_gramas_pedido,
            "macros_totais": {
                "calorias": round(total_calorias, 2),
                "proteinas": round(total_proteinas, 2),
                "carbos": round(total_carbos, 2),
                "gorduras": round(total_gorduras, 2)
            },
            "preco_total_reais": round(preco_final, 2)
        },
        "detalhes": detalhes_calculados
    }