from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal
from database import get_db
from models import Ingrediente, TamanhoMarmita, Usuario
from schemas import PedidoMarmita

from routers.auth import obter_usuario_atual

router = APIRouter(prefix="/api", tags=["Pedidos e Cardápio"])

@router.get("/ingredientes")
def listar_ingredientes(db: Session = Depends(get_db), usuario_atual: Usuario = Depends(obter_usuario_atual)):
    ingredientes_db = db.query(Ingrediente).all()
    
    resultado = []
    for item in ingredientes_db:
        resultado.append({
            "id": str(item.id), 
            "nome": item.nome,
            "categoria": item.categoria,
            "preco_adicional": float(item.preco_100g),
            "porcao_base_g": 100 
        })
        
    return resultado

@router.post("/calcular-marmita")
def calcular_marmita(pedido: PedidoMarmita, db: Session = Depends(get_db), usuario_atual: Usuario = Depends(obter_usuario_atual)):
    tamanho_db = db.query(TamanhoMarmita).filter(TamanhoMarmita.nome == pedido.tamanho).first()
    if not tamanho_db:
        raise HTTPException(status_code=400, detail="Tamanho de marmita não encontrado.")
    
    total_gramas_pedido = sum(item.gramas for item in pedido.itens)
    
    if total_gramas_pedido > tamanho_db.capacidade_maxima_gramas:
        raise HTTPException(
            status_code=400, 
            detail=f"Carga excedida! A marmita {pedido.tamanho} suporta no máximo {tamanho_db.capacidade_maxima_gramas}g. Selecionado: {total_gramas_pedido}g."
        )

    ids_pedidos = [item.id_alimento for item in pedido.itens]
    ingredientes_db = db.query(Ingrediente).filter(Ingrediente.id.in_(ids_pedidos)).all()
    mapa_ingredientes = {ing.id: ing for ing in ingredientes_db}

    # Inicialização de totais
    total_calorias = 0.0
    total_proteinas = 0.0
    total_carbos = 0.0
    total_gorduras = 0.0
    preco_final = tamanho_db.preco_base
    
    detalhes_calculados = []

    for item in pedido.itens:
        alimento_db = mapa_ingredientes.get(item.id_alimento)
        if not alimento_db:
            raise HTTPException(status_code=404, detail=f"Ingrediente {item.id_alimento} não existe no banco.")

        
        fator_float = item.gramas / 100.0  # Para cálculos com Float (Macros)
        fator_decimal = Decimal(str(item.gramas)) / Decimal("100.0")  # Para cálculos com Numeric (Dinheiro)
        
        cal_item = alimento_db.calorias_100g * fator_float
        prot_item = alimento_db.proteinas_100g * fator_float
        carb_item = alimento_db.carboidratos_100g * fator_float
        gord_item = alimento_db.gorduras_100g * fator_float
        preco_item = alimento_db.preco_100g * fator_decimal

        total_calorias += cal_item
        total_proteinas += prot_item
        total_carbos += carb_item
        total_gorduras += gord_item
        preco_final += preco_item

        detalhes_calculados.append({
            "nome": alimento_db.nome,
            "gramas": float(item.gramas),
            "calorias": round(cal_item, 2),
            "preco": float(round(preco_item, 2))
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
            "preco_total_reais": float(round(preco_final, 2))
        },
        "detalhes": detalhes_calculados
    }