from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from decimal import Decimal
from typing import List
from database import get_db
from models import Ingrediente, TamanhoMarmita, Usuario, Pedido, ItemPedidoDB, Combo, ItemCombo
from schemas import PedidoMarmita, PedidoFinalizar, PedidoResponse, IngredienteCriar, ComboCriar, IngredienteEditar
from routers.auth import obter_usuario_atual, obter_usuario_admin
import httpx
import asyncio
from bs4 import BeautifulSoup
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

router = APIRouter(prefix="/api", tags=["Pedidos e Cardápio"])

@router.get("/ingredientes")
def listar_ingredientes(db: Session = Depends(get_db), usuario_atual: Usuario = Depends(obter_usuario_atual)):
    ingredientes_db = db.query(Ingrediente).filter(Ingrediente.ativo == True).all()
    
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
        
        fator_float = item.gramas / 100.0  
        fator_decimal = Decimal(str(item.gramas)) / Decimal("100.0")  
        
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

@router.post("/finalizar-pedido")
def finalizar_pedido(pedidos_front: List[PedidoFinalizar], db: Session = Depends(get_db), usuario_atual: Usuario = Depends(obter_usuario_atual)):
    
    ids_pedidos_criados = []

    for pedido_front in pedidos_front:
        if getattr(pedido_front, 'is_combo', False) and pedido_front.combo_id:
            combo_db = db.query(Combo).filter(Combo.id == pedido_front.combo_id, Combo.ativo == True).first()
            if not combo_db:
                raise HTTPException(status_code=400, detail=f"Combo {pedido_front.combo_id} inválido ou inativo.")
            peso_total_combo = sum(item.gramas for item in combo_db.itens)
            
            novo_pedido = Pedido(
                usuario_id=usuario_atual.id,
                tamanho_marmita="Combo Padrão", 
                peso_total_g=peso_total_combo,
                preco_total=combo_db.preco,    
                is_combo=True,
                nome_combo=combo_db.nome,
                cep_entrega=pedido_front.cep,
                logradouro=pedido_front.logradouro,
                numero=pedido_front.numero,
                complemento=pedido_front.complemento,
                bairro=pedido_front.bairro,
                cidade=pedido_front.cidade,
                uf=pedido_front.uf
            )
            db.add(novo_pedido)
            db.flush()
            
            for item in combo_db.itens:
                db.add(ItemPedidoDB(pedido_id=novo_pedido.id, ingrediente_id=item.ingrediente_id, gramas=item.gramas))
            
            ids_pedidos_criados.append(novo_pedido.id)
            continue


        if not pedido_front.tamanho or not pedido_front.itens:
            raise HTTPException(status_code=400, detail="Tamanho e itens são obrigatórios para montar uma marmita.")

        tamanho_db = db.query(TamanhoMarmita).filter(TamanhoMarmita.nome == pedido_front.tamanho).first()
        if not tamanho_db:
            raise HTTPException(status_code=400, detail="Tamanho de marmita não encontrado.")
        
        total_gramas = sum(item.gramas for item in pedido_front.itens)
        if total_gramas > tamanho_db.capacidade_maxima_gramas:
            raise HTTPException(status_code=400, detail=f"Carga excedida! A marmita suporta no máximo {tamanho_db.capacidade_maxima_gramas}g.")

        ids_ingredientes = [item.id_alimento for item in pedido_front.itens]
        ingredientes_db = db.query(Ingrediente).filter(Ingrediente.id.in_(ids_ingredientes)).all()
        mapa_ingredientes = {str(ing.id): ing for ing in ingredientes_db} 
        # Recalculo do preço total para garantir integridade dos dados, evitando manipulação maliciosa do valor no frontend.
        preco_final_recalculado = Decimal(str(tamanho_db.preco_base)) 
        for item in pedido_front.itens:
            alimento_db = mapa_ingredientes.get(item.id_alimento)
            if not alimento_db:
                raise HTTPException(status_code=404, detail=f"Ingrediente {item.id_alimento} não existe.")
            
            fator_decimal = Decimal(str(item.gramas)) / Decimal("100.0")
            preco_final_recalculado += Decimal(str(alimento_db.preco_100g)) * fator_decimal

        novo_pedido = Pedido(
            usuario_id=usuario_atual.id, 
            tamanho_marmita=tamanho_db.nome,
            peso_total_g=total_gramas,
            preco_total=preco_final_recalculado,
            is_combo=False,
            nome_combo=None,
            cep_entrega=pedido_front.cep,
            logradouro=pedido_front.logradouro,
            numero=pedido_front.numero,
            complemento=pedido_front.complemento,
            bairro=pedido_front.bairro,
            cidade=pedido_front.cidade,
            uf=pedido_front.uf
        )
        db.add(novo_pedido)
        db.flush() 

        for item in pedido_front.itens:
            db.add(ItemPedidoDB(pedido_id=novo_pedido.id, ingrediente_id=item.id_alimento, gramas=item.gramas))
        
        ids_pedidos_criados.append(novo_pedido.id)

    db.commit()
    return {"status": "sucesso", "mensagem": f"{len(ids_pedidos_criados)} itens processados com sucesso!"}
    
