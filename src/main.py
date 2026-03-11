# Felipe Bueno de Oliveira
from fastapi import FastAPI
from src.settings import HOST, PORT, RELOAD
import uvicorn

# Import das classes com as rotas/endpoints
from src.routers import FuncionarioRouter
from src.routers import ClienteRouter
from src.routers import ProdutoRouter

app = FastAPI()

# Mapeamento das rotas/endpoints
app.include_router(FuncionarioRouter.router)
app.include_router(ClienteRouter.router)
app.include_router(ProdutoRouter.router)

if __name__ == "__main__":
    uvicorn.run('main:app', host=HOST, port=int(PORT), reload=RELOAD)

# rota padrão
@app.get("/", tags=["Root"], status_code=200)
def root():
    return {"detail": "API Pastelaria", "Swagger": "http://localhost:8000/docs" , "Redoc": "http://localhost:8000/redoc"}