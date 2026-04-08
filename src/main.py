# Felipe Bueno de Oliveira
from fastapi import FastAPI
from infra.rate_limit import limiter, rate_limit_exceeded_handler
from settings import HOST, PORT, RELOAD
from slowapi.errors import RateLimitExceeded
import uvicorn

# Import das classes com as rotas/endpoints
from routers import AuditoriaRouter
from routers import AuthRouter
from routers import FuncionarioRouter
from routers import ClienteRouter
from routers import ProdutoRouter
from routers import HealthRouter


# lifespan - Ciclo de vida aplicação
from infra import database
from contextlib import asynccontextmanager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Executa no startup
    print("API has started")
    # Cria, caso não existam, as tabelas de todos os modelos que encontras na aplicação(impotados)
    await database.cria_tabelas()
    yield
    # Executa no shutdown
    print("API is shutting down")

app = FastAPI(lifespan=lifespan)

# Configuração de Rate limiting
app.state.limiter = limiter

# Registrar hadler personalizada ANTES  de incluir  rotas
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# rota padrão
@app.get("/", tags=["Root"], status_code=200)
async def root():
    return {"detail": "API Pastelaria", "Swagger": "http://localhost:8000/docs" , "Redoc": "http://localhost:8000/redoc"}

# Mapeamento das rotas/endpoints
app.include_router(AuditoriaRouter.router)
app.include_router(AuthRouter.router)
app.include_router(FuncionarioRouter.router)
app.include_router(ClienteRouter.router)
app.include_router(ProdutoRouter.router)
app.include_router(AuthRouter.router)
app.include_router(HealthRouter.router)

if __name__ == "__main__":
    uvicorn.run('main:app', host=HOST, port=int(PORT), reload=RELOAD)
