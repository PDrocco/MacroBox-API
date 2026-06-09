# MacroBox API — Back-end

Este é o back-end da plataforma **MacroBox**, um ecossistema integrado para montagem, comercialização e gestão logística de refeições saudáveis customizadas.

A API foi desenvolvida seguindo o padrão **RESTful** e estruturada em camadas independentes de lógica de negócios, segurança e persistência de dados.

O sistema implementa motores de validação para restrição de capacidade física das embalagens, cálculo sob demanda de propriedades nutricionais e precificação, além de mecanismos de conformidade com a **Lei Geral de Proteção de Dados Pessoais (LGPD)**, como mascaramento de dados (*Data Masking*) e anonimização lógica de contas.

## Tecnologias Utilizadas

* **Python 3.11+**
* **FastAPI** — Framework web assíncrono de alta performance.
* **SQLAlchemy** — ORM (*Object-Relational Mapping*) para abstração e persistência de dados.
* **PostgreSQL / Supabase** — Banco de dados relacional para armazenamento seguro e escalável.
* **Bcrypt & PyJWT** — Mecanismos para hash de senhas e emissão de tokens de sessão em cookies `HttpOnly`.
* **HTTPX & BeautifulSoup4** — Ferramentas para consulta e extração automatizada de dados nutricionais.

## Funcionalidades Principais do Servidor

* **Autenticação segura:** login baseado em JWT trafegado via cookies com a flag `HttpOnly`.
* **Motor de regras:** validação de segurança no fechamento de pedidos, recalculando preços e pesos diretamente no servidor para evitar fraudes.
* **Consulta à TBCA/USP:** integração automatizada por raspagem controlada de dados para importação nutricional de insumos.
* **Subsistema LGPD:** recursos para exportação cadastral em formato JSON, portabilidade de dados e exclusão de contas com anonimização lógica de dados sensíveis.

## Instruções para Execução

### 1. Configurar variáveis de ambiente

Crie um arquivo chamado `.env` na raiz da pasta `MacroBox-API` e insira as credenciais de configuração:

```env
SECRET_KEY=sua_chave_secreta_aqui
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
DATABASE_URL=sua_string_de_conexao_postgresql_supabase
```



### 2. Configurar ambiente virtual

No terminal, dentro da pasta do projeto, execute:

```bash
python -m venv venv
```

### 3. Ativar o ambiente virtual

No Windows PowerShell:

```bash
.\venv\Scripts\activate
```

No Linux ou macOS:

```bash
source venv/bin/activate
```

### 4. Instalar dependências

```bash
pip install -r requirements.txt
```

### 5. Preparar o banco de dados

Para gerar a estrutura das tabelas via ORM e inserir a carga inicial de insumos pré-configurados, execute:

```bash
python seed_db.py
```

> Esta etapa é opcional caso o banco Supabase/PostgreSQL já esteja configurado e populado.

### 6. Iniciar a API

```bash
uvicorn main:app --reload
```

O servidor estará ativo em:

```text
http://localhost:8000
```

A documentação interativa da API, gerada automaticamente pelo FastAPI, pode ser acessada em:

```text
http://localhost:8000/docs
```

## Estrutura Geral do Back-end

```text
MacroBox-API/
├── routers/
│   ├── auth.py
│   └── pedidos.py
├── tests/
│   └── test_regras.py
├── database.py
├── main.py
├── models.py
├── schemas.py
├── security.py
├── seed_db.py
├── requirements.txt
└── README.md
```

## Observações de Segurança

* As senhas são armazenadas utilizando hash com **Bcrypt**.
* A autenticação utiliza **JWT** armazenado em cookie `HttpOnly`.
* O servidor recalcula preços e pesos no momento da finalização do pedido.
* As rotas administrativas exigem usuário autenticado com permissão de administrador.
* As credenciais do banco e a chave secreta da aplicação devem ser mantidas exclusivamente em variáveis de ambiente.

## Status do Projeto

Projeto desenvolvido como parte do **Projeto Final de Curso em Engenharia de Software** da Universidade de Mogi das Cruzes.
