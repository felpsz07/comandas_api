from infra import database
from sqlalchemy import Column, VARCHAR, CHAR, Integer

# ORM
class ClienteDB(database.Base):
    __tablename__ = 'tb_clientes'
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    nome = Column(VARCHAR(100), nullable=False)
    cpf = Column(CHAR(11), nullable=False, unique=True, index=True)
    telefone = Column(CHAR(11), nullable=False)

    def __init__(self, id, nome, cpf, telefone):
        self.id = id
        self.nome = nome
        self.cpf = cpf
        self.telefone = telefone