@router.get("/meus-pedidos", response_model=list[PedidoResponse])
def listar_meus_pedidos(db: Session = Depends(get_db), usuario_atual: Usuario = Depends(obter_usuario_atual)):
    pedidos = db.query(Pedido).filter(Pedido.usuario_id == usuario_atual.id).order_by(Pedido.data_criacao.desc()).all()
    return pedidos


# ROTAS DO PAINEL DE ADMINISTRAÇÃO (B2B)


@router.post("/admin/ingredientes", status_code=201)
def criar_ingrediente(ingrediente: IngredienteCriar, db: Session = Depends(get_db), admin: Usuario = Depends(obter_usuario_admin)):
    existente = db.query(Ingrediente).filter(Ingrediente.id == ingrediente.id).first()
    if existente:
        raise HTTPException(status_code=400, detail="ID de ingrediente já cadastrado.")
    
    novo = Ingrediente(
        id=ingrediente.id,
        nome=ingrediente.nome,
        categoria=ingrediente.categoria,
        calorias_100g=ingrediente.calorias_100g,
        proteinas_100g=ingrediente.proteinas_100g,
        carboidratos_100g=ingrediente.carboidratos_100g,
        gorduras_100g=ingrediente.gorduras_100g,
        preco_100g=ingrediente.preco_100g
    )
    db.add(novo)
    db.commit()
    return {"status": "sucesso", "mensagem": "Ingrediente criado com sucesso."}


@router.delete("/admin/ingredientes/{ingrediente_id}")
def deletar_ingrediente(ingrediente_id: str, db: Session = Depends(get_db), admin: Usuario = Depends(obter_usuario_admin)):
    ingrediente = db.query(Ingrediente).filter(Ingrediente.id == ingrediente_id).first()
    if not ingrediente:
        raise HTTPException(status_code=404, detail="Ingrediente não encontrado.")
    
    # Soft Delete: apenas desativamos o ingrediente no banco
    ingrediente.ativo = False
    db.commit()
    return {"status": "sucesso", "mensagem": "Ingrediente arquivado com sucesso. Ele não aparecerá mais para os clientes."}

@router.put("/admin/ingredientes/{ingrediente_id}")
def editar_ingrediente(ingrediente_id: str, dados: IngredienteEditar, db: Session = Depends(get_db), admin: Usuario = Depends(obter_usuario_admin)):
    ingrediente = db.query(Ingrediente).filter(Ingrediente.id == ingrediente_id).first()
    if not ingrediente:
        raise HTTPException(status_code=404, detail="Ingrediente não encontrado.")
    
    ingrediente.nome = dados.nome
    ingrediente.preco_100g = dados.preco_100g
    db.commit()
    return {"status": "sucesso", "mensagem": "Ingrediente atualizado com sucesso."}

