from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from routers import auth, pedidos

app = FastAPI(title="MacroBox API")

ORIGENS_PERMITIDAS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENS_PERMITIDAS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = auth.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth.router)
app.include_router(pedidos.router)

@app.get("/")
def home():
    return {"status": "ok", "mensagem": "MacroBox API Operacional."}