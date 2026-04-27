from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from slowapi import Limiter

from database import get_db
from models import Usuario
from schemas import UsuarioCriar, Token, UsuarioResposta
from security import obter_hash_senha, verificar_senha, criar_token_acesso, decodificar_token

# Configurações Infraestrutura de Proxy e Rate Limiting
def obter_ip_real(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0]
    return request.client.host

limiter = Limiter(key_func=obter_ip_real)
router = APIRouter(prefix="/api/auth", tags=["Autenticação"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Dependências de Autorização Base
def obter_usuario_atual(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    excecao_credenciais = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        email = decodificar_token(token)
        if email is None:
            raise excecao_credenciais
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if usuario is None:
        raise excecao_credenciais
    
    return usuario

# Dependências de Autorização Nível Admin
def obter_usuario_admin(usuario: Usuario = Depends(obter_usuario_atual)):
    if usuario.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Privilégios de administrador necessários."
        )
    return usuario

# Rotas de Autenticação
@router.post("/registrar", response_model=Token)
@limiter.limit("5/minute")
def registrar_usuario(request: Request, usuario: UsuarioCriar, db: Session = Depends(get_db)):
    if not usuario.aceitou_termos:
        raise HTTPException(status_code=400, detail="É necessário aceitar os termos de uso para se registrar.")
    
    usuario_existente = db.query(Usuario).filter(Usuario.email == usuario.email).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="Email já cadastrado.")
    
    # O primeiro usuário no sistema se torna admin automaticamente
    total_usuarios = db.query(Usuario).count()
    role_atribuida = "admin" if total_usuarios == 0 else "user"
    
    novo_usuario = Usuario(
        nome=usuario.nome,
        email=usuario.email,
        senha_hash=obter_hash_senha(usuario.senha),
        role=role_atribuida
    )
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    
    token = criar_token_acesso(dados={"sub": novo_usuario.email})
    return {"access_token": token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == form_data.username).first()
    if not usuario or not verificar_senha(form_data.password, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = criar_token_acesso(dados={"sub": usuario.email})
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me", response_model=UsuarioResposta)
def ler_usuario_atual(usuario_atual: Usuario = Depends(obter_usuario_atual)):
    return usuario_atual

@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def deletar_conta_lgpd(db: Session = Depends(get_db), usuario_atual: Usuario = Depends(obter_usuario_atual)):
    db.delete(usuario_atual)
    db.commit()
    return None