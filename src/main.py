# Felipe Bueno de Oliveira
from fastapi import FastAPI
from src.settings import HOST, PORT, RELOAD
import uvicorn

# Import das classes com as rotas/endpoints
from src.routers import AuthRouter
from src.routers import FuncionarioRouter
from src.routers import ClienteRouter
from src.routers import ProdutoRouter


# lifespan - Ciclo de vida aplicação
from src.infra import database
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

# rota padrão
@app.get("/", tags=["Root"], status_code=200)
async def root():
    return {"detail": "API Pastelaria", "Swagger": "http://localhost:8000/docs" , "Redoc": "http://localhost:8000/redoc"}

# Mapeamento das rotas/endpoints
app.include_router(AuthRouter.router)
app.include_router(FuncionarioRouter.router)
app.include_router(ClienteRouter.router)
app.include_router(ProdutoRouter.router)
app.include_router(AuthRouter.router)

if __name__ == "__main__":
    uvicorn.run('main:app', host=HOST, port=int(PORT), reload=RELOAD)
