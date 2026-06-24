from sqlalchemy import Column, DECIMAL, Integer, DateTime, ForeignKey
from infra.database import Base


class RecebimentoDB(Base):
    """
    Cabeçalho de um recebimento no caixa.
    Um recebimento pode quitar uma ou MAIS comandas simultaneamente
    (ver RecebimentoComandaDB, tabela associativa).
    """
    __tablename__ = "tb_recebimento"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    cliente_id = Column(Integer, ForeignKey("tb_clientes.id", ondelete="RESTRICT"), nullable=True, default=None)
    funcionario_id = Column(Integer, ForeignKey("tb_funcionarios.id", ondelete="RESTRICT"), nullable=False)
    data_hora = Column(DateTime, nullable=False)
    subtotal_geral = Column(DECIMAL(10, 2), nullable=False)
    desconto_total = Column(DECIMAL(10, 2), nullable=False, default=0)
    acrescimo_total = Column(DECIMAL(10, 2), nullable=False, default=0)
    valor_final = Column(DECIMAL(10, 2), nullable=False)


class RecebimentoComandaDB(Base):
    """
    Tabela associativa: registra quais comandas foram quitadas em cada recebimento.
    Permite N comandas por recebimento (requisito de recebimento múltiplo/simultâneo).
    """
    __tablename__ = "tb_recebimento_comanda"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    recebimento_id = Column(Integer, ForeignKey("tb_recebimento.id", ondelete="CASCADE"), nullable=False)
    comanda_id = Column(Integer, ForeignKey("tb_comanda.id", ondelete="RESTRICT"), nullable=False, unique=True)
    # unique=True em comanda_id garante, no nível de banco, que uma comanda
    # só pode aparecer em UM recebimento (não pode ser paga duas vezes)