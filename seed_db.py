import json
import os
from database import engine, SessionLocal, Base
from models import Ingrediente, TamanhoMarmita, Usuario

def popular_banco():
    """Script para popular o banco SQLite com dados do arquivo JSON."""
    print("Criando o banco de dados...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # 1. Popula tamanhos das marmitas.
    if db.query(TamanhoMarmita).count() == 0:
        print("Adicionando embalagens...")
        tamanhos = [
            TamanhoMarmita(nome="Pequena", capacidade_maxima_gramas=400, preco_base=5.00),
            TamanhoMarmita(nome="Média", capacidade_maxima_gramas=600, preco_base=7.00),
            TamanhoMarmita(nome="Grande", capacidade_maxima_gramas=800, preco_base=9.00)
        ]
        db.add_all(tamanhos)
        db.commit()

    # 2. Popula ingredientes a partir do JSON.
    if db.query(Ingrediente).count() == 0:
        print("Lendo json e cadastrando ingredientes...")
        if os.path.exists("banco_alimentos.json"):
            with open("banco_alimentos.json", "r", encoding="utf-8") as f:
                dados_json = json.load(f)

            for item in dados_json:
                novo_ingrediente = Ingrediente(
                    id=item["id"], 
                    nome=item["nome"],
                    categoria=item["categoria"],
                    calorias_100g=item["macros"]["calorias"],
                    proteinas_100g=item["macros"]["proteinas"],
                    carboidratos_100g=item["macros"]["carbos"],
                    gorduras_100g=item["macros"]["gorduras"],
                    preco_100g=item["preco_adicional"]
                )
                db.add(novo_ingrediente)
            
            db.commit()
            print(f"Feito. {len(dados_json)} alimentos cadastrados.")
        else:
            print("Erro: banco_alimentos.json não encontrado.")
    else:
        print("Banco já populado.")

    db.close()

if __name__ == "__main__":
    popular_banco()