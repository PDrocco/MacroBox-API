import json
import os
from database import engine, SessionLocal, Base
from models import Ingrediente, TamanhoMarmita, Usuario, Combo, ItemCombo

def higienizar_nome_tbca(nome_bruto: str) -> str:
    # Limpa os nomes da API
    n = nome_bruto.lower()
    if "frango" in n: return "Frango Grelhado Premium"
    if "patinho" in n or "boi" in n: return "Patinho Magro Grelhado"
    if "lombo" in n or "porco" in n: return "Lombo Suíno Assado"
    if "tilápia" in n or "peixe" in n: return "Filé de Tilápia com Ervas"
    if "arroz integral" in n: return "Arroz Integral"
    if "batata doce" in n: return "Batata Doce Rústica Assada"
    if "mandioca" in n or "aipim" in n: return "Mandioca Cozida"
    if "brócolis" in n: return "Brócolis Ninja ao Vapor"
    if "cenoura" in n: return "Cenoura em Cubos Cozida"
    if "quinoa" in n: return "Quinoa Real"
    return nome_bruto.split(",")[0].strip().title()

def popular_banco():
    """Script para popular o banco SQLite com dados do arquivo JSON."""
    print("Criando o banco de dados...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    if db.query(TamanhoMarmita).count() == 0:
        print("Adicionando embalagens...")
        tamanhos = [
            TamanhoMarmita(nome="Pequena", capacidade_maxima_gramas=400, preco_base=5.00),
            TamanhoMarmita(nome="Média", capacidade_maxima_gramas=600, preco_base=7.00),
            TamanhoMarmita(nome="Grande", capacidade_maxima_gramas=800, preco_base=9.00)
        ]
        db.add_all(tamanhos)
        db.commit()

    if db.query(Ingrediente).count() == 0:
        print("Lendo json e cadastrando ingredientes...")
        if os.path.exists("banco_alimentos.json"):
            with open("banco_alimentos.json", "r", encoding="utf-8") as f:
                dados_json = json.load(f)

            for item in dados_json:
                nome_comercial = higienizar_nome_tbca(item["nome"])
                novo_ingrediente = Ingrediente(
                    id=item["id"], 
                    nome=nome_comercial,
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
    if db.query(Combo).count() == 0:
        print("Adicionando combos oficiais...")
        combo1 = Combo(id="hipertrofia", nome="Combo Hipertrofia", preco=32.50)
        combo2 = Combo(id="pescetariano", nome="Fit Pescetariano", preco=38.00)
        db.add_all([combo1, combo2])
        db.commit()

        itens_combo = [
            ItemCombo(combo_id="hipertrofia", ingrediente_id="BRC0915F", gramas=150),
            ItemCombo(combo_id="hipertrofia", ingrediente_id="BRC0884B", gramas=150),
            ItemCombo(combo_id="hipertrofia", ingrediente_id="BRC0150B", gramas=100),
            ItemCombo(combo_id="pescetariano", ingrediente_id="BRC0099E", gramas=150),
            ItemCombo(combo_id="pescetariano", ingrediente_id="BRC0399A", gramas=100),
            ItemCombo(combo_id="pescetariano", ingrediente_id="BRC0913B", gramas=50),
        ]
        db.add_all(itens_combo)
        db.commit()
        print("Combos cadastrados com sucesso.")
    db.close()

if __name__ == "__main__":
    popular_banco()