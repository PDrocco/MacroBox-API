from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Conexão com o banco de dados. SQLite para facilitar por enquanto.
SQLALCHEMY_DATABASE_URL = "sqlite:///./macrobox.db"

# Inicializa o motor do banco.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Gerenciador de sessões.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Classe base para os modelos.
Base = declarative_base()

def get_db():
    """Injeta e gerencia a conexão do banco por requisição."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()