@router.post("/admin/combos", status_code=201)
def criar_combo(combo: ComboCriar, db: Session = Depends(get_db), admin: Usuario = Depends(obter_usuario_admin)):
    existente = db.query(Combo).filter(Combo.id == combo.id).first()
    if existente:
        raise HTTPException(status_code=400, detail="ID de combo já cadastrado.")
    
    novo_combo = Combo(id=combo.id, 
                       nome=combo.nome, 
                       preco=combo.preco, 
                       imagem_url=combo.imagem_url
    )
    db.add(novo_combo)
    db.flush()

    for item in combo.itens:
        ingrediente = db.query(Ingrediente).filter(Ingrediente.id == item.ingrediente_id).first()
        if not ingrediente:
            raise HTTPException(status_code=404, detail=f"Ingrediente {item.ingrediente_id} não existe.")
        
        db.add(ItemCombo(combo_id=novo_combo.id, ingrediente_id=item.ingrediente_id, gramas=item.gramas))
    
    db.commit()
    return {"status": "sucesso", "mensagem": "Combo catalogado com sucesso."}

@router.get("/admin/tbca/buscar")
async def buscar_alimento_tbca(termo: str, admin: Usuario = Depends(obter_usuario_admin)):
    url_busca = "https://www.tbca.net.br/base-dados/composicao_alimentos.php"
    headers = { "User-Agent": "Mozilla/5.0", "Origin": "https://www.tbca.net.br", "Referer": url_busca }
    formData = { "guarda": "tomo1", "produto": termo, "cmb_grupo": "", "cmb_tipo_alimento": "" }
    #
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(url_busca, data=formData, headers=headers, timeout=15.0)
        
        soup = await asyncio.to_thread(BeautifulSoup, res.text, 'html.parser')
        tabela = soup.find('table')
        
        if not tabela or not tabela.find('tbody'):
            return []
            
        opcoes = []
        for linha in tabela.find('tbody').find_all('tr')[:10]: 
            colunas = linha.find_all('td')
            if len(colunas) >= 2:
                link_tag = colunas[0].find('a')
                if link_tag and 'href' in link_tag.attrs:
                    href = link_tag['href']
                    chave_url = href.split('?')[1] if '?' in href else ""
                    id_alimento = link_tag.text.strip()
                    nome_alimento = colunas[1].text.strip()
                    opcoes.append({"chave": chave_url, "id": id_alimento, "nome": nome_alimento})
        return opcoes
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao consultar TBCA.")

@router.post("/admin/tbca/importar")
async def importar_alimento_tbca(dados: dict, db: Session = Depends(get_db), admin: Usuario = Depends(obter_usuario_admin)):
    chave = dados.get("chave")
    id_alimento = dados.get("id")
    nome = dados.get("nome")
    categoria = dados.get("categoria")
    preco = dados.get("preco")

    if db.query(Ingrediente).filter(Ingrediente.id == id_alimento).first():
        raise HTTPException(status_code=400, detail="Ingrediente já existe no sistema.")
        
    url_detalhes = f"https://www.tbca.net.br/base-dados/int_composicao_alimentos.php?{chave}"
    
    # Uso de httpx assíncrono para evitar bloqueio do servidor durante a consulta ao TBCA, que pode ser lenta.
    #  O parseamento do HTML com BeautifulSoup é feito em thread separada.
    async with httpx.AsyncClient() as client:
        res = await client.get(url_detalhes, headers={"User-Agent": "Mozilla/5.0"}, timeout=15.0)
        
    # Processamento em thread
    soup = await asyncio.to_thread(BeautifulSoup, res.text, 'html.parser')
    tabela = soup.find('table')
    
    macros = {"calorias": 0.0, "proteinas": 0.0, "carbos": 0.0, "gorduras": 0.0}
    if tabela and tabela.find('tbody'):
        for ln in tabela.find('tbody').find_all('tr'):
            cols = [c.text.strip() for c in ln.find_all('td')]
            if len(cols) < 3: continue
            comp, unid, val = cols[0], cols[1].lower(), cols[2].replace(',', '.')
            try:
                v_float = float(val) if val not in ["-", "NA", "tr", ""] else 0.0
            except:
                v_float = 0.0
            
            if comp == "Energia" and unid == "kcal": macros["calorias"] = v_float
            elif comp == "Proteína": macros["proteinas"] = v_float
            elif comp == "Carboidrato disponível": macros["carbos"] = v_float
            elif comp == "Lipídios": macros["gorduras"] = v_float
            
    nome_limpo = nome.split(",")[0].strip().title()
            
    novo = Ingrediente(
        id=id_alimento, nome=nome_limpo, categoria=categoria,
        calorias_100g=macros["calorias"], proteinas_100g=macros["proteinas"],
        carboidratos_100g=macros["carbos"], gorduras_100g=macros["gorduras"],
        preco_100g=preco
    )
    db.add(novo)
    db.commit()
    return {"status": "sucesso", "mensagem": f"{nome_limpo} importado e salvo com sucesso!"}

