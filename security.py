import os
from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
from dotenv import load_dotenv

load_dotenv()

# Configurações Token JWT
SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise ValueError("ERRO CRÍTICO: Variável de ambiente SECRET_KEY não foi encontrada.")

ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
# O uso do bcrypt atrasa ataques de força bruta ou rainbow tables ao exigir mais tempo de CPU por hash.
def obter_hash_senha(senha: str) -> str:
    salt = bcrypt.gensalt()
    hash_bytes = bcrypt.hashpw(senha.encode('utf-8'), salt)
    return hash_bytes.decode('utf-8')

def verificar_senha(senha_plana: str, senha_criptografada: str) -> bool:
    try:
        return bcrypt.checkpw(
            senha_plana.encode('utf-8'), 
            senha_criptografada.encode('utf-8')
        )
    except ValueError:
        return False

def criar_token_acesso(dados: dict) -> str:
    para_codificar = dados.copy()
    agora = datetime.now(timezone.utc)
    expiracao = agora + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    para_codificar.update({
        "exp": expiracao,
        "iat": agora
    })
    
    return jwt.encode(para_codificar, SECRET_KEY, algorithm=ALGORITHM)

def decodificar_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except ExpiredSignatureError:
        raise ValueError("Token expirado")
    except InvalidTokenError:
        raise ValueError("Token inválido ou adulterado")