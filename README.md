# MacroBox API (Back-end)
Este é o back-end do projeto MacroBox, desenvolvido com FastAPI e SQLite. Ele gerencia as regras de negócio, valida a capacidade das marmitas e calcula os macronutrientes em tempo real. 

## Tecnologias Utilizadas

Python 3 
- FastAPI: Framework web de alta performance. 
- SQLAlchemy: ORM para comunicação com o banco de dados. 
- SQLite: Banco de dados relacional local. 

## Instruções para Execução
Configurar Ambiente Virtual:
No terminal, dentro da pasta do projeto, execute:

`python -m venv venv`

## Ativar o Ambiente:
Windows: `.\venv\Scripts\activate`

Mac/Linux: `source venv/bin/activate`

## Instalar Dependências:
pip install -r requirements.txt 

## Preparar o Banco de Dados:
Gere as tabelas e popule os dados da TBCA (USP) executando:
`python seed_db.py`

## Iniciar a API:
`uvicorn main:app --reload`
Acesse em: http://localhost:8000
