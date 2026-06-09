from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from slowapi import Limiter
from datetime import datetime, timezone
import random
import string
import uuid
from sqlalchemy.exc import IntegrityError
from database import get_db
from models import Usuario
from schemas import UsuarioCriar, Token, UsuarioResposta, UsuarioAtualizar, AlterarSenha
from security import obter_hash_senha, verificar_senha, criar_token_acesso, decodificar_token

# Mitigação contra ataques de BruteForce.
def obter_ip_real(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0]
    return request.client.host

limiter = Limiter(key_func=obter_ip_real)
router = APIRouter(prefix="/api/auth", tags=["Autenticação"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def obter_usuario_atual(request: Request, db: Session = Depends(get_db)):
    excecao_credenciais = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sessão inválida ou expirada. Faça login novamente.",
    )
    
    token = request.cookies.get("access_token")
    if not token:
        raise excecao_credenciais
    
    try:
        email = decodificar_token(token)
        if email is None:
            raise excecao_credenciais
    except ValueError as e:
        raise excecao_credenciais
        
    
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if usuario is None or not usuario.is_active:
        raise excecao_credenciais
    return usuario

def obter_usuario_admin(usuario: Usuario = Depends(obter_usuario_atual)):
    if usuario.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Privilégios de administrador necessários."
        )
    return usuario

# Rotas de Autenticação
@router.post("/registrar")
@limiter.limit("5/minute")
def registrar_usuario(request: Request, usuario: UsuarioCriar, db: Session = Depends(get_db)):
    if not usuario.aceitou_termos:
        raise HTTPException(status_code=400, detail="É necessário aceitar os termos de uso para se registrar.")
    
    if db.query(Usuario).filter(Usuario.email == usuario.email).first():
        raise HTTPException(status_code=400, detail="Email já cadastrado.")
    
    if db.query(Usuario).filter(Usuario.cpf == usuario.cpf).first():
        raise HTTPException(status_code=400, detail="CPF já cadastrado no sistema.")
    
    novo_usuario = Usuario(
        nome=usuario.nome,
        email=usuario.email,
        celular=usuario.celular,
        cpf=usuario.cpf,
        data_nascimento=usuario.data_nascimento,
        senha_hash=obter_hash_senha(usuario.senha),
        role="user", 
        aceitou_termos=True,
        data_aceite_termos=datetime.now(timezone.utc)
    )
    
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    
    return {"status": "sucesso", "mensagem": "Conta criada. Faça o login para acessar."}

@router.post("/login")
@limiter.limit("5/minute")
def login(request: Request, response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == form_data.username).first()
    if not usuario or not verificar_senha(form_data.password, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos. Tente novamente.",
        )
    # Token armazenado em cookie HttpOnly para maior segurança contra XSS.
    token = criar_token_acesso(dados={"sub": usuario.email})
   
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=600
    )
    return {"status": "sucesso"}

@router.get("/me", response_model=UsuarioResposta)
def ler_usuario_atual(usuario_atual: Usuario = Depends(obter_usuario_atual)):
    return usuario_atual

@router.put("/me", response_model=UsuarioResposta)
def atualizar_perfil_usuario(dados: UsuarioAtualizar, db: Session = Depends(get_db), usuario_atual: Usuario = Depends(obter_usuario_atual)):
    if dados.nome is not None:
        usuario_atual.nome = dados.nome
    if dados.celular is not None:
        usuario_atual.celular = dados.celular
        
    db.commit()
    db.refresh(usuario_atual)
    return usuario_atual

@router.put("/me/senha")
def alterar_senha_usuario(dados: AlterarSenha, db: Session = Depends(get_db), usuario_atual: Usuario = Depends(obter_usuario_atual)):
    if not verificar_senha(dados.senha_atual, usuario_atual.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A senha atual inserida está incorreta."
        )
    
    usuario_atual.senha_hash = obter_hash_senha(dados.nova_senha)
    db.commit()
    return {"status": "sucesso", "mensagem": "Senha modificada com sucesso."}

@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
# Implementação de anonimização de dados para conformidade com a LGPD. 
def anonimizar_conta_lgpd(db: Session = Depends(get_db), usuario_atual: Usuario = Depends(obter_usuario_atual)):
    id_anonimo = uuid.uuid4().hex
    
    usuario_atual.nome = "Usuário Anonimizado"
    usuario_atual.email = f"deleted_{usuario_atual.id}_{id_anonimo}@macrobox.local"
    usuario_atual.cpf = f"DEL{id_anonimo[:8]}"
    usuario_atual.celular = "0000000000"
    usuario_atual.senha_hash = "DELETED"
    usuario_atual.is_active = False 
    
    db.commit()
    return None

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(
        key="access_token",
        path="/",
        secure=False,      
        httponly=True,
        samesite="lax"
    )
    return {"status": "sucesso", "mensagem": "Sessão encerrada"}