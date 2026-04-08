from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from settings import STR_DATABASE   
from sqlalchemy.orm import Session

# Cria a engine de conexão com o banco de dados
engine = create_engine(STR_DATABASE, echo=True)

# Cria a Sessão do banco de dados
Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Criar trabalhar com tabelas
Base = declarative_base()

# Cria, caso nao existam, as tabelas de todos os modelos que encontras na aplicação(impotados)
async def cria_tabelas():
    Base.metadata.create_all(engine)

# Dependencia para injetar a sessão do banco de dados nas rotas
def get_db():
    db_session = Session()
    try:
        yield db_session
    finally:
        db_session.close()
        