class StatusUpdate(BaseModel):
    novo_status: str


@router.get("/admin/pedidos")
def listar_todos_pedidos(db: Session = Depends(get_db), admin: Usuario = Depends(obter_usuario_admin)):

    pedidos = db.query(Pedido).options(
        joinedload(Pedido.usuario),
        joinedload(Pedido.itens).joinedload(ItemPedidoDB.ingrediente)
    ).order_by(Pedido.data_criacao.desc()).all()
    
    resultado = []
    for p in pedidos:
        resultado.append({
            "id": p.id,
            "data": p.data_criacao.strftime("%d/%m/%Y %H:%M"),
            "cliente_nome": p.usuario.nome,
            "cliente_telefone": p.usuario.celular,
            "status": p.status,
            "tipo": "Combo" if p.is_combo else "Monte sua Box",
            "detalhes": p.nome_combo if p.is_combo else f"Marmita {p.tamanho_marmita} ({p.peso_total_g}g)",
            "valor": float(p.preco_total),
            "endereco_completo": f"{p.logradouro}, {p.numero} - {p.bairro}, {p.cidade}"
        })
        
    return resultado

@router.put("/admin/pedidos/{pedido_id}/status")
def atualizar_status_pedido(pedido_id: int, status_update: StatusUpdate, db: Session = Depends(get_db), admin: Usuario = Depends(obter_usuario_admin)):

    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")
    
    status_permitidos = ["Pendente", "Preparando", "Saiu para Entrega", "Entregue", "Cancelado"]
    if status_update.novo_status not in status_permitidos:
        raise HTTPException(status_code=400, detail="Status inválido.")
        
    pedido.status = status_update.novo_status
    db.commit()
    return {"status": "sucesso", "mensagem": f"Status atualizado para {status_update.novo_status}!"}

@router.delete("/admin/pedidos/{pedido_id}")
def cancelar_pedido_admin(pedido_id: int, db: Session = Depends(get_db), admin: Usuario = Depends(obter_usuario_admin)):

    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")
   
    if pedido.status == "Cancelado":
        raise HTTPException(status_code=400, detail="Este pedido já está cancelado.")
    
    pedido.status = "Cancelado"
    db.commit()
    return {"status": "sucesso", "mensagem": "Pedido removido do painel."}

@router.get("/combos")
def listar_combos_publicos(db: Session = Depends(get_db)):

    combos_db = db.query(Combo).filter(Combo.ativo == True).options(
        joinedload(Combo.itens).joinedload(ItemCombo.ingrediente)
    ).all()
    
    resultado = []
    for combo in combos_db:
        total_calorias = 0.0
        total_proteinas = 0.0
        total_carbos = 0.0
        total_gorduras = 0.0
        nomes_ingredientes = []
        
        for item in combo.itens:
            ing = item.ingrediente
            if ing:
                nomes_ingredientes.append(ing.nome)
                fator = float(item.gramas) / 100.0
                total_calorias += ing.calorias_100g * fator
                total_proteinas += ing.proteinas_100g * fator
                total_carbos += ing.carboidratos_100g * fator
                total_gorduras += ing.gorduras_100g * fator
        
        descricao = f"Combinação de: {', '.join(nomes_ingredientes)}." if nomes_ingredientes else "Combo especial da cozinha."
        
        resultado.append({
            "id": combo.id,
            "nome": combo.nome,
            "descricao": descricao,
            "preco": float(combo.preco),
            "imagem_url": combo.imagem_url or "/Macrobox_vazia.jpg", 
            "calorias": round(total_calorias, 0),
            "proteinas": round(total_proteinas, 1),
            "carbos": round(total_carbos, 1),
            "gorduras": round(total_gorduras, 1)
        })
        
    return resultado